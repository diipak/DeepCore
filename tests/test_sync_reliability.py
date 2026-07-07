import json
import os
from datetime import datetime, timezone
import pytest
from typer.testing import CliRunner

from deepcore.cli.main import app
from deepcore.core.providers.markdown import MarkdownProvider
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObjectCreate
from deepcore.storage.sqlite.models import RegistryObject as DBRegistryObject, SyncRun as DBSyncRun

@pytest.fixture
def cli_runner(db_session):
    """Provides a CliRunner instance with the SessionLocal db patched to the test transactional session."""
    from unittest.mock import patch
    class NoCloseSession:
        def __init__(self, session):
            self.session = session
        def __getattr__(self, name):
            return getattr(self.session, name)
        def close(self):
            pass

    mock_sess = NoCloseSession(db_session)
    with patch("deepcore.cli.main.SessionLocal", return_value=mock_sess):
        yield CliRunner()

def test_fingerprint_move_detection(tmp_path, db_session):
    """Verify that renaming a file updates the existing registry object without duplicating it."""
    root = tmp_path / "Notes"
    root.mkdir()
    
    note_file = root / "fingerprint.md"
    note_file.write_text("Secret content")
    
    service = RegistryService(db_session)
    provider = MarkdownProvider(root_path=str(root))
    
    # 1. First sync registers the note
    provider.sync(service)
    db_objs = service.list_objects(filters={"source_system": "markdown"})
    assert len(db_objs) == 1
    original_obj = db_objs[0]
    assert original_obj.external_id == "fingerprint.md"
    assert original_obj.status == "active"
    assert original_obj.content_hash is not None
    
    # 2. Delete the original file and create renamed file with same content
    note_file.unlink()
    renamed_file = root / "renamed.md"
    renamed_file.write_text("Secret content")
    
    # 3. Sync again
    provider.sync(service)
    
    # Verify no new record was created, but the existing record updated its path details
    db_objs = service.list_objects(filters={"source_system": "markdown"})
    assert len(db_objs) == 1
    updated_obj = db_objs[0]
    assert updated_obj.id == original_obj.id
    assert updated_obj.external_id == "renamed.md"
    assert updated_obj.title == "renamed"
    assert updated_obj.status == "active"

def test_copy_detection_separate_objects(tmp_path, db_session):
    """Verify that having the same content in active notes registers them as separate copies."""
    root = tmp_path / "Notes"
    root.mkdir()
    
    note1 = root / "note1.md"
    note1.write_text("Identical text content")
    
    service = RegistryService(db_session)
    provider = MarkdownProvider(root_path=str(root))
    
    # First sync
    provider.sync(service)
    
    # Create copy file while original is still active
    note2 = root / "note2.md"
    note2.write_text("Identical text content")
    
    # Second sync
    provider.sync(service)
    
    # Should create a separate registry object since the first note is active
    db_objs = service.list_objects(filters={"source_system": "markdown"})
    assert len(db_objs) == 2
    titles = {obj.title for obj in db_objs}
    assert titles == {"note1", "note2"}

def test_missing_detection_scoping(tmp_path, db_session):
    """Verify that deleting a file marks it missing, isolated by root path directory scoping."""
    root_a = tmp_path / "NotesA"
    root_a.mkdir()
    root_b = tmp_path / "NotesB"
    root_b.mkdir()
    
    note_a = root_a / "noteA.md"
    note_a.write_text("Content A")
    
    note_b = root_b / "noteB.md"
    note_b.write_text("Content B")
    
    service = RegistryService(db_session)
    
    # Sync both folders
    provider_a = MarkdownProvider(root_path=str(root_a))
    provider_b = MarkdownProvider(root_path=str(root_b))
    
    provider_a.sync(service)
    provider_b.sync(service)
    
    # Delete noteA only
    note_a.unlink()
    
    # Resync folder A
    provider_a.sync(service)
    
    # noteA must be marked missing, noteB must remain active
    objs = service.list_objects(filters={"source_system": "markdown"})
    assert len(objs) == 2
    
    obj_a = next(o for o in objs if o.title == "noteA")
    obj_b = next(o for o in objs if o.title == "noteB")
    
    assert obj_a.status == "missing"
    assert obj_b.status == "active"

def test_sync_history_run_recording(tmp_path, db_session):
    """Verify that running a sync registers a sync history run record in database."""
    root = tmp_path / "Notes"
    root.mkdir()
    (root / "note.md").write_text("Content")
    
    service = RegistryService(db_session)
    provider = MarkdownProvider(root_path=str(root))
    
    provider.sync(service)
    
    # Query runs
    runs = service.list_sync_runs()
    assert len(runs) == 1
    run = runs[0]
    assert run.provider == "markdown"
    assert run.source_location == str(root)
    assert run.objects_scanned == 1
    assert run.objects_created == 1
    assert run.objects_existing == 0
    assert run.objects_updated == 0
    assert run.objects_missing == 0
    assert run.status == "success"

def test_cli_sync_history_command(tmp_path, cli_runner):
    """Verify that deepcore sync history prints the recorded runs list."""
    # Run sync CLI command to create history entry
    root = tmp_path / "Notes"
    root.mkdir()
    (root / "note.md").write_text("Content")
    
    cli_runner.invoke(app, ["sync", "markdown", str(root)])
    
    # Check sync history command
    result = cli_runner.invoke(app, ["sync", "history"])
    assert result.exit_code == 0
    assert "DATE | PROVIDER | SCANNED | NEW | STATUS" in result.stdout
    assert "markdown" in result.stdout
    assert "success" in result.stdout


def test_run_migrations_upgrades_schema(tmp_path):
    """Verify that run_migrations successfully upgrades an old schema missing content_hash."""
    from sqlalchemy import create_engine, Table, MetaData, Column, Integer, String, DateTime, text
    from deepcore.storage.sqlite.models import run_migrations, get_utc_now
    
    # 1. Create a database file with an old schema lacking content_hash
    db_file = tmp_path / "old_deepcore.db"
    db_url = f"sqlite:///{db_file}"
    old_engine = create_engine(db_url)
    
    metadata = MetaData()
    # Define registry_objects table WITHOUT content_hash column
    old_table = Table(
        "registry_objects",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
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
        Column("created_at", DateTime, default=get_utc_now, nullable=False),
        Column("updated_at", DateTime, default=get_utc_now, nullable=False)
    )
    metadata.create_all(bind=old_engine)
    
    # Verify that content_hash does not exist yet
    from sqlalchemy import inspect
    inspector = inspect(old_engine)
    columns = [col["name"] for col in inspector.get_columns("registry_objects")]
    assert "content_hash" not in columns
    
    # 2. Run run_migrations() on the old database
    run_migrations(old_engine)
    
    # 3. Verify that content_hash exists now
    inspector = inspect(old_engine)
    columns_after = [col["name"] for col in inspector.get_columns("registry_objects")]
    assert "content_hash" in columns_after
    
    # Verify we can execute a query containing content_hash
    with old_engine.connect() as conn:
        res = conn.execute(text("SELECT content_hash FROM registry_objects"))
        assert res is not None
