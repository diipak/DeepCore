import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from deepcore.api.main import app
from deepcore.core.acquisition.preview import PreviewService
from deepcore.core.objects.schemas import PreviewArtifactType, SyncRunState

@pytest.fixture
def temp_markdown_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = os.path.join(tmpdir, "doc1.md")
        with open(file1, "w") as f:
            f.write("# Doc 1\nHello world")
            
        file2 = os.path.join(tmpdir, "doc2.markdown")
        with open(file2, "w") as f:
            f.write("# Doc 2\nDeepCore offline database")
            
        file3 = os.path.join(tmpdir, "notes.txt")
        with open(file3, "w") as f:
            f.write("Ignore this")
            
        yield tmpdir

def test_preview_service(temp_markdown_dir):
    service = PreviewService()
    total = service.estimate_import(provider_id="markdown", location=temp_markdown_dir)
    preview = service.enumerate_preview(provider_id="markdown", location=temp_markdown_dir)
    assert total == 2
    assert len(preview) == 2
    
    types = [p.type for p in preview]
    assert all(t == PreviewArtifactType.NOTE for t in types)
    names = [p.name for p in preview]
    assert "doc1.md" in names
    assert "doc2.markdown" in names
    
    with pytest.raises(Exception):
        service.estimate_import(provider_id="markdown", location="/nonexistent/directory/path")

def test_connectors_api_lifecycle(temp_markdown_dir, client, db_session, monkeypatch):
    # Mock SessionLocal and BackgroundTasks to run synchronously within test transaction
    monkeypatch.setattr("deepcore.storage.sqlite.db.SessionLocal", lambda: db_session)
    from fastapi import BackgroundTasks
    monkeypatch.setattr(BackgroundTasks, "add_task", lambda self, func, *args, **kwargs: func(*args, **kwargs))
    
    # 1. Preview
    resp = client.post("/api/connectors/preview", json={
        "provider_id": "markdown",
        "location": temp_markdown_dir
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_artifacts"] == 2
    assert len(data["preview"]) == 2
    
    # 2. Register Connector
    resp = client.post("/api/connectors", json={
        "name": "Test Markdown Source",
        "provider_id": "markdown",
        "location": temp_markdown_dir,
        "kind": "filesystem"
    })
    assert resp.status_code == 200
    connector = resp.json()
    assert connector["name"] == "Test Markdown Source"
    assert connector["status"] == "Configured"
    connector_id = connector["id"]
    
    # 3. List Connectors
    resp = client.get("/api/connectors")
    assert resp.status_code == 200
    connectors = resp.json()
    assert any(c["id"] == connector_id for c in connectors)
    
    # 4. Trigger Sync
    resp = client.post("/api/connectors/sync", json={
        "provider_id": "markdown",
        "location": temp_markdown_dir,
        "connector_id": connector_id
    })
    assert resp.status_code == 200
    sync_run = resp.json()
    assert "run_id" in sync_run
    run_id = sync_run["run_id"]
    assert sync_run["state"] == SyncRunState.RUNNING.value
    
    # 5. Get Sync Status
    resp = client.get(f"/api/connectors/sync/{run_id}")
    assert resp.status_code == 200
    status_data = resp.json()
    assert status_data["run_id"] == run_id
    assert status_data["state"] in [SyncRunState.RUNNING.value, SyncRunState.COMPLETED.value]
    
    # 6. Cancel Sync (when it's running)
    resp = client.post(f"/api/connectors/sync/{run_id}/cancel")
    assert resp.status_code in [200, 400]
    
    # 7. Disconnect Connector
    resp = client.post(f"/api/connectors/{connector_id}/disconnect?option=freeze")
    assert resp.status_code == 200
    
    # Verify connector is removed
    resp = client.get("/api/connectors")
    connectors = resp.json()
    assert not any(c["id"] == connector_id for c in connectors)
