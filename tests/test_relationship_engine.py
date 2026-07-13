import os
import pytest
import json
from sqlalchemy.orm import Session
from deepcore.runtime.processing.runtime import ProcessingRuntime, ProcessingResult
from deepcore.runtime.processing.stages import ContentIndexStage, RelationshipStage
from deepcore.core.providers.markdown import MarkdownProvider
from deepcore.core.registry.service import RegistryService
from deepcore.storage.sqlite.models import RegistryObject, RegistryRelationship, ContentIndex
from deepcore.core.objects.schemas import RelationshipType

def test_relationship_engine_deterministic_extraction(staged_notes_dir, db_session):
    """Verify that Stage 2 RelationshipStage successfully processes and extracts deterministic relations."""
    root_path = staged_notes_dir
    
    # Create note A and note B in the same folder
    note_a_path = os.path.join(root_path, "noteA.md")
    note_b_path = os.path.join(root_path, "noteB.md")
    
    with open(note_a_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write("tags: [project-deepcore, work]\n")
        f.write("parent: noteC\n")
        f.write("version_of: oldNote\n")
        f.write("---\n")
        f.write("This is Note A which references [[noteB]].\n")
        
    with open(note_b_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write("tags: [project-deepcore]\n")
        f.write("---\n")
        f.write("This is Note B. It doesn't link to anything, but is linked by Note A.\n")

    # Let's also create noteC in a nested folder
    nested_dir = os.path.join(root_path, "nested")
    os.makedirs(nested_dir, exist_ok=True)
    note_c_path = os.path.join(nested_dir, "noteC.md")
    with open(note_c_path, "w", encoding="utf-8") as f:
        f.write("This is Note C.\n")

    # Also create oldNote
    old_note_path = os.path.join(root_path, "oldNote.md")
    with open(old_note_path, "w", encoding="utf-8") as f:
        f.write("This is oldNote.\n")

    # Ingest using MarkdownProvider
    provider = MarkdownProvider(root_path=root_path)
    registry_service = RegistryService(db_session)
    sync_result = provider.sync(registry_service)
    
    assert len(sync_result.created) >= 4
    
    # Run processing pipeline (Stage 1 and Stage 2)
    runtime = ProcessingRuntime()
    runtime.register_stage(ContentIndexStage())
    runtime.register_stage(RelationshipStage())
    
    pipeline_res = runtime.execute(db_session, sync_result)
    assert "content_indexing" in pipeline_res.stages_executed
    assert "relationship_engine" in pipeline_res.stages_executed
    assert len(pipeline_res.failures) == 0

    # Retrieve noteA and noteB DB objects
    db_note_a = db_session.query(RegistryObject).filter(RegistryObject.title == "noteA").first()
    db_note_b = db_session.query(RegistryObject).filter(RegistryObject.title == "noteB").first()
    db_note_c = db_session.query(RegistryObject).filter(RegistryObject.title == "noteC").first()
    db_old_note = db_session.query(RegistryObject).filter(RegistryObject.title == "oldNote").first()

    assert db_note_a is not None
    assert db_note_b is not None
    assert db_note_c is not None
    assert db_old_note is not None

    # Verify REFERENCES relationship
    ref_rel = db_session.query(RegistryRelationship).filter(
        RegistryRelationship.from_object_id == db_note_a.id,
        RegistryRelationship.to_object_id == db_note_b.id,
        RegistryRelationship.relationship_type == RelationshipType.REFERENCES.value
    ).first()
    assert ref_rel is not None
    assert ref_rel.confidence == 1.0
    evidence = json.loads(ref_rel.evidence_json)
    assert evidence["type"] == "markdown_link"
    assert "noteB" in evidence["detail"]
    assert evidence["producing_stage"] == "relationship_engine"
    assert ref_rel.uuid is not None

    # Verify REFERENCED_BY relationship (symmetrical inverse)
    inv_rel = db_session.query(RegistryRelationship).filter(
        RegistryRelationship.from_object_id == db_note_b.id,
        RegistryRelationship.to_object_id == db_note_a.id,
        RegistryRelationship.relationship_type == RelationshipType.REFERENCED_BY.value
    ).first()
    assert inv_rel is not None

    # Verify SAME_FOLDER relationship
    folder_rel = db_session.query(RegistryRelationship).filter(
        RegistryRelationship.from_object_id == db_note_a.id,
        RegistryRelationship.to_object_id == db_note_b.id,
        RegistryRelationship.relationship_type == RelationshipType.SAME_FOLDER.value
    ).first()
    assert folder_rel is not None
    evidence_folder = json.loads(folder_rel.evidence_json)
    assert evidence_folder["type"] == "shared_folder"

    # Verify SAME_PROJECT relationship
    project_rel = db_session.query(RegistryRelationship).filter(
        RegistryRelationship.from_object_id == db_note_a.id,
        RegistryRelationship.to_object_id == db_note_b.id,
        RegistryRelationship.relationship_type == RelationshipType.SAME_PROJECT.value
    ).first()
    assert project_rel is not None
    evidence_project = json.loads(project_rel.evidence_json)
    assert evidence_project["type"] == "shared_project"
    assert "project-deepcore" in evidence_project["detail"]

    # Verify CHILD_OF / PARENT_OF hierarchy relationship
    child_rel = db_session.query(RegistryRelationship).filter(
        RegistryRelationship.from_object_id == db_note_a.id,
        RegistryRelationship.to_object_id == db_note_c.id,
        RegistryRelationship.relationship_type == RelationshipType.CHILD_OF.value
    ).first()
    assert child_rel is not None

    parent_rel = db_session.query(RegistryRelationship).filter(
        RegistryRelationship.from_object_id == db_note_c.id,
        RegistryRelationship.to_object_id == db_note_a.id,
        RegistryRelationship.relationship_type == RelationshipType.PARENT_OF.value
    ).first()
    assert parent_rel is not None

    # Verify VERSION_OF relationship
    version_rel = db_session.query(RegistryRelationship).filter(
        RegistryRelationship.from_object_id == db_note_a.id,
        RegistryRelationship.to_object_id == db_old_note.id,
        RegistryRelationship.relationship_type == RelationshipType.VERSION_OF.value
    ).first()
    assert version_rel is not None


def test_relationship_incremental_updates_and_deletions(staged_notes_dir, db_session):
    """Verify that file modification correctly updates relations and link deletion cleans up stale relations."""
    root_path = staged_notes_dir
    note_a_path = os.path.join(root_path, "noteA.md")
    note_b_path = os.path.join(root_path, "noteB.md")
    
    with open(note_a_path, "w", encoding="utf-8") as f:
        f.write("This links to [[noteB]]\n")
    with open(note_b_path, "w", encoding="utf-8") as f:
        f.write("Note B content\n")

    provider = MarkdownProvider(root_path=root_path)
    registry_service = RegistryService(db_session)
    
    sync_result1 = provider.sync(registry_service)
    runtime = ProcessingRuntime()
    runtime.register_stage(ContentIndexStage())
    runtime.register_stage(RelationshipStage())
    runtime.execute(db_session, sync_result1)

    db_note_a = db_session.query(RegistryObject).filter(RegistryObject.title == "noteA").first()
    db_note_b = db_session.query(RegistryObject).filter(RegistryObject.title == "noteB").first()

    assert db_session.query(RegistryRelationship).filter(
        RegistryRelationship.from_object_id == db_note_a.id,
        RegistryRelationship.to_object_id == db_note_b.id,
        RegistryRelationship.relationship_type == RelationshipType.REFERENCES.value
    ).count() == 1

    # Modify Note A to remove the link
    with open(note_a_path, "w", encoding="utf-8") as f:
        f.write("Link deleted entirely.\n")

    sync_result2 = provider.sync(registry_service)
    assert db_note_a in sync_result2.updated

    runtime.execute(db_session, sync_result2)

    # REFERENCES between A and B must be removed
    assert db_session.query(RegistryRelationship).filter(
        RegistryRelationship.from_object_id == db_note_a.id,
        RegistryRelationship.to_object_id == db_note_b.id,
        RegistryRelationship.relationship_type == RelationshipType.REFERENCES.value
    ).count() == 0

    # Symmetrical complement REFERENCED_BY must also be removed
    assert db_session.query(RegistryRelationship).filter(
        RegistryRelationship.from_object_id == db_note_b.id,
        RegistryRelationship.to_object_id == db_note_a.id,
        RegistryRelationship.relationship_type == RelationshipType.REFERENCED_BY.value
    ).count() == 0


def test_duplicate_prevention_and_incremental_isolation(staged_notes_dir, db_session):
    """Verify that multiple sync runs do not result in duplicate relationships."""
    root_path = staged_notes_dir
    note_a_path = os.path.join(root_path, "noteA.md")
    note_b_path = os.path.join(root_path, "noteB.md")
    
    with open(note_a_path, "w", encoding="utf-8") as f:
        f.write("Link to [[noteB]]\n")
    with open(note_b_path, "w", encoding="utf-8") as f:
        f.write("Target\n")

    provider = MarkdownProvider(root_path=root_path)
    registry_service = RegistryService(db_session)
    
    runtime = ProcessingRuntime()
    runtime.register_stage(ContentIndexStage())
    runtime.register_stage(RelationshipStage())

    sync1 = provider.sync(registry_service)
    runtime.execute(db_session, sync1)

    db_note_a = db_session.query(RegistryObject).filter(RegistryObject.title == "noteA").first()
    db_note_b = db_session.query(RegistryObject).filter(RegistryObject.title == "noteB").first()

    assert db_session.query(RegistryRelationship).filter(
        RegistryRelationship.from_object_id == db_note_a.id,
        RegistryRelationship.to_object_id == db_note_b.id,
        RegistryRelationship.relationship_type == RelationshipType.REFERENCES.value
    ).count() == 1

    sync2 = provider.sync(registry_service)
    runtime.execute(db_session, sync2)

    assert db_session.query(RegistryRelationship).filter(
        RegistryRelationship.from_object_id == db_note_a.id,
        RegistryRelationship.to_object_id == db_note_b.id,
        RegistryRelationship.relationship_type == RelationshipType.REFERENCES.value
    ).count() == 1
