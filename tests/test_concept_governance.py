import json
import pytest
from typer.testing import CliRunner

from deepcore.core.concepts.service import ConceptService
from deepcore.core.content.service import ContentService
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObjectCreate, ObjectType
from deepcore.storage.sqlite.models import (
    RegistryObject as DBRegistryObject,
    RegistryRelationship as DBRegistryRelationship,
    ContentIndex as DBContentIndex
)
from deepcore.cli.main import app

def test_concept_governance_defaults(tmp_path, db_session):
    """Verify that newly extracted concepts default to candidate status and unknown type."""
    note_file = tmp_path / "defaults.md"
    note_file.write_text("# Ollama\nOllama is running.")
    
    registry = RegistryService(db_session)
    content_service = ContentService(db_session)
    concept_service = ConceptService(db_session)
    
    obj = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Defaults Note",
        source_system="markdown",
        location=str(note_file),
        status="active"
    ))
    content_service.index_object(obj.id)
    
    res = concept_service.extract_from_object(obj.id)
    assert res["concepts_created"] == 1
    
    concept = concept_service.get_concept_by_name("Ollama")
    assert concept is not None
    assert concept.status == "active"  # Object lifecycle status remains active
    
    meta = json.loads(concept.metadata_json)
    assert meta["concept_status"] == "candidate"
    assert meta["concept_type"] == "unknown"


def test_on_the_fly_metadata_migration(db_session):
    """Verify that concepts created before governance are migrated on-the-fly on read paths."""
    registry = RegistryService(db_session)
    concept_service = ConceptService(db_session)
    
    # Pre-create concept lacking governance metadata
    legacy_concept = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.CONCEPT,
        title="Legacy",
        source_system="deepcore",
        status="active",
        metadata_json=json.dumps({"normalized_key": "legacy"})
    ))
    
    # Trigger on-the-fly migration via get_concept_by_name
    concept = concept_service.get_concept_by_name("Legacy")
    assert concept is not None
    assert concept.id == legacy_concept.id
    
    meta = json.loads(concept.metadata_json)
    assert meta["concept_status"] == "candidate"
    assert meta["concept_type"] == "unknown"


def test_concept_type_whitelist_validation(db_session):
    """Verify that only whitelisted concept types are allowed, and others are rejected."""
    registry = RegistryService(db_session)
    concept_service = ConceptService(db_session)
    
    registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.CONCEPT,
        title="Validation",
        source_system="deepcore",
        status="active",
        metadata_json=json.dumps({"normalized_key": "validation", "concept_status": "candidate", "concept_type": "unknown"})
    ))
    
    # Approved with valid type
    concept_service.approve_concept("Validation", concept_type="tool")
    concept = concept_service.get_concept_by_name("Validation")
    meta = json.loads(concept.metadata_json)
    assert meta["concept_status"] == "approved"
    assert meta["concept_type"] == "tool"
    
    # Reject invalid type
    with pytest.raises(ValueError, match="Invalid concept type"):
        concept_service.approve_concept("Validation", concept_type="invalid_type")


def test_ignore_concept(db_session):
    """Verify ignoring a concept sets its concept_status to ignored."""
    registry = RegistryService(db_session)
    concept_service = ConceptService(db_session)
    
    registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.CONCEPT,
        title="Click",
        source_system="deepcore",
        status="active",
        metadata_json=json.dumps({"normalized_key": "click", "concept_status": "candidate", "concept_type": "unknown"})
    ))
    
    concept_service.ignore_concept("Click")
    concept = concept_service.get_concept_by_name("Click")
    meta = json.loads(concept.metadata_json)
    assert meta["concept_status"] == "ignored"


def test_merge_concepts_safety_and_evidence(tmp_path, db_session):
    """Verify merging reroutes relationships, handles duplicate relationships cleanly, and records origins in evidence_json."""
    registry = RegistryService(db_session)
    content_service = ContentService(db_session)
    concept_service = ConceptService(db_session)
    
    # Create two source files referencing variants of Git
    f1 = tmp_path / "n1.md"
    f1.write_text("# GitHUB\nGitHUB is cool.")
    f2 = tmp_path / "n2.md"
    f2.write_text("# GitHub\nGitHub is cool.")
    
    o1 = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE, title="N1", source_system="markdown", location=str(f1), status="active"
    ))
    o2 = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE, title="N2", source_system="markdown", location=str(f2), status="active"
    ))
    
    content_service.index_object(o1.id)
    content_service.index_object(o2.id)
    
    # Extract concepts
    concept_service.extract_from_object(o1.id)
    concept_service.extract_from_object(o2.id)
    
    src = concept_service.get_concept_by_name("GitHUB")
    tgt = concept_service.get_concept_by_name("GitHub")
    
    assert src is not None
    assert tgt is not None
    assert src.id != tgt.id
    
    # Now merge GitHUB into GitHub
    concept_service.merge_concepts("GitHUB", "GitHub")
    
    # Verify source status and metadata
    db_session.refresh(src)
    assert src.status == "merged"
    src_meta = json.loads(src.metadata_json)
    assert src_meta["merged_into"] == tgt.id
    
    # Verify relationships are rerouted and duplicates combined
    # Note 1 referenced GitHUB (which was merged into GitHub). It did NOT reference GitHub before.
    # Note 2 referenced GitHub.
    # We should have one relationship from o1 to GitHub and one from o2 to GitHub.
    rel_o1 = db_session.query(DBRegistryRelationship).filter(
        DBRegistryRelationship.from_object_id == o1.id,
        DBRegistryRelationship.to_object_id == tgt.id
    ).first()
    assert rel_o1 is not None
    
    # Create a situation where a single note references BOTH concepts to test duplicate merging
    f3 = tmp_path / "n3.md"
    f3.write_text("# GitHUB and GitHub\nBoth GitHUB and GitHub appear here.")
    o3 = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE, title="N3", source_system="markdown", location=str(f3), status="active"
    ))
    content_service.index_object(o3.id)
    
    # We manually create the two concepts again or merge them after extraction
    # Let's extract on o3
    # Wait, because GitHUB already has status='merged' in database, the extractor
    # will find the existing GitHUB concept and existing GitHub concept, and link them.
    # Let's verify it links them
    concept_service.extract_from_object(o3.id)
    
    # Verify relationships from o3 to src (GitHUB) and tgt (GitHub) exist
    rel_src = db_session.query(DBRegistryRelationship).filter(
        DBRegistryRelationship.from_object_id == o3.id,
        DBRegistryRelationship.to_object_id == src.id
    ).first()
    rel_tgt = db_session.query(DBRegistryRelationship).filter(
        DBRegistryRelationship.from_object_id == o3.id,
        DBRegistryRelationship.to_object_id == tgt.id
    ).first()
    
    assert rel_src is not None
    assert rel_tgt is not None
    
    # Perform another merge operation (merging same concepts, which will trigger the duplicate relationship logic)
    concept_service.merge_concepts("GitHUB", "GitHub")
    
    # Check that relationship from o3 to src is deleted
    assert db_session.query(DBRegistryRelationship).filter(DBRegistryRelationship.id == rel_src.id).first() is None
    
    # Check that target relationship is preserved and has merged evidence
    db_session.refresh(rel_tgt)
    evidence = json.loads(rel_tgt.evidence_json)
    assert evidence["occurrences"] >= 2
    assert "merge_origins" in evidence
    assert len(evidence["merge_origins"]) > 0
    assert evidence["merge_origins"][0]["merged_concept_id"] == src.id


def test_list_concepts_filtering(db_session):
    """Verify that listing filters out ignored and merged concepts by default, but includes ignored if show_ignored is True."""
    registry = RegistryService(db_session)
    concept_service = ConceptService(db_session)
    
    # Note: list_concepts relies on relationships existing. Let's register a note object and relationships.
    n = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE, title="N", source_system="test", status="active"
    ))
    
    c1 = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.CONCEPT, title="ShowMe", source_system="deepcore", status="active",
        metadata_json=json.dumps({"normalized_key": "showme", "concept_status": "candidate", "concept_type": "unknown"})
    ))
    c2 = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.CONCEPT, title="HideMe", source_system="deepcore", status="active",
        metadata_json=json.dumps({"normalized_key": "hideme", "concept_status": "ignored", "concept_type": "unknown"})
    ))
    c3 = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.CONCEPT, title="MergedMe", source_system="deepcore", status="merged",
        metadata_json=json.dumps({"normalized_key": "mergedme", "concept_status": "candidate", "concept_type": "unknown"})
    ))
    
    # Create relationships
    db_session.add(DBRegistryRelationship(from_object_id=n.id, to_object_id=c1.id, relationship_type="mentions"))
    db_session.add(DBRegistryRelationship(from_object_id=n.id, to_object_id=c2.id, relationship_type="mentions"))
    db_session.add(DBRegistryRelationship(from_object_id=n.id, to_object_id=c3.id, relationship_type="mentions"))
    db_session.commit()
    
    # Default list should only contain c1 (ShowMe)
    results_default = concept_service.list_concepts(show_ignored=False)
    titles_default = [obj.title for obj, _ in results_default]
    assert "ShowMe" in titles_default
    assert "HideMe" not in titles_default
    assert "MergedMe" not in titles_default
    
    # List with show_ignored=True should contain c1 and c2
    results_all = concept_service.list_concepts(show_ignored=True)
    titles_all = [obj.title for obj, _ in results_all]
    assert "ShowMe" in titles_all
    assert "HideMe" in titles_all
    assert "MergedMe" not in titles_all


@pytest.fixture
def cli_runner_gov(db_session):
    """Provides a CliRunner instance with SessionLocal db patched to the test transactional session."""
    class NoCloseSession:
        def __init__(self, session):
            self.session = session
        def __getattr__(self, name):
            return getattr(self.session, name)
        def close(self):
            pass

    mock_sess = NoCloseSession(db_session)
    import unittest.mock as mock
    with mock.patch("deepcore.cli.main.SessionLocal", return_value=mock_sess):
        yield CliRunner()


def test_cli_governance_commands(tmp_path, db_session, cli_runner_gov):
    """Verify CLI concepts commands ignore, approve, merge, list, and show execute successfully."""
    note_file = tmp_path / "cli_gov.md"
    note_file.write_text("# Click\nClick is a command-line interface tool.")
    
    registry = RegistryService(db_session)
    content_service = ContentService(db_session)
    
    obj = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE, title="CLI Gov Note", source_system="markdown", location=str(note_file), status="active"
    ))
    content_service.index_object(obj.id)
    
    # Extract concepts
    result_extract = cli_runner_gov.invoke(app, ["concepts", "extract"])
    assert result_extract.exit_code == 0
    
    # 1. Verify show outputs type and status
    result_show = cli_runner_gov.invoke(app, ["concepts", "show", "Click"])
    assert result_show.exit_code == 0
    assert "Concept:\nClick" in result_show.stdout
    assert "Type:\nunknown" in result_show.stdout
    assert "Status:\ncandidate" in result_show.stdout
    
    # 2. Approve concept Click as tool
    result_approve = cli_runner_gov.invoke(app, ["concepts", "approve", "Click", "--type", "tool"])
    assert result_approve.exit_code == 0
    assert "Concept 'Click' approved with type 'tool'." in result_approve.stdout
    
    # Check that type and status updated in show
    result_show_updated = cli_runner_gov.invoke(app, ["concepts", "show", "Click"])
    assert "Type:\ntool" in result_show_updated.stdout
    assert "Status:\napproved" in result_show_updated.stdout
    
    # 3. Ignore concept Click
    result_ignore = cli_runner_gov.invoke(app, ["concepts", "ignore", "Click"])
    assert result_ignore.exit_code == 0
    assert "Concept 'Click' marked as ignored." in result_ignore.stdout
    
    # Check that Click is hidden from default list
    result_list_default = cli_runner_gov.invoke(app, ["concepts", "list"])
    assert "Click" not in result_list_default.stdout
    
    # Check that Click is shown in list --show-ignored
    result_list_ignored = cli_runner_gov.invoke(app, ["concepts", "list", "--show-ignored"])
    assert "Click" in result_list_ignored.stdout
    
    # 4. Merge concept Click into another
    registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.CONCEPT, title="ClickCLI", source_system="deepcore", status="active",
        metadata_json=json.dumps({"normalized_key": "clickcli", "concept_status": "candidate", "concept_type": "unknown"})
    ))
    
    result_merge = cli_runner_gov.invoke(app, ["concepts", "merge", "Click", "ClickCLI"])
    assert result_merge.exit_code == 0
    assert "Concept 'Click' merged into 'ClickCLI'." in result_merge.stdout
