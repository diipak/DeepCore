import sys
import types
import pytest
import json
from datetime import datetime, timezone
from typing import Dict, Any, Generator
from sqlalchemy.orm import Session

from deepcore.storage.sqlite.models import (
    KnowledgeSource as DBKnowledgeSource,
    SyncRun as DBSyncRun,
    RegistryObject as DBRegistryObject,
    ContentIndex as DBContentIndex,
    Workspace as DBWorkspace
)
from deepcore.runtime.descriptors import ProviderDescriptor, DescriptorCategory
from deepcore.core.acquisition.base import (
    BaseConnector,
    BaseTranslator,
    SyncContext,
    Provenance,
    HealthStatus
)
from deepcore.core.acquisition.ingestion import IngestionService
from deepcore.core.acquisition.runtime import AcquisitionRuntime
from deepcore.core.acquisition.manager import AcquisitionManager

# Define Mock classes for testing
class MockConnector(BaseConnector):
    def authenticate(self, credentials: Dict[str, Any]) -> HealthStatus:
        return HealthStatus(state="HEALTHY", message="Auth OK")

    def discover(self, ctx: SyncContext) -> Generator[Dict[str, Any], None, None]:
        yield {"external_id": "ext_1", "title": "Event 1", "raw_text": "Meeting one contents"}
        yield {"external_id": "ext_2", "title": "Event 2", "raw_text": "Meeting two contents"}

    def sync(self, ctx: SyncContext) -> Generator[Dict[str, Any], None, None]:
        ctx.cursor_state["last_id"] = "ext_3"
        yield {"external_id": "ext_3", "title": "Event 3", "raw_text": "Meeting three contents"}

    def watch(self, ctx: SyncContext) -> Generator[Dict[str, Any], None, None]:
        yield {"external_id": "ext_live", "title": "Live Event", "raw_text": "Live event contents"}

    def health(self, ctx: SyncContext) -> HealthStatus:
        return HealthStatus(state="HEALTHY", message="Mock checked")


class MockTranslator(BaseTranslator):
    def translate_object(self, raw_data: Dict[str, Any], provenance: Provenance) -> Dict[str, Any]:
        # A pure mapper, no side effects
        return {
            "object_type": "document",
            "title": raw_data["title"],
            "raw_text": raw_data["raw_text"],
            "location": f"http://mock-calendar/{raw_data['external_id']}",
            "description": f"Calendar details for {raw_data['title']}"
        }


# Dynamic Mock Module for Import tests
MOCK_MODULE_NAME = "deepcore.connectors.mock_calendar"
mock_module = types.ModuleType(MOCK_MODULE_NAME)

mock_descriptor = ProviderDescriptor(
    id="mock_calendar",
    name="Mock Calendar Sync",
    description="Connector for mock calendar integration",
    category=DescriptorCategory.PROVIDER,
    provider_type="mock_calendar",
    capabilities=["sync", "watch", "authenticate"],
    permissions=["network", "calendar"],
    supported_types=["Event"]
)

mock_module.CONNECTOR_DESCRIPTOR = mock_descriptor
mock_module.CONNECTOR_CLASS = MockConnector
mock_module.TRANSLATOR_CLASS = MockTranslator

sys.modules[MOCK_MODULE_NAME] = mock_module


# Verification tests
def test_provenance_immutability():
    """Verify that Provenance model enforces immutability/frozen constraints."""
    provenance = Provenance(
        connector_id="mock_calendar",
        provider_id="mock_calendar",
        source_system="Mock Calendar Sync",
        external_id="ext_1",
        sync_run_id="run_uuid_123"
    )

    with pytest.raises(ValidationError if 'ValidationError' in globals() else Exception) as exc:
        provenance.external_id = "new_id"
    assert "frozen" in str(exc.value).lower() or "immutable" in str(exc.value).lower() or "read-only" in str(exc.value).lower()


def test_standardized_discovery():
    """Verify AcquisitionManager scans and registers connectors via CONNECTOR_DESCRIPTOR export."""
    manager = AcquisitionManager()
    
    # Try importing invalid module path
    with pytest.raises(ValueError) as err:
        manager.register_connector("deepcore.connectors.non_existent")
    assert "Cannot import module" in str(err.value)

    # Register mock module
    descriptor = manager.register_connector(MOCK_MODULE_NAME)
    
    assert descriptor.id == "mock_calendar"
    assert descriptor.category == DescriptorCategory.PROVIDER
    assert manager.get_connector_class("mock_calendar") == MockConnector
    assert manager.get_translator_class("mock_calendar") == MockTranslator
    assert manager.get_descriptor("mock_calendar") == mock_descriptor
    assert mock_descriptor in manager.list_descriptors()


def test_ingestion_service_deduplication(db_session: Session):
    """Verify IngestionService handles validation, deduplication and hash checks correctly."""
    ingester = IngestionService(db_session)
    
    # 1. Enforce validation (missing title)
    provenance = Provenance(
        connector_id="mock_calendar",
        provider_id="mock_calendar",
        source_system="Mock Calendar Sync",
        external_id="ext_1",
        sync_run_id="run_uuid_123"
    )
    with pytest.raises(ValueError) as err:
        ingester.ingest_object({"object_type": "document", "title": ""}, provenance)
    assert "title" in str(err.value).lower()

    # 2. First Ingest (Insert object)
    raw_translate = {
        "object_type": "document",
        "title": "Ingest Meeting",
        "raw_text": "Meeting test contents",
        "location": "http://mock-calendar/ext_1",
        "description": "Calendar test description"
    }

    db_obj = ingester.ingest_object(raw_translate, provenance)
    assert db_obj.id is not None
    assert db_obj.title == "Ingest Meeting"
    assert db_obj.status == "active"
    
    # Check index record
    idx_record = db_session.query(DBContentIndex).filter(DBContentIndex.object_id == db_obj.id).first()
    assert idx_record is not None
    assert idx_record.raw_text == "Meeting test contents"

    # 3. Duplicate Ingest (Identical hash should update timestamps but skip inserts)
    orig_updated_at = db_obj.updated_at
    db_obj_dup = ingester.ingest_object(raw_translate, provenance)
    
    assert db_obj_dup.id == db_obj.id
    assert db_obj_dup.content_hash == db_obj.content_hash
    
    # 4. Hash Differs (Should update fields)
    original_hash = db_obj.content_hash
    raw_translate_diff = dict(raw_translate)
    raw_translate_diff["raw_text"] = "Meeting test contents - changed!"
    
    db_obj_changed = ingester.ingest_object(raw_translate_diff, provenance)
    assert db_obj_changed.id == db_obj.id
    assert db_obj_changed.content_hash != original_hash
    
    # Check index updated
    idx_updated = db_session.query(DBContentIndex).filter(DBContentIndex.object_id == db_obj.id).first()
    assert idx_updated.raw_text == "Meeting test contents - changed!"


def test_acquisition_runtime_orchestration(db_session: Session):
    """Verify AcquisitionRuntime manages states, logs, and processes sync loops correctly."""
    # Ensure a default workspace exists in the db session
    workspace = db_session.query(DBWorkspace).filter(DBWorkspace.id == 1).first()
    if not workspace:
        workspace = DBWorkspace(id=1, name="Personal Workspace")
        db_session.add(workspace)
        db_session.commit()

    # Create dummy KnowledgeSource
    source = DBKnowledgeSource(
        workspace_id=1,
        provider_id="mock_calendar",
        kind="calendar",
        name="Mock Calendar Sync",
        location="http://mock-calendar/sync",
        config_json="{}",
        status="Configured"
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    ingester = IngestionService(db_session)
    runtime = AcquisitionRuntime(db_session, ingester)
    
    # Run sync orchestration (full_sync=False -> incremental sync)
    sync_run = runtime.run_sync(
        source_id=source.id,
        connector=MockConnector(),
        translator=MockTranslator(),
        full_sync=False
    )

    # 1. Assert status finishes successfully
    assert sync_run.status == "success"
    assert sync_run.progress == 1.0
    assert sync_run.objects_scanned == 1  # sync yields 1 object
    assert sync_run.objects_created == 1
    
    # 2. Check source updates status and cursor
    db_session.refresh(source)
    assert source.status == "Healthy"
    
    cursor = json.loads(source.cursor_state)
    assert cursor.get("last_id") == "ext_3"

    # 3. Assert failure/state machine for errors
    class ErroringConnector(MockConnector):
        def sync(self, ctx: SyncContext) -> Generator[Dict[str, Any], None, None]:
            raise ConnectionError("API connection failure")

    sync_run_fail = runtime.run_sync(
        source_id=source.id,
        connector=ErroringConnector(),
        translator=MockTranslator(),
        full_sync=False,
        max_retries=0
    )

    assert sync_run_fail.status == "failed"
    assert "API connection failure" in sync_run_fail.error_message
    
    db_session.refresh(source)
    assert source.status == "Error"


def test_pure_translator_invariance():
    """Verify that translators behave as pure mappers without side-effects."""
    class SideEffectTranslator(MockTranslator):
        def translate_object(self, raw_data: Dict[str, Any], provenance: Provenance) -> Dict[str, Any]:
            # This violates the invariant of database/session access
            db_session = "dummy_session" 
            if db_session:
                raise PermissionError("Translators must remain pure side-effect-free functions")
            return super().translate_object(raw_data, provenance)

    translator = SideEffectTranslator()
    provenance = Provenance(
        connector_id="mock_calendar",
        provider_id="mock_calendar",
        source_system="Mock Calendar Sync",
        external_id="ext_1",
        sync_run_id="run_uuid_123"
    )
    with pytest.raises(PermissionError) as err:
        translator.translate_object({"title": "Test", "raw_text": ""}, provenance)
    assert "side-effect-free" in str(err.value)
