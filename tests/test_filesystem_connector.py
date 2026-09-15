import os
import json
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from deepcore.storage.sqlite.models import (
    KnowledgeSource as DBKnowledgeSource,
    RegistryObject as DBRegistryObject,
    ContentIndex as DBContentIndex,
    Workspace as DBWorkspace
)
from deepcore.core.acquisition.base import SyncContext
from deepcore.core.acquisition.ingestion import IngestionService
from deepcore.core.acquisition.runtime import AcquisitionRuntime
from deepcore.core.acquisition.manager import AcquisitionManager
from deepcore.core.registry.service import RegistryService
from deepcore.connectors.filesystem.connector import FilesystemConnector
from deepcore.connectors.filesystem.translator import MarkdownTranslator
from deepcore.connectors.filesystem.descriptor import CONNECTOR_DESCRIPTOR

def test_filesystem_descriptor_metadata():
    """Verify descriptor capabilities and properties matching amendments."""
    assert CONNECTOR_DESCRIPTOR.id == "filesystem"
    assert "sync" in CONNECTOR_DESCRIPTOR.capabilities
    # Ensure watch is not advertised in capabilities in this milestone (Amendment 3)
    assert "watch" not in CONNECTOR_DESCRIPTOR.capabilities
    assert "filesystem" in CONNECTOR_DESCRIPTOR.permissions
    assert "File" in CONNECTOR_DESCRIPTOR.supported_types


def test_filesystem_health_checks(tmp_path):
    """Verify FilesystemConnector health checks for directories, existence, and permissions."""
    connector = FilesystemConnector()
    
    # 1. Invalid configuration (missing path)
    ctx_invalid = SyncContext(workspace_id=1, source_id=1, config={}, credentials={})
    health_invalid = connector.health(ctx_invalid)
    assert health_invalid.state == "CRITICAL"
    assert "path" in health_invalid.message.lower()
    assert "not specified" in health_invalid.message.lower()

    # 2. Non-existent directory path
    fake_path = str(tmp_path / "does_not_exist")
    ctx_fake = SyncContext(workspace_id=1, source_id=1, config={"path": fake_path}, credentials={})
    health_fake = connector.health(ctx_fake)
    assert health_fake.state == "CRITICAL"
    assert "does not exist" in health_fake.message

    # 3. Path is a file, not a directory
    temp_file = tmp_path / "file.txt"
    temp_file.write_text("hello")
    ctx_file = SyncContext(workspace_id=1, source_id=1, config={"path": str(temp_file)}, credentials={})
    health_file = connector.health(ctx_file)
    assert health_file.state == "CRITICAL"
    assert "is not a directory" in health_file.message

    # 4. Valid directory health check
    valid_dir = tmp_path / "valid_notes"
    valid_dir.mkdir()
    ctx_valid = SyncContext(workspace_id=1, source_id=1, config={"path": str(valid_dir)}, credentials={})
    health_valid = connector.health(ctx_valid)
    assert health_valid.state == "HEALTHY"
    assert "prior synchronization" in health_valid.message


def test_filesystem_discovery_and_ignores(staged_notes_dir):
    """Verify filesystem connector scans recursively and ignores dot/hidden folders correctly."""
    connector = FilesystemConnector()
    ctx = SyncContext(workspace_id=1, source_id=1, config={"path": staged_notes_dir}, credentials={})
    
    discovered_files = list(connector.discover(ctx))
    filenames = [f["filename"] for f in discovered_files]

    # Verify matching files
    assert len(discovered_files) == 3
    assert "note1.md" in filenames
    assert "note2.MD" in filenames
    assert "note3.md" in filenames

    # Verify ignores (hidden / txt files excluded)
    assert "draft.txt" not in filenames
    assert "ignored_note.md" not in filenames
    assert "deleted_note.md" not in filenames
    
    # Check that active file paths were recorded in the cursor
    assert len(ctx.cursor_state["active_ids"]) == 3
    assert "note1.md" in ctx.cursor_state["active_ids"]


def test_pure_markdown_translator(staged_notes_dir):
    """Verify pure MarkdownTranslator extracts content and generates provenance/hash correctly."""
    translator = MarkdownTranslator()
    from deepcore.core.acquisition.base import Provenance
    provenance = Provenance(
        connector_id="filesystem",
        provider_id="filesystem",
        source_system="Personal Notes Source",
        external_id="note1.md",
        sync_run_id="sync_run_123"
    )

    note1_abs = os.path.join(staged_notes_dir, "note1.md")
    raw_file = {
        "absolute_path": note1_abs,
        "relative_path": "note1.md",
        "filename": "note1.md",
        "file_size": 12,
        "created_at_ts": 1700000000.0,
        "modified_at_ts": 1700000001.0,
        "parent_folder": "Notes"
    }

    translated = translator.translate_object(raw_file, provenance)

    assert translated["object_type"] == "note"
    assert translated["title"] == "note1"
    assert translated["location"] == note1_abs
    assert translated["raw_text"] == "Hello note 1"
    assert translated["content_hash"] is not None
    
    # Verify metadata formatting
    metadata = json.loads(translated["metadata_json"])
    assert metadata["folder"] == "Notes"
    assert metadata["viewer_hint"] == "obsidian_compatible"


def test_full_filesystem_sync_orchestration(db_session: Session, staged_notes_dir):
    """Verify full orchestration loop: Connector -> Translator -> IngestionService -> DB."""
    # Ensure default workspace
    ws = db_session.query(DBWorkspace).filter(DBWorkspace.id == 1).first()
    if not ws:
        ws = DBWorkspace(id=1, name="Personal Workspace")
        db_session.add(ws)
        db_session.commit()

    # Create configured KnowledgeSource
    source = DBKnowledgeSource(
        workspace_id=1,
        provider_id="filesystem",
        kind="filesystem",
        name="Personal Vault",
        location=staged_notes_dir,
        config_json=json.dumps({"path": staged_notes_dir}),
        status="Configured"
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    connector = FilesystemConnector()
    translator = MarkdownTranslator()
    ingester = IngestionService(db_session)
    runtime = AcquisitionRuntime(db_session, ingester)

    # 1. Run Ingestion Sync
    sync_run = runtime.run_sync(
        source_id=source.id,
        connector=connector,
        translator=translator,
        full_sync=True
    )

    assert sync_run.status == "success"
    assert sync_run.objects_scanned == 3
    assert sync_run.objects_created == 3

    # Check that database records exist
    notes = db_session.query(DBRegistryObject).filter(
        DBRegistryObject.workspace_id == 1,
        DBRegistryObject.source_id == source.id
    ).all()
    assert len(notes) == 3

    # Verify content index database writes
    idx = db_session.query(DBContentIndex).filter(DBContentIndex.object_id == notes[0].id).first()
    assert idx is not None
    assert idx.raw_text in ["Hello note 1", "Case insensitive test", "Nested markdown note"]


def test_incremental_sync_and_deletions(db_session: Session, staged_notes_dir):
    """Verify incremental sync only processes updates, and deleted files are marked missing."""
    # Ensure default workspace
    ws = db_session.query(DBWorkspace).filter(DBWorkspace.id == 1).first()
    if not ws:
        ws = DBWorkspace(id=1, name="Personal Workspace")
        db_session.add(ws)
        db_session.commit()

    source = DBKnowledgeSource(
        workspace_id=1,
        provider_id="filesystem",
        kind="filesystem",
        name="Personal Vault",
        location=staged_notes_dir,
        config_json=json.dumps({"path": staged_notes_dir}),
        status="Configured"
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    connector = FilesystemConnector()
    translator = MarkdownTranslator()
    ingester = IngestionService(db_session)
    runtime = AcquisitionRuntime(db_session, ingester)

    # 1. Initial full scan sync
    runtime.run_sync(source.id, connector, translator, full_sync=True)

    # 2. Modify one file on disk
    note1_path = os.path.join(staged_notes_dir, "note1.md")
    note1_orig_stat = os.stat(note1_path)
    
    # Sleep briefly to ensure mtime changes
    import time
    time.sleep(1.0)
    with open(note1_path, "w") as f:
        f.write("Hello note 1 - MODIFIED!")

    # 3. Run incremental sync
    sync_run_inc = runtime.run_sync(source.id, connector, translator, full_sync=False)
    
    # Should only scan the modified file
    assert sync_run_inc.objects_scanned == 1
    assert sync_run_inc.objects_updated == 1
    assert sync_run_inc.objects_created == 0

    # 4. Delete one file and verify deletion is handled via active_ids comparison
    note3_path = os.path.join(staged_notes_dir, "nested", "note3.md")
    os.remove(note3_path)

    # Execute sync scan (needed to rebuild cursor active_ids)
    runtime.run_sync(source.id, connector, translator, full_sync=False)

    # Run delete marking (identical to CLI implementation)
    db_session.refresh(source)
    cursor_state = json.loads(source.cursor_state or "{}")
    active_ids = cursor_state.get("active_ids", [])
    
    assert "nested/note3.md" not in active_ids
    
    reg_service = RegistryService(db_session, workspace_id=1)
    missing_count = reg_service.mark_missing_objects(source.name, source.location, active_ids)
    
    assert missing_count == 1

    # Verify record status changed to 'missing'
    deleted_obj = db_session.query(DBRegistryObject).filter(
        DBRegistryObject.source_id == source.id,
        DBRegistryObject.external_id == "nested/note3.md"
    ).first()
    assert deleted_obj.status == "missing"
