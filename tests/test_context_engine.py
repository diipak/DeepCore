import pytest
from datetime import datetime
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObjectCreate, ObjectType
from deepcore.storage.sqlite.models import RegistryObject as DBRegistryObject, RegistryRelationship as DBRegistryRelationship
from deepcore.intelligence import ContextRequest, ContextEngine

def test_context_engine_trigger_object(db_session):
    """Verify that a trigger object correctly retrieves direct mentions and references."""
    service = RegistryService(db_session)
    engine = ContextEngine(db_session)

    # 1. Create trigger note
    note_a = service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Docker Setup Guide",
        source_system="obsidian",
        location="/notes/docker.md",
        status="active"
    ))

    # 2. Create concept
    concept_x = service.register_object(RegistryObjectCreate(
        object_type=ObjectType.CONCEPT,
        title="Docker",
        source_system="deepcore",
        status="active",
        metadata_json='{"normalized_key": "docker", "concept_status": "approved", "concept_type": "technology"}'
    ))

    # 3. Create target note
    note_b = service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Production Deployment",
        source_system="obsidian",
        location="/notes/prod.md",
        status="active"
    ))

    # Link note_a -> mentions -> concept_x
    db_session.add(DBRegistryRelationship(
        from_object_id=note_a.id,
        to_object_id=concept_x.id,
        relationship_type="mentions",
        confidence=1.0
    ))

    # Link note_a -> references -> note_b
    db_session.add(DBRegistryRelationship(
        from_object_id=note_a.id,
        to_object_id=note_b.id,
        relationship_type="references",
        confidence=1.0
    ))
    db_session.commit()

    # Query context using trigger_object_uuid
    req = ContextRequest(trigger_object_uuid=note_a.uuid)
    package = engine.build_context(req)

    assert package.trigger_object is not None
    assert package.trigger_object.uuid == note_a.uuid
    
    # Verify concepts
    assert len(package.concepts) == 1
    c_item = package.concepts[0]
    assert c_item.concept.uuid == concept_x.uuid
    assert c_item.evidence.relationship_type == "direct_mention"
    assert c_item.evidence.traversal_distance == 1
    assert c_item.evidence.is_direct is True

    # Verify memories
    assert len(package.memories) == 1
    m_item = package.memories[0]
    assert m_item.memory.uuid == note_b.uuid
    assert m_item.evidence.relationship_type == "direct_reference"
    assert m_item.evidence.traversal_distance == 1
    assert m_item.evidence.is_direct is True


def test_context_engine_query_match(db_session):
    """Verify that a query retrieves matched concepts and transitive memories matching them."""
    service = RegistryService(db_session)
    engine = ContextEngine(db_session)

    # 1. Create a concept
    concept_x = service.register_object(RegistryObjectCreate(
        object_type=ObjectType.CONCEPT,
        title="Kubernetes",
        source_system="deepcore",
        status="active",
        metadata_json='{"normalized_key": "kubernetes", "concept_status": "approved"}'
    ))

    # 2. Create memory mentioning it
    note_a = service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="K8s Configs",
        source_system="obsidian",
        location="/notes/k8s.md",
        status="active"
    ))

    db_session.add(DBRegistryRelationship(
        from_object_id=note_a.id,
        to_object_id=concept_x.id,
        relationship_type="mentions"
    ))
    db_session.commit()

    # Query context with query="Kubernetes"
    req = ContextRequest(query="Kubernetes")
    package = engine.build_context(req)

    assert len(package.concepts) == 1
    assert package.concepts[0].concept.uuid == concept_x.uuid
    assert package.concepts[0].evidence.relationship_type == "query_match"
    assert package.concepts[0].evidence.matched_query == "Kubernetes"

    # Transitive match note_a should be retrieved because it mentions concept_x
    assert len(package.memories) == 1
    assert package.memories[0].memory.uuid == note_a.uuid
    assert package.memories[0].evidence.relationship_type == "concept_match"
    assert package.memories[0].evidence.traversal_distance == 2
    assert "Kubernetes" in package.memories[0].evidence.matched_concepts


def test_context_engine_deterministic_sort(db_session):
    """Verify that the sorting logic is completely deterministic."""
    service = RegistryService(db_session)
    engine = ContextEngine(db_session)

    # Create 3 concepts with different connection counts
    c1 = service.register_object(RegistryObjectCreate(
        object_type=ObjectType.CONCEPT,
        title="A_concept",
        source_system="deepcore",
        status="active",
        metadata_json='{"normalized_key": "aconcept"}'
    ))
    c2 = service.register_object(RegistryObjectCreate(
        object_type=ObjectType.CONCEPT,
        title="B_concept",
        source_system="deepcore",
        status="active",
        metadata_json='{"normalized_key": "bconcept"}'
    ))

    note_1 = service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Note 1",
        source_system="obsidian",
        status="active"
    ))
    note_2 = service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Note 2",
        source_system="obsidian",
        status="active"
    ))

    # c1 has 2 connections, c2 has 1 connection
    db_session.add(DBRegistryRelationship(from_object_id=note_1.id, to_object_id=c1.id, relationship_type="mentions"))
    db_session.add(DBRegistryRelationship(from_object_id=note_2.id, to_object_id=c1.id, relationship_type="mentions"))
    db_session.add(DBRegistryRelationship(from_object_id=note_1.id, to_object_id=c2.id, relationship_type="mentions"))
    db_session.commit()

    req = ContextRequest(query="concept")
    
    # Run multiple times to verify identical output ordering
    package1 = engine.build_context(req)
    package2 = engine.build_context(req)

    assert [c.concept.uuid for c in package1.concepts] == [c.concept.uuid for c in package2.concepts]
    # The higher connection count concept (c1) should come first
    assert package1.concepts[0].concept.uuid == c1.uuid
    assert package1.concepts[1].concept.uuid == c2.uuid


def test_assistant_context_api_endpoints(client, db_session):
    """Test the POST and GET FastAPI endpoints for assistant context."""
    service = RegistryService(db_session)

    note = service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="API Testing Context",
        source_system="obsidian",
        status="active"
    ))

    # 1. Test POST /assistant/context
    payload = {
        "trigger_object_uuid": note.uuid,
        "query": "API",
        "max_concepts": 5,
        "max_memories": 5
    }
    response = client.post("/assistant/context", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["trigger_object"]["uuid"] == note.uuid
    assert data["request"]["query"] == "API"

    # 2. Test GET /assistant/context
    response_get = client.get(f"/assistant/context?trigger_uuid={note.uuid}&query=API")
    assert response_get.status_code == 200
    data_get = response_get.json()
    assert data_get["trigger_object"]["uuid"] == note.uuid
    assert data_get["request"]["query"] == "API"
