from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObjectCreate, ObjectType
from deepcore.core.providers.manual import ManualProvider

def test_object_creation_retrieval_and_source(db_session):
    """Test standard service layer object creation, retrieval by ID/UUID, and preservation of source references."""
    service = RegistryService(db_session)
    
    # Create registration payload
    obj_data = RegistryObjectCreate(
        object_type=ObjectType.DOCUMENT,
        title="DeepCore Architecture",
        source_system="manual",
        external_id="doc_123",
        location="/docs/arch.md",
        description="Core architecture of DeepCore",
        status="active",
        metadata_json='{"tags": ["core", "mvp"]}',
        provider_version="1.0.0"
    )
    
    # 1. Test register_object
    db_obj = service.register_object(obj_data)
    assert db_obj.id is not None
    assert db_obj.uuid is not None
    assert db_obj.title == "DeepCore Architecture"
    
    # 2. Test get_object by integer ID
    retrieved_by_id = service.get_object(db_obj.id)
    assert retrieved_by_id is not None
    assert retrieved_by_id.uuid == db_obj.uuid
    assert retrieved_by_id.title == "DeepCore Architecture"
    
    # 3. Test get_object by UUID string
    retrieved_by_uuid = service.get_object(db_obj.uuid)
    assert retrieved_by_uuid is not None
    assert retrieved_by_uuid.id == db_obj.id
    
    # 4. Test get_object by string representation of integer ID
    retrieved_by_id_str = service.get_object(str(db_obj.id))
    assert retrieved_by_id_str is not None
    assert retrieved_by_id_str.id == db_obj.id
    
    # 5. Verify original source reference and newly added fields are kept
    assert retrieved_by_id.source_system == "manual"
    assert retrieved_by_id.external_id == "doc_123"
    assert retrieved_by_id.metadata_json == '{"tags": ["core", "mvp"]}'
    assert retrieved_by_id.provider_version == "1.0.0"

def test_manual_provider_sync(db_session):
    """Test that ManualProvider can ingest raw data, normalize it, and register via service."""
    service = RegistryService(db_session)
    provider = ManualProvider()
    
    raw_data = {
        "object_type": "note",
        "title": "My MVP Ideas",
        "external_id": "idea_999",
        "location": "/notes/mvp.txt",
        "description": "Registry MVP outline",
        "metadata_json": '{"priority": "high"}'
    }
    
    provider.add_input(raw_data)
    synced = provider.sync(service)
    
    assert len(synced) == 1
    db_obj = synced[0]
    
    # Verify normalization defaults (source_system -> manual)
    assert db_obj.source_system == "manual"
    assert db_obj.external_id == "idea_999"
    assert db_obj.title == "My MVP Ideas"
    assert db_obj.object_type == ObjectType.NOTE
    
    # Verify it is retrievable in the database
    retrieved = service.get_object(db_obj.id)
    assert retrieved is not None
    assert retrieved.title == "My MVP Ideas"

def test_api_endpoints(client):
    """Test API routes: POST /objects, GET /objects, and GET /objects/{id_or_uuid}."""
    # Test POST /objects
    post_payload = {
        "object_type": "project",
        "title": "Build DeepCore MVP",
        "source_system": "jira",
        "external_id": "PROJ-1",
        "location": "https://jira.com/PROJ-1",
        "description": "First version",
        "status": "active"
    }
    
    response = client.post("/objects", json=post_payload)
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["id"] is not None
    assert json_data["uuid"] is not None
    assert json_data["title"] == "Build DeepCore MVP"
    assert json_data["source_system"] == "jira"
    
    obj_id = json_data["id"]
    obj_uuid = json_data["uuid"]
    
    # Test GET /objects/{id} using ID
    response_get_id = client.get(f"/objects/{obj_id}")
    assert response_get_id.status_code == 200
    assert response_get_id.json()["uuid"] == obj_uuid
    
    # Test GET /objects/{uuid} using UUID
    response_get_uuid = client.get(f"/objects/{obj_uuid}")
    assert response_get_uuid.status_code == 200
    assert response_get_uuid.json()["id"] == obj_id
    
    # Test GET /objects
    response_list = client.get("/objects")
    assert response_list.status_code == 200
    assert len(response_list.json()) >= 1
    
    # Test GET /objects with matching object_type filter
    response_filter_match = client.get("/objects?object_type=project")
    assert response_filter_match.status_code == 200
    assert len(response_filter_match.json()) >= 1
    
    # Test GET /objects with non-matching object_type filter
    response_filter_no_match = client.get("/objects?object_type=transaction")
    assert response_filter_no_match.status_code == 200
    assert len(response_filter_no_match.json()) == 0
