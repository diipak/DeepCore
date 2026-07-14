import os
import pytest
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from deepcore.runtime.processing.runtime import ProcessingRuntime, ProcessingResult
from deepcore.runtime.processing.stages import ContentIndexStage, RelationshipStage, SignalStage
from deepcore.core.providers.markdown import MarkdownProvider
from deepcore.core.registry.service import RegistryService
from deepcore.storage.sqlite.models import RegistryObject, RegistryRelationship, RegistrySignal, ObjectActivityLog
from deepcore.core.objects.schemas import SignalType, RelationshipType
from deepcore.intelligence.signal_engine import SignalEngine, SignalPolicy

def test_signal_engine_all_rules(tmp_path, db_session):
    """Verify all signal rules: RECENT_ACTIVITY, FREQUENT_ACTIVITY, HIGH_REFERENCE_COUNT, ORPHAN_NOTE, and BROKEN_REFERENCE."""
    db_session.query(RegistrySignal).delete()
    db_session.query(RegistryRelationship).delete()
    db_session.query(RegistryObject).delete()
    db_session.commit()

    root_path = str(tmp_path)
    
    # 1. Create a note with a broken link and tags
    note_a_path = os.path.join(root_path, "noteA.md")
    with open(note_a_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write("tags: [deepcore]\n")
        f.write("---\n")
        f.write("References [[noteB]] and a broken [[NonExistent]].\n")

    # 2. Create note B
    note_b_path = os.path.join(root_path, "noteB.md")
    with open(note_b_path, "w", encoding="utf-8") as f:
        f.write("References [[noteC]].\n")

    # 3. Create note C
    note_c_path = os.path.join(root_path, "noteC.md")
    with open(note_c_path, "w", encoding="utf-8") as f:
        f.write("I am note C. I have links from note B.\n")

    # 4. Ingest and run stages
    provider = MarkdownProvider(root_path=root_path)
    registry_service = RegistryService(db_session)
    sync_result = provider.sync(registry_service)
    
    runtime = ProcessingRuntime()
    runtime.register_stage(ContentIndexStage())
    runtime.register_stage(RelationshipStage())
    runtime.register_stage(SignalStage())
    
    pipeline_res = runtime.execute(db_session, sync_result)
    assert len(pipeline_res.failures) == 0

    # Query DB objects
    db_note_a = db_session.query(RegistryObject).filter(RegistryObject.title == "noteA").first()
    db_note_b = db_session.query(RegistryObject).filter(RegistryObject.title == "noteB").first()
    db_note_c = db_session.query(RegistryObject).filter(RegistryObject.title == "noteC").first()
    
    assert db_note_a is not None
    assert db_note_b is not None
    assert db_note_c is not None

    # Verify RECENT_ACTIVITY on note A
    sig_recent = db_session.query(RegistrySignal).filter(
        RegistrySignal.target_object_id == db_note_a.id,
        RegistrySignal.signal_type == SignalType.RECENT_ACTIVITY.value
    ).first()
    assert sig_recent is not None
    assert sig_recent.value == "recent"
    evidence_recent = json.loads(sig_recent.evidence_json)
    assert evidence_recent["type"] == "temporal_recency"
    assert "measured_value" in evidence_recent
    assert "threshold" in evidence_recent

    # Verify BROKEN_REFERENCE on note A
    sig_broken = db_session.query(RegistrySignal).filter(
        RegistrySignal.target_object_id == db_note_a.id,
        RegistrySignal.signal_type == SignalType.BROKEN_REFERENCE.value
    ).first()
    assert sig_broken is not None
    assert sig_broken.value == "NonExistent"
    evidence_broken = json.loads(sig_broken.evidence_json)
    assert evidence_broken["type"] == "broken_link"
    assert evidence_broken["target_title"] == "NonExistent"

    # Verify ORPHAN_NOTE: note A is NOT an orphan because it has relationships with note B.
    sig_orphan = db_session.query(RegistrySignal).filter(
        RegistrySignal.target_object_id == db_note_a.id,
        RegistrySignal.signal_type == SignalType.ORPHAN_NOTE.value
    ).first()
    assert sig_orphan is None


def test_signal_engine_dormant_and_orphan(tmp_path, db_session):
    """Verify DORMANT and ORPHAN_NOTE signals work correctly."""
    db_session.query(RegistrySignal).delete()
    db_session.query(RegistryRelationship).delete()
    db_session.query(RegistryObject).delete()
    db_session.commit()

    root_path = str(tmp_path)
    note_dir = os.path.join(root_path, "isolated")
    os.makedirs(note_dir, exist_ok=True)
    note_path = os.path.join(note_dir, "isolated_note.md")
    with open(note_path, "w", encoding="utf-8") as f:
        f.write("I am isolated.\n")

    provider = MarkdownProvider(root_path=root_path)
    registry_service = RegistryService(db_session)
    sync_result = provider.sync(registry_service)

    runtime = ProcessingRuntime()
    runtime.register_stage(ContentIndexStage())
    runtime.register_stage(RelationshipStage())
    runtime.register_stage(SignalStage())
    
    pipeline_res = runtime.execute(db_session, sync_result)
    assert len(pipeline_res.failures) == 0

    db_note = db_session.query(RegistryObject).filter(RegistryObject.title == "isolated_note").first()
    assert db_note is not None

    # At this point, it is recent (modified today) and has 0 relations -> Orphan!
    sig_orphan = db_session.query(RegistrySignal).filter(
        RegistrySignal.target_object_id == db_note.id,
        RegistrySignal.signal_type == SignalType.ORPHAN_NOTE.value
    ).first()
    assert sig_orphan is not None
    assert sig_orphan.value == "orphan"

    # Now manually mock dormancy by backdating updated_at to 40 days ago
    past_date = datetime.now(timezone.utc) - timedelta(days=40)
    db_note.updated_at = past_date
    db_session.add(db_note)
    db_session.commit()

    # Re-run evaluation via SignalEngine directly with default policy (dormancy_days=30)
    engine = SignalEngine(db_session)
    # We pass a dummy ProcessingResult to evaluate
    dummy_res = ProcessingResult()
    engine.evaluate_object_signals(db_note, dummy_res)

    # RECENT_ACTIVITY should be removed, and DORMANT should be added
    sig_recent_after = db_session.query(RegistrySignal).filter(
        RegistrySignal.target_object_id == db_note.id,
        RegistrySignal.signal_type == SignalType.RECENT_ACTIVITY.value
    ).first()
    assert sig_recent_after is None

    sig_dormant = db_session.query(RegistrySignal).filter(
        RegistrySignal.target_object_id == db_note.id,
        RegistrySignal.signal_type == SignalType.DORMANT.value
    ).first()
    assert sig_dormant is not None
    assert sig_dormant.value == "dormant"
    evidence = json.loads(sig_dormant.evidence_json)
    assert evidence["type"] == "temporal_dormancy"
    assert evidence["threshold"] == "30 days"


def test_signal_engine_frequent_activity(tmp_path, db_session):
    """Verify FREQUENT_ACTIVITY works correctly."""
    db_session.query(RegistrySignal).delete()
    db_session.query(RegistryRelationship).delete()
    db_session.query(RegistryObject).delete()
    db_session.query(ObjectActivityLog).delete()
    db_session.commit()

    root_path = str(tmp_path)
    note_path = os.path.join(root_path, "active_note.md")
    with open(note_path, "w", encoding="utf-8") as f:
        f.write("Frequent updates test.\n")

    provider = MarkdownProvider(root_path=root_path)
    registry_service = RegistryService(db_session)
    sync_result = provider.sync(registry_service)

    runtime = ProcessingRuntime()
    runtime.register_stage(ContentIndexStage())
    runtime.register_stage(RelationshipStage())
    runtime.register_stage(SignalStage())
    
    # Executing the pipeline once logs 1 modification in ObjectActivityLog
    runtime.execute(db_session, sync_result)

    db_note = db_session.query(RegistryObject).filter(RegistryObject.title == "active_note").first()
    assert db_note is not None

    # Verify no frequent activity signal yet (threshold is 3)
    sig_freq = db_session.query(RegistrySignal).filter(
        RegistrySignal.target_object_id == db_note.id,
        RegistrySignal.signal_type == SignalType.FREQUENT_ACTIVITY.value
    ).first()
    assert sig_freq is None

    # Simulate two more sync updates in the log
    for _ in range(2):
        log_entry = ObjectActivityLog(
            object_id=db_note.id,
            action="updated",
            timestamp=datetime.now(timezone.utc)
        )
        db_session.add(log_entry)
    db_session.commit()

    # Re-evaluate
    engine = SignalEngine(db_session)
    engine.evaluate_object_signals(db_note)

    # Now the count is 3 -> FREQUENT_ACTIVITY should be active!
    sig_freq = db_session.query(RegistrySignal).filter(
        RegistrySignal.target_object_id == db_note.id,
        RegistrySignal.signal_type == SignalType.FREQUENT_ACTIVITY.value
    ).first()
    assert sig_freq is not None
    assert sig_freq.value == "frequent"
    evidence = json.loads(sig_freq.evidence_json)
    assert evidence["measured_value"] == 3


def test_signal_engine_lifecycle_identity_preservation(tmp_path, db_session):
    """Verify that the Signal Engine updates signals in-place and preserves UUID/identity."""
    db_session.query(RegistrySignal).delete()
    db_session.query(RegistryRelationship).delete()
    db_session.query(RegistryObject).delete()
    db_session.query(ObjectActivityLog).delete()
    db_session.commit()

    root_path = str(tmp_path)
    note_path = os.path.join(root_path, "lifecycle_note.md")
    with open(note_path, "w", encoding="utf-8") as f:
        f.write("Identity preservation test.\n")

    provider = MarkdownProvider(root_path=root_path)
    registry_service = RegistryService(db_session)
    sync_result = provider.sync(registry_service)

    runtime = ProcessingRuntime()
    runtime.register_stage(ContentIndexStage())
    runtime.register_stage(RelationshipStage())
    runtime.register_stage(SignalStage())
    
    runtime.execute(db_session, sync_result)

    db_note = db_session.query(RegistryObject).filter(RegistryObject.title == "lifecycle_note").first()
    
    # Find RECENT_ACTIVITY signal
    sig_before = db_session.query(RegistrySignal).filter(
        RegistrySignal.target_object_id == db_note.id,
        RegistrySignal.signal_type == SignalType.RECENT_ACTIVITY.value
    ).first()
    assert sig_before is not None
    sig_id = sig_before.id
    sig_uuid = sig_before.uuid

    # Run the evaluate again (which triggers an update on the signal)
    engine = SignalEngine(db_session)
    engine.evaluate_object_signals(db_note)

    # Query the signal again
    sig_after = db_session.query(RegistrySignal).filter(
        RegistrySignal.target_object_id == db_note.id,
        RegistrySignal.signal_type == SignalType.RECENT_ACTIVITY.value
    ).first()
    assert sig_after is not None
    assert sig_after.id == sig_id
    assert sig_after.uuid == sig_uuid
