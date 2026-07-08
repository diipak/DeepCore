import os
import json
import pytest
from sqlalchemy import create_engine, Table, Column, Integer, String, Float, DateTime, MetaData, insert, select
from datetime import datetime
from typer.testing import CliRunner

from deepcore.core.concepts.service import ConceptService
from deepcore.core.content.service import ContentService
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObjectCreate, ObjectType
from deepcore.storage.sqlite.models import (
    RegistryObject as DBRegistryObject,
    RegistryRelationship as DBRegistryRelationship,
    ContentIndex as DBContentIndex,
    run_migrations
)
from deepcore.cli.main import app

def test_migration_safety_concepts(tmp_path):
    """Verify that migrations safely add the relationship evidence columns without corrupting existing data."""
    db_file = tmp_path / "migration_concepts_test.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url)
    
    # 1. Mimic old database state with old schema columns
    metadata = MetaData()
    registry_relationships_table = Table(
        "registry_relationships",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("from_object_id", Integer, nullable=False),
        Column("to_object_id", Integer, nullable=False),
        Column("relationship_type", String, nullable=False),
        Column("confidence", Float, default=1.0, nullable=False),
    )
    metadata.create_all(engine)
    
    # 2. Insert test data
    with engine.begin() as conn:
        conn.execute(insert(registry_relationships_table).values(
            from_object_id=1,
            to_object_id=2,
            relationship_type="links"
        ))
        
    # 3. Run the migrations
    run_migrations(engine)
    
    # 4. Verify new columns exist in registry_relationships
    from sqlalchemy import inspect
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("registry_relationships")]
    assert "evidence_json" in columns
    assert "relationship_source" in columns
    
    # 5. Verify the pre-existing relationship data is preserved
    with engine.begin() as conn:
        res = conn.execute(select(registry_relationships_table)).fetchall()
        assert len(res) == 1
        assert res[0][3] == "links"  # relationship_type


def test_concept_extraction_logic(tmp_path, db_session):
    """Verify that headings, technical terms, frequency terms, stop words, and logical identities work as intended."""
    # Write a test markdown file containing multiple concept cues
    note_content = (
        "# Ollama Setup\n"
        "Deploy Ollama on local machines.\n"
        "## FastAPI Backend\n"
        "FastAPI is a CamelCase keyword. FastAPI is used with SQLite.\n"
        "We also love MLX for local LLM acceleration.\n"
        "SQLite runs inside Docker containers. Docker helps deployment.\n"
        "And we ignore system data and project files.\n"
    )
    note_file = tmp_path / "extraction_note.md"
    note_file.write_text(note_content)
    
    registry = RegistryService(db_session)
    content_service = ContentService(db_session)
    concept_service = ConceptService(db_session)
    
    # 1. Register and index the note
    obj = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Extraction Note",
        source_system="markdown",
        location=str(note_file),
        status="active"
    ))
    content_service.index_object(obj.id)
    
    # 2. Extract concepts
    res = concept_service.extract_from_object(obj.id)
    assert res["concepts_created"] > 0
    assert res["relationships_created"] > 0
    
    # 3. Verify specific concepts are extracted:
    # A. Headings:
    # - "Ollama Setup"
    # - "FastAPI Backend"
    concept_heading1 = concept_service.get_concept_by_name("Ollama Setup")
    assert concept_heading1 is not None
    assert concept_heading1.title == "Ollama Setup"
    meta1 = json.loads(concept_heading1.metadata_json)
    assert meta1["normalized_key"] == "ollamasetup"
    
    # B. Technical Terms:
    # - "FastAPI" (CamelCase)
    # - "SQLite" (CamelCase)
    # - "MLX" (ALLCAPS abbreviation)
    concept_tech1 = concept_service.get_concept_by_name("FastAPI")
    assert concept_tech1 is not None
    
    concept_tech2 = concept_service.get_concept_by_name("SQLite")
    assert concept_tech2 is not None
    
    concept_tech3 = concept_service.get_concept_by_name("MLX")
    assert concept_tech3 is not None
    
    # C. Repeated Capitalized Phrase:
    # - "Docker" (occurs 2 times)
    concept_freq = concept_service.get_concept_by_name("Docker")
    assert concept_freq is not None
    
    # D. Stop Words Excluded:
    # - "system", "data", "project", "and" should NOT be extracted
    assert concept_service.get_concept_by_name("system") is None
    assert concept_service.get_concept_by_name("data") is None
    
    # 4. Verify evidence structure in relationships
    rel = db_session.query(DBRegistryRelationship).filter(
        DBRegistryRelationship.from_object_id == obj.id,
        DBRegistryRelationship.to_object_id == concept_tech1.id
    ).first()
    assert rel is not None
    assert rel.relationship_type == "mentions"
    assert rel.relationship_source == "concept_v0.1"
    evidence = json.loads(rel.evidence_json)
    assert evidence["extractor"] == "concept_v0.1"
    assert "technical_term" in evidence["methods"]
    assert evidence["occurrences"] >= 2  # FastAPI occurs twice
    
    # 5. Idempotency: re-running does not create duplicate concepts or relationships
    res_dup = concept_service.extract_from_object(obj.id)
    assert res_dup["concepts_created"] == 0
    assert res_dup["relationships_created"] == 0


def test_active_status_filtering_concepts(tmp_path, db_session):
    """Verify that archived or merged concepts are ignored and queries filter by status='active'."""
    note_file = tmp_path / "active_test.md"
    note_file.write_text("# FastAPI\nFastAPI rocks.")
    
    registry = RegistryService(db_session)
    content_service = ContentService(db_session)
    concept_service = ConceptService(db_session)
    
    obj = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Active Note",
        source_system="markdown",
        location=str(note_file),
        status="active"
    ))
    content_service.index_object(obj.id)
    
    # Pre-create concept as archived
    archived_concept = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.CONCEPT,
        title="FastAPI",
        source_system="deepcore",
        status="archived",
        metadata_json=json.dumps({"normalized_key": "fastapi"})
    ))
    
    # Run extraction: should ignore the archived concept and create a new active one
    res = concept_service.extract_from_object(obj.id)
    assert res["concepts_created"] == 1
    
    active_concept = concept_service.get_concept_by_name("FastAPI")
    assert active_concept is not None
    assert active_concept.id != archived_concept.id
    assert active_concept.status == "active"


@pytest.fixture
def cli_runner_concepts(db_session):
    """Provides a CliRunner instance with the SessionLocal db patched to the test transactional session."""
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


def test_cli_concepts_commands(tmp_path, db_session, cli_runner_concepts):
    """Verify Typer CLI commands 'concepts extract', 'concepts list', and 'concepts show' work with correct format."""
    note_file = tmp_path / "cli_concepts.md"
    note_file.write_text("# FastAPI\nFastAPI uses SQLite.")
    
    registry = RegistryService(db_session)
    content_service = ContentService(db_session)
    
    obj = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="CLI Concept Note",
        source_system="markdown",
        location=str(note_file),
        status="active"
    ))
    content_service.index_object(obj.id)
    
    # 1. Run 'deepcore concepts extract'
    result_extract = cli_runner_concepts.invoke(app, ["concepts", "extract"])
    assert result_extract.exit_code == 0
    assert "DeepCore Concept Extraction" in result_extract.stdout
    assert "Scanned:\n1" in result_extract.stdout
    assert "Concepts Created:\n2" in result_extract.stdout  # FastAPI and SQLite
    
    # 2. Run 'deepcore concepts list'
    result_list = cli_runner_concepts.invoke(app, ["concepts", "list"])
    assert result_list.exit_code == 0
    assert "CONCEPT | CONNECTIONS" in result_list.stdout
    assert "FastAPI | 1" in result_list.stdout
    assert "SQLite | 1" in result_list.stdout
    
    # 3. Run 'deepcore concepts show FastAPI'
    result_show = cli_runner_concepts.invoke(app, ["concepts", "show", "FastAPI"])
    assert result_show.exit_code == 0
    assert "Concept:\nFastAPI" in result_show.stdout
    assert "Connected Memories:\n- CLI Concept Note" in result_show.stdout
