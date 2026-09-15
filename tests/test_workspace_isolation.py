import pytest
from deepcore.storage.sqlite.models import Workspace, KnowledgeSource, RegistryObject

def test_workspace_lifecycle_and_isolation(client, staged_notes_dir, db_session):
    """
    Test workspace creation, source configuration, isolation during sync/queries,
    workspace diagnostics, and the KnowledgeSource Identity Invariant.
    """
    # 1. Create Workspace A and Workspace B
    response_a = client.post("/api/workspaces", json={"name": "Workspace A"})
    assert response_a.status_code == 200
    ws_a = response_a.json()
    uuid_a = ws_a["uuid"]
    assert ws_a["name"] == "Workspace A"

    response_b = client.post("/api/workspaces", json={"name": "Workspace B"})
    assert response_b.status_code == 200
    ws_b = response_b.json()
    uuid_b = ws_b["uuid"]
    assert ws_b["name"] == "Workspace B"

    # Verify listing workspaces
    list_resp = client.get("/api/workspaces")
    assert list_resp.status_code == 200
    workspaces = list_resp.json()
    # At least "Personal Workspace", "Workspace A", and "Workspace B"
    names = {w["name"] for w in workspaces}
    assert "Workspace A" in names
    assert "Workspace B" in names

    # 2. Add KnowledgeSource to Workspace A and Workspace B
    source_a_payload = {
        "name": "Source A",
        "kind": "filesystem",
        "provider_id": "markdown",
        "location": staged_notes_dir
    }
    src_a_resp = client.post(f"/api/workspaces/{uuid_a}/sources", json=source_a_payload)
    assert src_a_resp.status_code == 200
    source_a = src_a_resp.json()
    src_a_uuid = source_a["uuid"]
    assert source_a["name"] == "Source A"
    assert source_a["location"] == staged_notes_dir

    source_b_payload = {
        "name": "Source B",
        "kind": "filesystem",
        "provider_id": "markdown",
        "location": staged_notes_dir
    }
    src_b_resp = client.post(f"/api/workspaces/{uuid_b}/sources", json=source_b_payload)
    assert src_b_resp.status_code == 200
    source_b = src_b_resp.json()
    src_b_uuid = source_b["uuid"]

    # 3. Synchronize Workspace A source (Inject X-Workspace-UUID header)
    sync_a_resp = client.post(
        f"/api/sources/{src_a_uuid}/sync",
        headers={"X-Workspace-UUID": uuid_a}
    )
    assert sync_a_resp.status_code == 200
    sync_a_data = sync_a_resp.json()
    assert sync_a_data["status"] == "success"
    assert sync_a_data["objects_created"] == 3

    # 4. Verify isolation (Querying objects in A vs B)
    # Query with Workspace A header -> Should see 3 objects
    objs_a_resp = client.get("/api/objects", headers={"X-Workspace-UUID": uuid_a})
    assert objs_a_resp.status_code == 200
    objs_a = objs_a_resp.json()
    assert len(objs_a) == 3

    # Query with Workspace B header -> Should see 0 objects
    objs_b_resp = client.get("/api/objects", headers={"X-Workspace-UUID": uuid_b})
    assert objs_b_resp.status_code == 200
    objs_b = objs_b_resp.json()
    assert len(objs_b) == 0

    # 5. Ingest Workspace B and check isolation
    sync_b_resp = client.post(
        f"/api/sources/{src_b_uuid}/sync",
        headers={"X-Workspace-UUID": uuid_b}
    )
    assert sync_b_resp.status_code == 200
    
    objs_b_resp2 = client.get("/api/objects", headers={"X-Workspace-UUID": uuid_b})
    assert len(objs_b_resp2.json()) == 3

    # 6. Verify Workspace diagnostics endpoint
    diag_a_resp = client.get("/api/system/workspace", headers={"X-Workspace-UUID": uuid_a})
    assert diag_a_resp.status_code == 200
    diag_a = diag_a_resp.json()
    assert diag_a["workspace_name"] == "Workspace A"
    assert diag_a["object_count"] == 3
    assert len(diag_a["registered_sources"]) == 1
    assert diag_a["registered_sources"][0]["name"] == "Source A"

    diag_b_resp = client.get("/api/system/workspace", headers={"X-Workspace-UUID": uuid_b})
    assert diag_b_resp.status_code == 200
    diag_b = diag_b_resp.json()
    assert diag_b["workspace_name"] == "Workspace B"
    assert diag_b["object_count"] == 3

    # 7. Verify KnowledgeSource Identity Invariant:
    # Mutating location of Source A should not transfer ownership or touch existing RegistryObjects
    db_source_a = db_session.query(KnowledgeSource).filter(KnowledgeSource.uuid == src_a_uuid).first()
    original_source_a_id = db_source_a.id
    
    # Change location of Source A
    db_source_a.location = "/mutated/path/to/source"
    db_session.commit()

    # Query RegistryObjects of Workspace A in database directly
    db_objs_a = db_session.query(RegistryObject).filter(RegistryObject.workspace_id == db_source_a.workspace_id).all()
    assert len(db_objs_a) == 3
    for obj in db_objs_a:
        # Ownership must remain linked to original source ID
        assert obj.source_id == original_source_a_id
        # Invariant preserved


def test_default_workspaces_and_observability(client):
    """
    Test that the default workspaces are auto-provisioned, default sources are registered,
    and platform observability (sync runs and health status) works.
    """
    # 1. Fetch workspaces list
    resp = client.get("/api/workspaces")
    assert resp.status_code == 200
    workspaces = resp.json()
    
    names = {w["name"]: w for w in workspaces}
    assert "Personal Workspace" in names
    assert "Demo Workspace" in names

    personal_uuid = names["Personal Workspace"]["uuid"]
    demo_uuid = names["Demo Workspace"]["uuid"]

    # 2. Verify sources auto-provisioned
    personal_sources_resp = client.get(f"/api/workspaces/{personal_uuid}/sources")
    assert personal_sources_resp.status_code == 200
    personal_sources = personal_sources_resp.json()
    assert len(personal_sources) >= 1
    assert any("Notes" in s["location"] for s in personal_sources)

    demo_sources_resp = client.get(f"/api/workspaces/{demo_uuid}/sources")
    assert demo_sources_resp.status_code == 200
    demo_sources = demo_sources_resp.json()
    assert len(demo_sources) >= 1
    assert any("demo/markdown" in s["location"] for s in demo_sources)

    # 3. Verify Sync Runs History API
    runs_resp = client.get("/api/system/runs", headers={"X-Workspace-UUID": personal_uuid})
    assert runs_resp.status_code == 200
    runs = runs_resp.json()
    assert isinstance(runs, list)

    # 4. Verify Platform Health Check API (All 10 major subsystems)
    health_resp = client.get("/api/system/health", headers={"X-Workspace-UUID": personal_uuid})
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert "status" in health_data
    assert "subsystems" in health_data

    subs = health_data["subsystems"]
    required_subs = [
        "database", "workspace_resolver", "registry", "provider_registry",
        "knowledge_sources", "processing_runtime", "content_index_stage",
        "relationship_engine", "temporal_signal_engine", "api_runtime",
        "workspace_integrity"
    ]
    for sub in required_subs:
        assert sub in subs
        assert "status" in subs[sub]
        assert "message" in subs[sub]
        assert "metrics" in subs[sub]
        assert isinstance(subs[sub]["metrics"], dict)


def test_workspace_integrity_validator_and_repair(db_session):
    """
    Test WorkspaceIntegrityValidator, WorkspaceIntegrityRepair, and idempotency guarantees.
    """
    from deepcore.core.integrity.service import WorkspaceIntegrityService
    from deepcore.storage.sqlite.models import RegistryObject, RegistryRelationship

    # 1. Ensure test workspace exists
    ws = db_session.query(Workspace).filter(Workspace.name == "Personal Workspace").first()
    assert ws is not None

    service = WorkspaceIntegrityService(db_session, ws.id)

    # 2. Inject corrupted/invalid state:
    # A relationship pointing to an inactive object
    source_obj = RegistryObject(
        workspace_id=ws.id,
        uuid="source-obj-uuid",
        title="Source Object",
        object_type="note",
        provider_id="markdown",
        source_system="markdown",
        location="/workspace/notes/Src.md",
        status="active"
    )
    target_obj = RegistryObject(
        workspace_id=ws.id,
        uuid="target-obj-uuid",
        title="Target Object",
        object_type="note",
        provider_id="markdown",
        source_system="markdown",
        location="/workspace/notes/Target.md",
        status="archived"  # Inactive status
    )
    db_session.add(source_obj)
    db_session.add(target_obj)
    db_session.commit()

    invalid_rel = RegistryRelationship(
        workspace_id=ws.id,
        from_object_id=source_obj.id,
        to_object_id=target_obj.id,
        relationship_type="references"
    )
    db_session.add(invalid_rel)
    
    # An object in Workspace 1 with demo/markdown location (which should not be in Workspace 1)
    demo_obj = RegistryObject(
        workspace_id=ws.id,
        uuid="test-demo-uuid-in-personal",
        title="Test Demo Object",
        object_type="note",
        provider_id="markdown",
        source_system="markdown",
        location="/workspace/demo/markdown/Test.md",
        status="active"
    )
    db_session.add(demo_obj)
    db_session.commit()

    # 3. Validate -> Must fail/degrade
    health_report = service.validate_integrity()
    assert health_report["is_healthy"] is False
    assert health_report["status"] == "degraded"
    assert health_report["checks"]["workspace_ownership"]["status"] == "fail"
    assert health_report["checks"]["navigation_consistency"]["status"] == "fail"

    # 4. Repair -> Must fix the issues
    repair_report = service.repair_integrity()
    assert repair_report["repaired_workspace_objects"] >= 1
    assert repair_report["repaired_invalid_relationships"] >= 1

    # 5. Validate -> Must pass
    health_report2 = service.validate_integrity()
    assert health_report2["is_healthy"] is True
    assert health_report2["status"] == "healthy"

    # 6. Repair Again -> Must be idempotent (0 additional repairs)
    repair_report2 = service.repair_integrity()
    assert repair_report2["total_repaired"] == 0

    # 7. Validate Again -> Must still pass
    health_report3 = service.validate_integrity()
    assert health_report3["is_healthy"] is True
    assert health_report3["status"] == "healthy"

