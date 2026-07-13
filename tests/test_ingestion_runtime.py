import pytest
from deepcore.runtime.ingestion.runtime import IngestionRuntime
from deepcore.runtime.ingestion.callbacks import IngestionCallback
from deepcore.core.providers.markdown import MarkdownProvider
from deepcore.core.providers.base import SyncResult

class MockCallback:
    def __init__(self):
        self.called = False
        self.sync_result = None

    def __call__(self, db, sync_result):
        self.called = True
        self.sync_result = sync_result


def test_ingestion_runtime_provider_and_callback_registration():
    """Verify that IngestionRuntime registers providers and callbacks correctly."""
    runtime = IngestionRuntime()
    runtime.register_provider("markdown", MarkdownProvider)
    
    callback = MockCallback()
    runtime.register_callback(callback)

    assert "markdown" in runtime._providers
    assert runtime._providers["markdown"] == MarkdownProvider
    assert len(runtime._callbacks) == 1
    assert runtime._callbacks[0] == callback


def test_ingestion_runtime_sync_orchestration(client, staged_notes_dir, db_session):
    """Verify that IngestionRuntime orchestrates sync and executes registered callbacks with SyncResult."""
    runtime = IngestionRuntime()
    runtime.register_provider("markdown", MarkdownProvider)
    
    callback = MockCallback()
    runtime.register_callback(callback)

    # Trigger sync through the runtime directly
    sync_run = runtime.sync_provider("markdown", db_session, staged_notes_dir)

    # Verify that the sync run was recorded and stats populated
    assert sync_run.provider == "markdown"
    assert sync_run.source_location == staged_notes_dir
    assert sync_run.status == "success"
    assert sync_run.objects_scanned == 3
    assert sync_run.objects_created == 3

    # Verify callback execution
    assert callback.called is True
    assert callback.sync_result is not None
    assert isinstance(callback.sync_result, SyncResult)
    assert callback.sync_result.scanned == 3
    assert len(callback.sync_result.created) == 3
    assert len(callback.sync_result.updated) == 0
    assert len(callback.sync_result.existing) == 0
    assert len(callback.sync_result.missing) == 0


def test_api_delegates_to_runtime(client, staged_notes_dir):
    """Verify that the API route invokes the runtime and returns a successful response."""
    payload = {"path": staged_notes_dir}
    response = client.post("/api/providers/markdown/sync", json=payload)
    assert response.status_code == 200
    
    sync_run = response.json()
    assert sync_run["provider"] == "markdown"
    assert sync_run["objects_scanned"] == 3
    assert sync_run["objects_created"] == 3
