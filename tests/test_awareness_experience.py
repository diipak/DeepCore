import json
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from deepcore.storage.sqlite.models import (
    RegistryObject as DBRegistryObject,
    RegistryRelationship as DBRegistryRelationship,
    Workspace as DBWorkspace,
    SyncRun as DBSyncRun
)
from deepcore.core.awareness.service import AwarenessService

def test_awareness_service_empty_state(db_session: Session):
    """Verify default composed Awareness state when workspace is empty."""
    # Ensure workspace exists
    ws = db_session.query(DBWorkspace).filter(DBWorkspace.id == 1).first()
    if not ws:
        ws = DBWorkspace(id=1, name="Workspace 1")
        db_session.add(ws)
        db_session.commit()

    service = AwarenessService(db_session, workspace_id=1)
    state = service.get_awareness_state()

    assert state["summary"]["memory_count"] == 0
    assert state["summary"]["concept_count"] == 0
    assert len(state["focus"]) == 0
    assert len(state["understanding"]) == 0
    
    # Verify default orientation text is returned (Amendment 1)
    assert len(state["orientation"]) == 1
    assert state["orientation"][0]["title"] == "Quiet reflection state"
    assert state["orientation"][0]["change_type"] == "updated_context"


def test_awareness_focus_recency_approximation(db_session: Session):
    """Verify focus intent returns last modified memories (Amendment 2)."""
    # Create test notes
    n1 = DBRegistryObject(
        workspace_id=1,
        object_type="note",
        title="Active Project Proposal",
        source_system="filesystem",
        status="active",
        updated_at=datetime.now()
    )
    n2 = DBRegistryObject(
        workspace_id=1,
        object_type="note",
        title="Dormant Meeting Notes",
        source_system="filesystem",
        status="active",
        updated_at=datetime.now()
    )
    db_session.add(n1)
    db_session.add(n2)
    db_session.commit()

    service = AwarenessService(db_session, workspace_id=1)
    focus = service._get_focus_intent()

    assert len(focus) == 2
    assert focus[0]["title"] == "Dormant Meeting Notes" # sorted by updated_at desc
    assert focus[1]["title"] == "Active Project Proposal"
    assert focus[0]["object_type"] == "note"


def test_awareness_orientation_sync_runs(db_session: Session):
    """Verify orientation feed lists recent synchronization activities (Amendment 1)."""
    run = DBSyncRun(
        provider="filesystem",
        source_location="/Users/test/notes",
        started_at=datetime.now(),
        finished_at=datetime.now(),
        status="Finished",
        objects_scanned=10,
        objects_created=3,
        objects_updated=1,
        objects_existing=6,
        objects_missing=0
    )
    db_session.add(run)
    db_session.commit()

    service = AwarenessService(db_session, workspace_id=1)
    orientation = service._get_orientation()

    assert len(orientation) >= 1
    assert "Synced filesystem library" in orientation[0]["title"]
    assert orientation[0]["change_type"] == "new_artifact"
    assert "Discovered 3 new" in orientation[0]["description"]


def test_awareness_understanding_orphans_and_unapproved_concepts(db_session: Session):
    """Verify observations correctly surface orphans and unapproved concepts (Amendment 1)."""
    # 1. Create an orphaned note (no relationships)
    orphan_note = DBRegistryObject(
        workspace_id=1,
        object_type="note",
        title="Orphan Note",
        source_system="filesystem",
        status="active"
    )
    # 2. Create an unapproved concept
    unapproved_concept = DBRegistryObject(
        workspace_id=1,
        object_type="concept",
        title="Quantum Compute",
        source_system="filesystem",
        status="active",
        metadata_json=json.dumps({"concept_status": "extracted"})
    )
    db_session.add(orphan_note)
    db_session.add(unapproved_concept)
    db_session.commit()

    service = AwarenessService(db_session, workspace_id=1)
    observations = service._get_understanding()

    # Assert both observations are generated
    obs_types = [o["observation_type"] for o in observations]
    assert "unapproved_concept" in obs_types
    assert "orphan" in obs_types

    # Verify action routes CTA mapping
    concept_obs = next(o for o in observations if o["observation_type"] == "unapproved_concept")
    assert concept_obs["action_route"] == "/platform"
    assert concept_obs["action_label"] == "Review Concepts"

    orphan_obs = next(o for o in observations if o["observation_type"] == "orphan")
    assert "/assistant" in orphan_obs["action_route"]
    assert "Ask Assistant" in orphan_obs["action_label"]


def test_awareness_continuation_thinking_prompts(db_session: Session):
    """Verify continuation steps suggest guided prompts for active focus (Amendment 1)."""
    service = AwarenessService(db_session, workspace_id=1)
    
    # 1. Verify general prompt when focus is empty
    steps_empty = service._get_continuation(focus_items=[], observations=[])
    assert len(steps_empty) == 1
    assert steps_empty[0]["action_label"] == "Analyze Web"

    # 2. Verify pre-populated prompt cards targeting active focus
    focus_items = [{
        "title": "Quantum Compute",
        "object_type": "note",
        "object_uuid": "xyz-123",
        "description": "Concept definition",
        "last_accessed": "just now"
    }]
    steps_focus = service._get_continuation(focus_items=focus_items, observations=[])
    assert len(steps_focus) == 3
    assert "Quantum Compute" in steps_focus[0]["title"]
    assert "Quantum Compute" in steps_focus[0]["prompt"]
    assert steps_focus[0]["action_label"] == "Start Thread"
