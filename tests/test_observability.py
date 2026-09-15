import pytest
from unittest.mock import MagicMock
from deepcore.core.observability.service import ObservabilityService
from deepcore.runtime.processing.runtime import ProcessingRuntime, ProcessingResult
from deepcore.runtime.processing.stages import ContentIndexStage
from deepcore.storage.sqlite.models import SyncRun


def test_observability_service_decoupling(db_session):
    """
    Verify that ObservabilityService is fully decoupled from the Application singleton,
    and isolates run results properly per workspace.
    """
    service = ObservabilityService()
    
    # Create mock processing result for Workspace A
    res_a = ProcessingResult()
    res_a.stage_status["content_indexing"] = "success"
    res_a.stage_durations["content_indexing"] = 0.45
    service.publish_processing_result(1, res_a)

    # Create mock processing result for Workspace B
    res_b = ProcessingResult()
    res_b.stage_status["content_indexing"] = "failed"
    res_b.stage_durations["content_indexing"] = 1.2
    res_b.failures.append({"stage_id": "content_indexing", "error": "Disk full"})
    service.publish_processing_result(2, res_b)

    # Create mock application container (mocking only the public APIs)
    mock_stage = MagicMock()
    mock_stage.id = "content_indexing"
    mock_stage.name = "Content Indexing"
    mock_stage.order = 100
    mock_stage.enabled = True

    mock_desc = MagicMock()
    mock_desc.id = "markdown_provider"
    mock_desc.name = "Markdown Sync"
    mock_desc.category.value = "provider"
    mock_desc.descriptor_version = "1.0.0"
    mock_desc.implementation_version = "1.0.0"
    mock_desc.configurable = True
    mock_desc.tags = ["fs"]

    mock_app = MagicMock()
    mock_app.processing_service.get_registered_stages.return_value = [mock_stage]
    mock_app.capabilities_service.registry.list.return_value = [mock_desc]
    mock_app.tool_registry.list_tools.return_value = []
    mock_app.skill_registry.list_skills.return_value = []

    # Insert a mock SyncRun into the DB for both workspaces
    run_a = SyncRun(workspace_id=1, provider="markdown", status="success", objects_scanned=10)
    run_b = SyncRun(workspace_id=2, provider="markdown", status="failed", objects_scanned=5, errors_json='["Failed during indexing"]')
    db_session.add(run_a)
    db_session.add(run_b)
    db_session.commit()

    # Query observability data for workspace 1
    data_a = service.get_observability_data(1, db_session, mock_app)
    assert data_a is not None
    assert len(data_a["execution_history"]) > 0
    assert data_a["timeline"]["status"] == "success"
    
    # Confirm stage details match workspace 1's mock execution
    idx_stage_a = next(s for s in data_a["timeline"]["stages"] if s["id"] == "content_indexing")
    assert idx_stage_a["status"] == "success"
    assert idx_stage_a["duration_ms"] == 450.0
    assert len(idx_stage_a["errors"]) == 0

    # Query observability data for workspace 2
    data_b = service.get_observability_data(2, db_session, mock_app)
    assert data_b["timeline"]["status"] == "failed"
    
    # Confirm stage details match workspace 2's mock execution
    idx_stage_b = next(s for s in data_b["timeline"]["stages"] if s["id"] == "content_indexing")
    assert idx_stage_b["status"] == "failed"
    assert idx_stage_b["duration_ms"] == 1200.0
    assert "Disk full" in idx_stage_b["errors"]


def test_processing_runtime_injection():
    """
    Verify that ProcessingRuntime operates correctly with an injected ObservabilityService
    and exposes stages exclusively through public APIs.
    """
    mock_service = MagicMock()
    runtime = ProcessingRuntime(observability_service=mock_service)
    
    # Verify stages can be retrieved via public API
    stage = ContentIndexStage()
    runtime.register_stage(stage)
    
    stages = runtime.get_registered_stages()
    assert len(stages) == 1
    assert stages[0].id == stage.id

    # Verify execute publishes results to the service
    mock_db = MagicMock()
    mock_sync_result = MagicMock()
    mock_sync_result.created = []
    mock_sync_result.updated = []
    mock_sync_result.existing = []
    mock_sync_result.missing = []

    # Run execution and verify the publish mock call was invoked
    runtime.execute(mock_db, mock_sync_result, workspace_id=42)
    assert mock_service.publish_processing_result.called
    called_args = mock_service.publish_processing_result.call_args[0]
    assert called_args[0] == 42
    assert isinstance(called_args[1], ProcessingResult)


def test_api_observability_endpoint(client):
    """
    Verify the thin /api/system/observability route returns correct dynamic payloads
    matching the registered capability/descriptor registries.
    """
    # Create a workspace first to ensure context headers resolve
    ws_resp = client.post("/api/workspaces", json={"name": "Obs Workspace"})
    assert ws_resp.status_code == 200
    ws_uuid = ws_resp.json()["uuid"]

    # Call endpoint with headers
    headers = {"X-Workspace-UUID": ws_uuid}
    resp = client.get("/api/system/observability", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Verify runtimes registry details
    runtimes = data["registered_runtimes"]
    names = {rt["name"] for rt in runtimes}
    assert "Ingestion Runtime" in names
    assert "Processing Runtime" in names
    assert "Tool Runtime" in names
    assert "Skill Runtime" in names

    # Verify all 7 components are listed
    assert len(runtimes) == 7
    for rt in runtimes:
        assert "version" in rt
        assert "initialized" in rt
        assert "health" in rt
        assert "dependencies" in rt
        assert "capabilities" in rt

    # Verify capability registry has items
    assert len(data["capability_registry"]) > 0
    categories = {d["category"] for d in data["capability_registry"]}
    assert "provider" in categories
    assert "model" in categories
