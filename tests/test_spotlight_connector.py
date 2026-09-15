import os
import json
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from deepcore.storage.sqlite.models import (
    KnowledgeSource as DBKnowledgeSource,
    RegistryObject as DBRegistryObject,
    Workspace as DBWorkspace
)
from deepcore.core.acquisition.base import SyncContext, Provenance
from deepcore.core.acquisition.ingestion import IngestionService
from deepcore.core.acquisition.runtime import AcquisitionRuntime
from deepcore.connectors.spotlight.connector import SpotlightConnector
from deepcore.connectors.spotlight.translator import SpotlightTranslator
from deepcore.connectors.spotlight.schema import DiscoveredArtifact

def test_spotlight_descriptor_metadata():
    """Verify static connector capability parameters."""
    from deepcore.connectors.spotlight.descriptor import CONNECTOR_DESCRIPTOR
    assert CONNECTOR_DESCRIPTOR.id == "spotlight"
    assert "sync" in CONNECTOR_DESCRIPTOR.capabilities
    assert "filesystem" in CONNECTOR_DESCRIPTOR.permissions
    assert "spotlight" in CONNECTOR_DESCRIPTOR.permissions
    assert "DiscoveredArtifact" in CONNECTOR_DESCRIPTOR.supported_types


def test_spotlight_strategy_to_query_translation():
    """Verify mapping of high-level Discovery Strategies into native query syntax (Amendment 3)."""
    connector = SpotlightConnector()
    
    # 1. Test empty strategies translates to fallback wildcard query
    q_empty = connector._build_mdfind_query({})
    assert q_empty == 'kMDItemFSName == "*"'

    # 2. Test File Type strategy translation
    q_types = connector._build_mdfind_query({"file_types": [".md", ".pdf"]})
    assert q_types == '(kMDItemFSName == "*.md" || kMDItemFSName == "*.pdf")'

    # 3. Test Tags strategy translation
    q_tags = connector._build_mdfind_query({"tags": ["Work", "Finance"]})
    assert q_tags == '(kMDItemUserTags == "Work" || kMDItemUserTags == "Finance")'

    # 4. Test combination of strategies
    q_combined = connector._build_mdfind_query({"file_types": [".txt"], "tags": ["Draft"]})
    assert q_combined == '(kMDItemFSName == "*.txt") && (kMDItemUserTags == "Draft")'


def test_spotlight_health_check_states(tmp_path):
    """Verify health indicator mapping logic for mock configurations (Amendment 4)."""
    connector = SpotlightConnector()
    
    # 1. Unconfigured check
    ctx_unconfigured = SyncContext(workspace_id=1, source_id=1, config={}, credentials={})
    health_un = connector.health(ctx_unconfigured)
    assert health_un.state == "CRITICAL"
    assert health_un.details["Discovery Ready"] is False

    # 2. Configured check with a valid directory path
    valid_dir = str(tmp_path)
    ctx_configured = SyncContext(workspace_id=1, source_id=1, config={"search_path": valid_dir}, credentials={})
    health_ok = connector.health(ctx_configured)
    # Since health_ok state depends on OS platform capability, we check that it populates detail fields correctly
    assert "Index Available" in health_ok.details
    assert "Index Operational" in health_ok.details
    assert health_ok.details["Discovery Ready"] is True


def test_spotlight_translator_normalization():
    """Verify raw file data records parse into canonical DiscoveredArtifact models (Amendment 1)."""
    translator = SpotlightTranslator()
    provenance = Provenance(
        connector_id="spotlight",
        provider_id="spotlight",
        source_system="Local Spotlight",
        external_id="ext_sha",
        sync_run_id="run_1"
    )

    raw_item = {
        "absolute_path": "/Users/test/Documents/notes/finance.md",
        "filename": "finance.md",
        "modified_at_ts": 1700000000.0,
        "file_size": 1024,
        "tags": ["Work"]
    }

    artifact = translator.translate_object(raw_item, provenance)

    assert isinstance(artifact, DiscoveredArtifact)
    assert artifact.title == "finance"
    assert artifact.location == "/Users/test/Documents/notes/finance.md"
    assert artifact.mime_type == "text/markdown"
    assert artifact.size_bytes == 1024
    assert artifact.tags == ["Work"]
    assert len(artifact.uid) == 64 # SHA256 length


def test_spotlight_sync_classification_and_ingestion(db_session: Session, tmp_path):
    """Test full sync pipeline: file discovery -> translation -> runtime classification -> DB."""
    # Ensure workspace exists
    ws = db_session.query(DBWorkspace).filter(DBWorkspace.id == 1).first()
    if not ws:
        ws = DBWorkspace(id=1, name="Workspace 1")
        db_session.add(ws)
        db_session.commit()

    # Create dummy workspace files
    search_dir = tmp_path / "search_scope"
    search_dir.mkdir()
    
    note_file = search_dir / "todo.md"
    with open(note_file, "w") as f:
        f.write("# ToDo List\n- Finish connector integration.")

    txt_file = search_dir / "log.txt"
    with open(txt_file, "w") as f:
        f.write("System execution logs.")

    source = DBKnowledgeSource(
        workspace_id=1,
        provider_id="spotlight",
        kind="spotlight",
        name="Spotlight Search Scope",
        location=str(search_dir),
        config_json=json.dumps({
            "search_path": str(search_dir),
            "file_types": [".md", ".txt"]
        }),
        status="Configured"
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    connector = SpotlightConnector()
    translator = SpotlightTranslator()
    ingester = IngestionService(db_session)
    runtime = AcquisitionRuntime(db_session, ingester)

    # 1. Execute full sync
    sync_run = runtime.run_sync(source.id, connector, translator, full_sync=True)
    assert sync_run.status == "success"
    assert sync_run.objects_scanned == 2
    assert sync_run.objects_created == 2

    # Verify classification logic has mapped markdown to 'note' and txt to 'file' (Final Amendment)
    db_objs = db_session.query(DBRegistryObject).filter(DBRegistryObject.source_id == source.id).all()
    assert len(db_objs) == 2

    from deepcore.storage.sqlite.models import ContentIndex as DBContentIndex
    note_obj = next(o for o in db_objs if o.title == "todo")
    txt_obj = next(o for o in db_objs if o.title == "log")

    assert note_obj.object_type == "note"
    note_idx = db_session.query(DBContentIndex).filter(DBContentIndex.object_id == note_obj.id).first()
    assert note_idx is not None
    assert note_idx.raw_text == "# ToDo List\n- Finish connector integration."

    assert txt_obj.object_type == "file"
    txt_idx = db_session.query(DBContentIndex).filter(DBContentIndex.object_id == txt_obj.id).first()
    assert txt_idx is None  # Texts of non-notes are not loaded in default mapping

    # Verify root_path and mime_type inside metadata_json
    meta_note = json.loads(note_obj.metadata_json)
    assert meta_note["root_path"] == str(search_dir)
    assert meta_note["mime_type"] == "text/markdown"
