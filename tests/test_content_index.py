import os
import pytest
import json
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, insert, select
from datetime import datetime
from typer.testing import CliRunner

from deepcore.core.content.service import ContentService
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObjectCreate, ObjectType
from deepcore.storage.sqlite.models import (
    RegistryObject as DBRegistryObject,
    ContentIndex as DBContentIndex,
    run_migrations
)
from deepcore.cli.main import app

def test_migration_safety(tmp_path):
    """Verify that migrations safely add the content_index table without corrupting existing registry data."""
    db_file = tmp_path / "migration_test.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url)
    
    # 1. Mimic old database state (only containing the registry_objects table)
    metadata = MetaData()
    registry_objects_table = Table(
        "registry_objects",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("uuid", String, nullable=False),
        Column("object_type", String, nullable=False),
        Column("title", String, nullable=False),
        Column("source_system", String, nullable=False),
        Column("external_id", String, nullable=True),
        Column("location", String, nullable=True),
        Column("description", String, nullable=True),
        Column("status", String, nullable=False, default="active"),
        Column("metadata_json", String, nullable=True),
        Column("provider_version", String, nullable=True),
        Column("content_hash", String, nullable=True),
    )
    metadata.create_all(engine)
    
    # 2. Insert test data into the old registry_objects table
    with engine.begin() as conn:
        conn.execute(insert(registry_objects_table).values(
            uuid="existing-uuid-123",
            object_type="note",
            title="Pre-existing Note",
            source_system="manual",
            status="active"
        ))
        
    # 3. Run the migrations
    run_migrations(engine)
    
    # 4. Verify content_index table exists
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "content_index" in tables
    
    # 5. Verify the pre-existing registry data is preserved
    with engine.begin() as conn:
        res = conn.execute(select(registry_objects_table)).fetchall()
        assert len(res) == 1
        # ID is column 0, Title is column 3
        assert res[0][3] == "Pre-existing Note"


def test_markdown_indexing_lifecycle_and_search(tmp_path, db_session):
    """Verify standard markdown indexing, deduplication, updates, missing files, and case-insensitive search."""
    # Setup test notes
    note_file = tmp_path / "rag_note.md"
    note_file.write_text("Build a RAG system using local files.")
    
    registry = RegistryService(db_session)
    content_service = ContentService(db_session)
    
    # 1. Register the note object
    obj = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="RAG Note",
        source_system="markdown",
        location=str(note_file),
        status="active"
    ))
    
    # 2. Run index_object first time
    idx_entry = content_service.index_object(obj.id)
    assert idx_entry is not None
    assert idx_entry.object_id == obj.id
    assert idx_entry.content_type == "markdown"
    assert idx_entry.raw_text == "Build a RAG system using local files."
    assert idx_entry.word_count == 7
    assert idx_entry.index_version == "content_v0.1"
    assert idx_entry.content_hash != ""
    
    # 3. Re-running index does not duplicate or create new DB entries
    first_indexed_at = idx_entry.indexed_at
    idx_entry_dup = content_service.index_object(obj.id)
    assert idx_entry_dup.id == idx_entry.id
    assert idx_entry_dup.content_hash == idx_entry.content_hash
    assert idx_entry_dup.indexed_at == first_indexed_at
    
    # Verify count is 1
    count = db_session.query(DBContentIndex).filter(DBContentIndex.object_id == obj.id).count()
    assert count == 1
    
    # 4. Modifying file updates content hash
    note_file.write_text("Build a RAG system using local files and SQLite LIKE.")
    # Re-index
    idx_entry_updated = content_service.index_object(obj.id)
    assert idx_entry_updated is not None
    assert idx_entry_updated.id == idx_entry.id
    assert idx_entry_updated.raw_text == "Build a RAG system using local files and SQLite LIKE."
    assert idx_entry_updated.word_count == 10
    assert idx_entry_updated.content_hash != idx_entry.content_hash
    
    # 5. Missing source files handled safely
    os.remove(note_file)
    idx_entry_missing = content_service.index_object(obj.id)
    assert idx_entry_missing is None
    
    # Verify the previous content_index remains intact (Derived deleting content_index never deletes registry)
    retained_idx = db_session.query(DBContentIndex).filter(DBContentIndex.object_id == obj.id).first()
    assert retained_idx is not None
    assert retained_idx.raw_text == "Build a RAG system using local files and SQLite LIKE."
    
    # 6. Case-insensitive search finds text inside notes
    search_results = content_service.search_content("sqlite")
    assert len(search_results) == 1
    found_obj, found_idx = search_results[0]
    assert found_obj.id == obj.id
    assert "sqlite" in found_idx.raw_text.lower()


@pytest.fixture
def cli_runner_content(db_session):
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


def test_cli_content_commands(tmp_path, db_session, cli_runner_content):
    """Verify Typer CLI commands 'index', 'content search', and 'content show' work with correct format."""
    note_file = tmp_path / "cli_note.md"
    note_file.write_text("DeepCore memory layer supports CLI index.")
    
    registry = RegistryService(db_session)
    obj = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="CLI Note",
        source_system="markdown",
        location=str(note_file),
        status="active"
    ))
    
    # 1. Test 'deepcore index'
    result_index = cli_runner_content.invoke(app, ["index"])
    assert result_index.exit_code == 0
    assert "DeepCore Content Index" in result_index.stdout
    assert "Objects scanned:\n1" in result_index.stdout
    assert "Indexed:\n1" in result_index.stdout
    assert "Skipped:\n0" in result_index.stdout
    
    # 2. Test 'deepcore content search' (case-insensitive + snippet verify)
    result_search = cli_runner_content.invoke(app, ["content", "search", "cli"])
    assert result_search.exit_code == 0
    assert "ID | TITLE | MATCH" in result_search.stdout
    assert "------------------------------------" in result_search.stdout
    assert f"{obj.id} | CLI Note | ..." in result_search.stdout
    
    # 3. Test 'deepcore content show'
    result_show = cli_runner_content.invoke(app, ["content", "show", str(obj.id)])
    assert result_show.exit_code == 0
    assert "DeepCore memory layer supports CLI index." in result_show.stdout

    # 4. Test 'deepcore content show' with uuid
    result_show_uuid = cli_runner_content.invoke(app, ["content", "show", obj.uuid])
    assert result_show_uuid.exit_code == 0
    assert "DeepCore memory layer supports CLI index." in result_show_uuid.stdout


def test_stable_database_path_determination(tmp_path, monkeypatch):
    """Verify that deepcore settings default to expand ~ to ~/.deepcore/deepcore.db and handle local migrations."""
    # 1. Setup mock environment
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("DEEPCORE_DB_PATH", raising=False)
    
    # Create old local database file
    local_db = tmp_path / "deepcore.db"
    local_db.write_text("pre-existing sqlite data")
    
    # Change current working directory to our mock temp directory
    monkeypatch.chdir(tmp_path)
    
    # 2. Instantiate Settings to trigger path calculation & migration
    from deepcore.config import Settings
    s = Settings()
    
    # 3. Assertions
    expected_path = os.path.join(str(tmp_path), ".deepcore", "deepcore.db")
    assert s.DB_PATH == expected_path
    
    # Verify migration copy succeeded
    assert os.path.exists(expected_path)
    with open(expected_path, "r") as f:
        assert f.read() == "pre-existing sqlite data"

