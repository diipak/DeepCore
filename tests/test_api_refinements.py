import pytest
import json
from deepcore.core.objects.schemas import ObjectType, RegistryObjectCreate
from deepcore.core.registry.service import RegistryService
from deepcore.core.concepts.service import ConceptService
from deepcore.storage.sqlite.models import RegistryObject, RegistryRelationship

def test_recent_memories_endpoint(client, db_session):
    # Setup test objects
    registry = RegistryService(db_session)
    
    # 1. Human-created knowledge sources
    note = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="My Note",
        source_system="manual",
        status="active"
    ))
    video = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.VIDEO,
        title="My Video",
        source_system="youtube",
        status="active"
    ))
    doc = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.DOCUMENT,
        title="My Document",
        source_system="manual",
        status="active"
    ))
    
    # 2. Excluded / System objects
    concept = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.CONCEPT,
        title="My Concept",
        source_system="deepcore",
        status="active"
    ))
    project = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.PROJECT,
        title="My Project",
        source_system="jira",
        status="active"
    ))

    # Request GET /api/memories/recent
    response = client.get("/api/memories/recent")
    assert response.status_code == 200
    memories = response.json()
    
    # Should only return: note, video, document
    # (And in order of registration/creation descending: doc, video, note)
    assert len(memories) == 3
    assert memories[0]["title"] == "My Document"
    assert memories[1]["title"] == "My Video"
    assert memories[2]["title"] == "My Note"
    
    # Exclude concept and project
    assert not any(m["title"] == "My Concept" for m in memories)
    assert not any(m["title"] == "My Project" for m in memories)


def test_concept_quality_filters_and_sorting(client, db_session):
    # Create notes to attach concepts to
    note = db_session.add(RegistryObject(
        object_type="note",
        title="Note 1",
        source_system="manual",
        status="active"
    ))
    db_session.commit()
    
    # We retrieve the note to get its ID
    note_id = db_session.query(RegistryObject).filter(RegistryObject.title == "Note 1").first().id
    
    # Create concepts:
    # 1. Approved with 1 connection
    approved_1 = db_session.add(RegistryObject(
        object_type="concept",
        title="ApprovedOne",
        source_system="deepcore",
        status="active",
        metadata_json='{"normalized_key": "approvedone", "concept_status": "approved", "concept_type": "technology"}'
    ))
    
    # 2. Approved with 2 connections (should rank highest)
    approved_2 = db_session.add(RegistryObject(
        object_type="concept",
        title="ApprovedTwo",
        source_system="deepcore",
        status="active",
        metadata_json='{"normalized_key": "approvedtwo", "concept_status": "approved", "concept_type": "technology"}'
    ))
    
    # 3. Candidate with 3 connections (should rank below approved despite more connections)
    candidate_3 = db_session.add(RegistryObject(
        object_type="concept",
        title="CandidateThree",
        source_system="deepcore",
        status="active",
        metadata_json='{"normalized_key": "candidatethree", "concept_status": "candidate", "concept_type": "unknown"}'
    ))
    
    # 4. Ignored (should be hidden)
    ignored = db_session.add(RegistryObject(
        object_type="concept",
        title="IgnoredConcept",
        source_system="deepcore",
        status="active",
        metadata_json='{"normalized_key": "ignoredconcept", "concept_status": "ignored", "concept_type": "unknown"}'
    ))
    
    # 5. Merged (should be hidden)
    merged = db_session.add(RegistryObject(
        object_type="concept",
        title="MergedConcept",
        source_system="deepcore",
        status="merged",
        metadata_json='{"normalized_key": "mergedconcept", "concept_status": "approved", "concept_type": "unknown"}'
    ))
    
    db_session.commit()
    
    # Fetch IDs
    db_objects = db_session.query(RegistryObject).all()
    concept_map = {o.title: o.id for o in db_objects if o.object_type == "concept"}
    
    # Add relationships to build connection counts:
    # ApprovedOne: 1 connection
    db_session.add(RegistryRelationship(from_object_id=note_id, to_object_id=concept_map["ApprovedOne"], relationship_type="mentions"))
    
    # ApprovedTwo: 2 connections
    db_session.add(RegistryRelationship(from_object_id=note_id, to_object_id=concept_map["ApprovedTwo"], relationship_type="mentions"))
    db_session.add(RegistryRelationship(from_object_id=note_id, to_object_id=concept_map["ApprovedTwo"], relationship_type="mentions"))
    
    # CandidateThree: 3 connections
    db_session.add(RegistryRelationship(from_object_id=note_id, to_object_id=concept_map["CandidateThree"], relationship_type="mentions"))
    db_session.add(RegistryRelationship(from_object_id=note_id, to_object_id=concept_map["CandidateThree"], relationship_type="mentions"))
    db_session.add(RegistryRelationship(from_object_id=note_id, to_object_id=concept_map["CandidateThree"], relationship_type="mentions"))
    
    # Ignored: 1 connection
    db_session.add(RegistryRelationship(from_object_id=note_id, to_object_id=concept_map["IgnoredConcept"], relationship_type="mentions"))
    
    # Merged: 1 connection
    db_session.add(RegistryRelationship(from_object_id=note_id, to_object_id=concept_map["MergedConcept"], relationship_type="mentions"))
    
    db_session.commit()
    
    # Test GET /api/concepts (without show_ignored, should hide ignored and merged)
    response = client.get("/api/concepts")
    assert response.status_code == 200
    concepts = response.json()
    
    # Ignored and Merged concepts must be hidden
    assert not any(c["concept"]["title"] == "IgnoredConcept" for c in concepts)
    assert not any(c["concept"]["title"] == "MergedConcept" for c in concepts)
    
    # Check prioritization sorting order:
    # 1. ApprovedTwo (Approved, count=2)
    # 2. ApprovedOne (Approved, count=1)
    # 3. CandidateThree (Candidate, count=3 - lower priority despite higher count)
    assert len(concepts) == 3
    assert concepts[0]["concept"]["title"] == "ApprovedTwo"
    assert concepts[0]["connection_count"] == 2
    
    assert concepts[1]["concept"]["title"] == "ApprovedOne"
    assert concepts[1]["connection_count"] == 1
    
    assert concepts[2]["concept"]["title"] == "CandidateThree"
    assert concepts[2]["connection_count"] == 3


def test_dashboard_endpoint(client, db_session):
    # Setup test DB structure
    registry = RegistryService(db_session)
    
    # Add human memories
    note = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE, title="Dashboard Note", source_system="manual"
    ))
    video = registry.register_object(RegistryObjectCreate(
        object_type=ObjectType.VIDEO, title="Dashboard Video", source_system="youtube"
    ))
    
    # Add concepts
    db_session.add(RegistryObject(
        object_type="concept",
        title="DashboardConcept1",
        source_system="deepcore",
        status="active",
        metadata_json='{"normalized_key": "dashboardconcept1", "concept_status": "approved"}'
    ))
    db_session.add(RegistryObject(
        object_type="concept",
        title="DashboardConcept2",
        source_system="deepcore",
        status="active",
        metadata_json='{"normalized_key": "dashboardconcept2", "concept_status": "candidate"}'
    ))
    db_session.commit()
    
    # Add relationship
    db_objects = db_session.query(RegistryObject).all()
    concept1_id = [o.id for o in db_objects if o.title == "DashboardConcept1"][0]
    note_id = [o.id for o in db_objects if o.title == "Dashboard Note"][0]
    
    db_session.add(RegistryRelationship(
        from_object_id=note_id,
        to_object_id=concept1_id,
        relationship_type="mentions"
    ))
    db_session.commit()
    
    # Request GET /api/dashboard
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    dashboard = response.json()
    
    # Verify summary structure
    assert "summary" in dashboard
    summary = dashboard["summary"]
    assert summary["memory_count"] == 2
    assert summary["concept_count"] == 2
    assert summary["approved_concepts"] == 1
    assert summary["relationship_count"] == 1
    
    # Verify top concepts
    assert "top_concepts" in dashboard
    assert len(dashboard["top_concepts"]) >= 1
    assert dashboard["top_concepts"][0]["concept"]["title"] == "DashboardConcept1"
    
    # Verify recent memories
    assert "recent_memories" in dashboard
    assert len(dashboard["recent_memories"]) == 2
