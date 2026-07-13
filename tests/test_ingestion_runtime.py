import pytest
from deepcore.runtime.ingestion.runtime import IngestionRuntime
from deepcore.runtime.processing.runtime import ProcessingRuntime
from deepcore.core.providers.markdown import MarkdownProvider
from deepcore.core.providers.base import SyncResult

def test_ingestion_runtime_provider_registration():
    """Verify that IngestionRuntime registers providers correctly."""
    processing_runtime = ProcessingRuntime()
    runtime = IngestionRuntime(processing_runtime)
    runtime.register_provider("markdown", MarkdownProvider)

    assert "markdown" in runtime._providers
    assert runtime._providers["markdown"] == MarkdownProvider
    assert runtime.processing_runtime == processing_runtime


def test_ingestion_runtime_sync_orchestration(client, staged_notes_dir, db_session):
    """Verify that IngestionRuntime orchestrates sync through its ProcessingRuntime."""
    processing_runtime = ProcessingRuntime()
    runtime = IngestionRuntime(processing_runtime)
    runtime.register_provider("markdown", MarkdownProvider)

    # Trigger sync through the runtime directly
    sync_run = runtime.sync_provider("markdown", db_session, staged_notes_dir)

    # Verify that the sync run was recorded and stats populated
    assert sync_run.provider == "markdown"
    assert sync_run.source_location == staged_notes_dir
    assert sync_run.status == "success"
    assert sync_run.objects_scanned == 3
    assert sync_run.objects_created == 3


def test_api_delegates_to_runtime(client, staged_notes_dir):
    """Verify that the API route invokes the runtime and returns a successful response."""
    payload = {"path": staged_notes_dir}
    response = client.post("/api/providers/markdown/sync", json=payload)
    assert response.status_code == 200
    
    sync_run = response.json()
    assert sync_run["provider"] == "markdown"
    assert sync_run["objects_scanned"] == 3
    assert sync_run["objects_created"] == 3
