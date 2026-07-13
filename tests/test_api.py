import pytest
import json
from datetime import datetime, timezone
from deepcore.core.objects.schemas import ObjectType, RegistryObjectCreate
from deepcore.core.registry.service import RegistryService
from deepcore.core.content.service import ContentService
from deepcore.core.concepts.service import ConceptService
from deepcore.storage.sqlite.models import RegistryObject, ContentIndex, RegistryRelationship

def test_api_objects_endpoints(client, db_session):
    # Setup test objects in the database
    registry = RegistryService(db_session)
    obj1 = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.DOCUMENT,
        title="DeepCore Design",
        source_system="manual",
        external_id="doc_1",
        location="/docs/design.md",
        description="Architecture design document",
        status="active"
    ))
    obj2 = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.PROJECT,
        title="API Gateway Phase 5",
        source_system="jira",
        external_id="proj_5",
        location="https://jira.com/PROJ-5",
        description="FastAPI gateway layer",
        status="active"
    ))

    # 1. Test GET /api/objects (Memory Explorer)
    # 1.1 Without query params
    response = client.get("/api/objects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    # Check that we received proper structured JSON representing RegistryObject
    assert any(o["title"] == "DeepCore Design" for o in data)
    assert any(o["title"] == "API Gateway Phase 5" for o in data)

    # 1.2 Search parameter
    response_search = client.get("/api/objects?search=Gateway")
    assert response_search.status_code == 200
    search_data = response_search.json()
    assert len(search_data) == 1
    assert search_data[0]["title"] == "API Gateway Phase 5"

    # 1.3 Filter by type
    response_type = client.get("/api/objects?type=document")
    assert response_type.status_code == 200
    type_data = response_type.json()
    assert len(type_data) == 1
    assert type_data[0]["title"] == "DeepCore Design"

    # 1.4 Filter by source
    response_source = client.get("/api/objects?source=jira")
    assert response_source.status_code == 200
    source_data = response_source.json()
    assert len(source_data) == 1
    assert source_data[0]["title"] == "API Gateway Phase 5"

    # 2. Test GET /api/objects/recent
    response_recent = client.get("/api/objects/recent?limit=1")
    assert response_recent.status_code == 200
    recent_data = response_recent.json()
    assert len(recent_data) == 1
    assert recent_data[0]["title"] == "API Gateway Phase 5"  # registered second

    # 3. Test GET /api/objects/{id_or_uuid}
    # Using ID
    response_details_id = client.get(f"/api/objects/{obj1.id}")
    assert response_details_id.status_code == 200
    details_id = response_details_id.json()
    assert details_id["title"] == "DeepCore Design"
    assert details_id["source"] == "manual"
    assert details_id["type"] == "document"
    assert "uuid" in details_id
    assert "created_at" in details_id

    # Using UUID
    response_details_uuid = client.get(f"/api/objects/{obj2.uuid}")
    assert response_details_uuid.status_code == 200
    details_uuid = response_details_uuid.json()
    assert details_uuid["title"] == "API Gateway Phase 5"
    assert details_uuid["source"] == "jira"
    assert details_uuid["type"] == "project"

    # Not found case
    response_not_found = client.get("/api/objects/non_existent_id")
    assert response_not_found.status_code == 404
    assert "not found" in response_not_found.json()["detail"].lower()


def test_api_content_endpoints(client, db_session, tmp_path):
    # Setup test file content
    note_file = tmp_path / "testing.md"
    note_file.write_text("# Overview\nThis is a file containing FastAPI test info.")

    registry = RegistryService(db_session)
    content_service = ContentService(db_session)

    obj = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="FastAPI Overview",
        source_system="markdown",
        location=str(note_file),
        status="active"
    ))

    # Index the object
    idx_entry = content_service.index_object(obj.id)
    assert idx_entry is not None

    # 1. Test GET /api/content/search
    response_search = client.get("/api/content/search?query=FastAPI")
    assert response_search.status_code == 200
    search_data = response_search.json()
    assert len(search_data) == 1
    assert search_data[0]["object"]["title"] == "FastAPI Overview"
    assert search_data[0]["content"]["raw_text"] == "# Overview\nThis is a file containing FastAPI test info."

    # 2. Test GET /api/content/{object_id}
    # Using ID
    response_content = client.get(f"/api/content/{obj.id}")
    assert response_content.status_code == 200
    content_data = response_content.json()
    assert content_data["object_id"] == obj.id
    assert content_data["raw_text"] == "# Overview\nThis is a file containing FastAPI test info."

    # Using UUID
    response_content_uuid = client.get(f"/api/content/{obj.uuid}")
    assert response_content_uuid.status_code == 200
    content_uuid_data = response_content_uuid.json()
    assert content_uuid_data["object_id"] == obj.id

    # Not found case
    response_not_found = client.get("/api/content/999999")
    assert response_not_found.status_code == 404


def test_api_concepts_endpoints(client, db_session, tmp_path):
    # Setup a file to extract concepts from
    note_file = tmp_path / "concept_note.md"
    note_file.write_text("# Python\nPython is a programming language. PySpark is used with Python.")

    registry = RegistryService(db_session)
    content_service = ContentService(db_session)
    concept_service = ConceptService(db_session)

    obj = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Concept Note",
        source_system="markdown",
        location=str(note_file),
        status="active"
    ))

    # Index and extract concepts
    content_service.index_object(obj.id)
    extraction_res = concept_service.extract_from_object(obj.id)
    assert extraction_res["concepts_created"] >= 1

    # 1. Test GET /api/concepts
    response_concepts = client.get("/api/concepts")
    assert response_concepts.status_code == 200
    concepts_data = response_concepts.json()
    assert len(concepts_data) >= 1
    assert concepts_data[0]["concept"]["object_type"] == "concept"
    assert concepts_data[0]["connection_count"] >= 1

    concept_name = concepts_data[0]["concept"]["title"]

    # 2. Test GET /api/concepts/{name}
    response_concept_details = client.get(f"/api/concepts/{concept_name}")
    assert response_concept_details.status_code == 200
    concept_details = response_concept_details.json()
    assert concept_details["concept"]["title"] == concept_name
    assert len(concept_details["connected_memories"]) >= 1
    assert concept_details["connected_memories"][0]["title"] == "Concept Note"

    # 3. Test POST /api/concepts/{name}/approve
    response_approve = client.post(f"/api/concepts/{concept_name}/approve", json={"type": "technology"})
    assert response_approve.status_code == 200
    approved_obj = response_approve.json()
    assert approved_obj["title"] == concept_name
    meta = json.loads(approved_obj["metadata_json"])
    assert meta["concept_status"] == "approved"
    assert meta["concept_type"] == "technology"

    # Approve with invalid type should return 400
    response_invalid_approve = client.post(f"/api/concepts/{concept_name}/approve", json={"type": "invalid_type"})
    assert response_invalid_approve.status_code == 400

    # Approve non-existent concept should return 404
    response_approve_non_existent = client.post("/api/concepts/non_existent_concept/approve", json={"type": "technology"})
    assert response_approve_non_existent.status_code == 404

    # 4. Test POST /api/concepts/{name}/ignore
    # Let's extract or find another concept or just reuse
    response_ignore = client.post(f"/api/concepts/{concept_name}/ignore")
    assert response_ignore.status_code == 200
    ignored_obj = response_ignore.json()
    meta_ignored = json.loads(ignored_obj["metadata_json"])
    assert meta_ignored["concept_status"] == "ignored"

    # Ignore non-existent concept should return 404
    response_ignore_non_existent = client.post("/api/concepts/non_existent_concept/ignore")
    assert response_ignore_non_existent.status_code == 404


def test_api_system_stats(client, db_session):
    # Setup some dummy records
    registry = RegistryService(db_session)
    registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.DOCUMENT,
        title="Stats Document",
        source_system="manual",
        status="active"
    ))
    # Create a concept and a relationship
    concept = db_session.add(RegistryObject(
        object_type="concept",
        title="TestConcept",
        source_system="deepcore",
        status="active",
        metadata_json='{"normalized_key": "testconcept", "concept_status": "candidate", "concept_type": "unknown"}'
    ))
    db_session.commit()
    
    # Retrieve the objects to get IDs
    db_objects = db_session.query(RegistryObject).all()
    obj_id = db_objects[0].id
    concept_id = [o.id for o in db_objects if o.object_type == "concept"][0]
    
    db_session.add(RegistryRelationship(
        from_object_id=obj_id,
        to_object_id=concept_id,
        relationship_type="mentions",
        confidence=1.0,
        relationship_source="concept_v0.1"
    ))
    db_session.commit()

    # Test GET /api/stats
    response = client.get("/api/stats")
    assert response.status_code == 200
    stats = response.json()
    assert stats["total_objects"] >= 2
    assert "concept" in stats["by_type"]
    assert stats["concept_count"] >= 1
    assert stats["relationship_count"] >= 1


def test_api_assistant_placeholders(client):
    # Test assistant chat placeholder
    response_chat_get = client.get("/assistant/chat")
    assert response_chat_get.status_code == 501
    assert "not implemented" in response_chat_get.json()["detail"].lower()

    response_chat_post = client.post("/assistant/chat")
    assert response_chat_post.status_code == 501

