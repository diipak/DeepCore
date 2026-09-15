import pytest
from deepcore.config import Settings
from deepcore.runtime.composition import bootstrap_application, get_application
from deepcore.runtime.application import Application

def test_kernel_smoke_lifecycle(client):
    """
    Lightweight Kernel Smoke Test verifying the composed application lifecycle:
    - Application singleton construction and retrieval
    - Health diagnostics and hierarchical domain status
    - Key database routes execution (stats, dashboard, memories, objects, concepts)
    - Graceful shutdown hook execution
    """
    # 1. Verify Application singleton retrieval and startup status
    settings = Settings()
    app = bootstrap_application(settings)
    assert isinstance(app, Application)
    assert app.status == "ready"
    
    retrieved_app = get_application()
    assert retrieved_app is app

    # 2. Verify Health Endpoint Response and Structure
    response = client.get("/api/health")
    assert response.status_code == 200
    health_data = response.json()
    assert health_data["status"] == "ready"
    assert "domains" in health_data
    
    domains = health_data["domains"]
    for domain in ["kernel", "registry", "providers", "models", "synchronization"]:
        assert domain in domains
        assert "status" in domains[domain]

    # 3. Verify Representative API Endpoints (200 OK & structure checks)
    
    # 3.1 Stats API
    res_stats = client.get("/api/stats")
    assert res_stats.status_code == 200
    stats_data = res_stats.json()
    assert "total_objects" in stats_data
    assert "concept_count" in stats_data
    assert "relationship_count" in stats_data

    # 3.2 Dashboard API
    res_dash = client.get("/api/dashboard")
    assert res_dash.status_code == 200
    dash_data = res_dash.json()
    assert "summary" in dash_data
    assert "focus" in dash_data
    assert "orientation" in dash_data
    assert "understanding" in dash_data
    assert "continuation" in dash_data

    # 3.3 Memories API
    res_mem = client.get("/api/memories/recent?limit=5")
    assert res_mem.status_code == 200
    assert isinstance(res_mem.json(), list)

    # 3.4 Objects API
    res_obj = client.get("/api/objects")
    assert res_obj.status_code == 200
    assert isinstance(res_obj.json(), list)

    # 3.5 Concepts API
    res_concepts = client.get("/api/concepts")
    assert res_concepts.status_code == 200
    assert isinstance(res_concepts.json(), list)

    # 4. Verify Graceful Shutdown Hooks
    shutdown_invoked = False
    
    def on_shutdown():
        nonlocal shutdown_invoked
        shutdown_invoked = True
        
    app.register_shutdown_hook(on_shutdown)
    app.shutdown()
    
    assert app.status == "stopped"
    assert shutdown_invoked is True
