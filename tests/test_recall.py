from datetime import datetime, timedelta
import pytest
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObjectCreate, ObjectType
from deepcore.storage.sqlite.models import RegistryObject as DBRegistryObject

def test_title_search_works_and_is_case_insensitive(db_session):
    """Verify that title search works and is case-insensitive (regression test)."""
    service = RegistryService(db_session)
    
    # Register search targets
    service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Build RAG System",
        source_system="markdown",
        location="/notes/rag.md",
        description="A great RAG note",
        status="active"
    ))
    service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Python Learning",
        source_system="manual",
        location="/notes/python.md",
        description="Learning Python syntax",
        status="active"
    ))
    
    # 1. Search title exact case
    results = service.search_objects(query="RAG")
    assert len(results) == 1
    assert results[0].title == "Build RAG System"
    
    # 2. Search title lowercase (regression test)
    results_lower = service.search_objects(query="rag")
    assert len(results_lower) == 1
    assert results_lower[0].title == "Build RAG System"
    
    # 3. Search title mixed case (regression test)
    results_mixed = service.search_objects(query="RaG SyStEm")
    assert len(results_mixed) == 1
    assert results_mixed[0].title == "Build RAG System"

    # 4. Search description case-insensitive
    results_desc = service.search_objects(query="lEaRnInG")
    assert len(results_desc) == 1
    assert results_desc[0].title == "Python Learning"

    # 5. Search location case-insensitive
    results_loc = service.search_objects(query="PyThOn.md")
    assert len(results_loc) == 1
    assert results_loc[0].title == "Python Learning"


def test_search_filters_work(db_session):
    """Verify that search results can be filtered by object_type and source_system."""
    service = RegistryService(db_session)
    
    service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="RAG note",
        source_system="markdown",
        status="active"
    ))
    service.register_object(RegistryObjectCreate(
        object_type=ObjectType.VIDEO,
        title="RAG video",
        source_system="youtube",
        status="active"
    ))
    
    # Filter by object_type
    results = service.search_objects(query="RAG", object_type="note")
    assert len(results) == 1
    assert results[0].title == "RAG note"
    
    # Filter by source_system
    results = service.search_objects(query="RAG", source_system="youtube")
    assert len(results) == 1
    assert results[0].title == "RAG video"


def test_search_excludes_non_active(db_session):
    """Verify that search excludes inactive status (missing, archived). Only status='active' is returned."""
    service = RegistryService(db_session)
    
    service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="RAG archived note",
        source_system="markdown",
        status="archived"
    ))
    service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="RAG missing note",
        source_system="markdown",
        status="missing"
    ))
    service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="RAG active note",
        source_system="markdown",
        status="active"
    ))
    
    results = service.search_objects(query="RAG")
    assert len(results) == 1
    assert results[0].title == "RAG active note"


def test_get_object_details_returns_full_metadata(db_session):
    """Verify that get_object_details returns a dictionary with the full metadata requirements."""
    service = RegistryService(db_session)
    
    obj = service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="RAG note",
        source_system="markdown",
        location="/notes/rag.md",
        description="A great RAG note",
        status="active",
        metadata_json='{"key": "value"}'
    ))
    
    # Retrieve details by UUID
    details = service.get_object_details(obj.uuid)
    assert details is not None
    assert details["uuid"] == obj.uuid
    assert details["type"] == ObjectType.NOTE
    assert details["title"] == "RAG note"
    assert details["source"] == "markdown"
    assert details["location"] == "/notes/rag.md"
    assert details["status"] == "active"
    assert details["metadata_json"] == '{"key": "value"}'
    assert isinstance(details["created_at"], datetime)
    assert isinstance(details["updated_at"], datetime)
    
    # Retrieve details by integer ID
    details_by_id = service.get_object_details(obj.id)
    assert details_by_id is not None
    assert details_by_id["uuid"] == obj.uuid

    # Test not found returns None
    assert service.get_object_details("non-existent-uuid") is None
    assert service.get_object_details(999999) is None


def test_recent_ordering_and_limit_works(db_session):
    """Verify that recent_objects sorts by created_at descending and respects the limit."""
    service = RegistryService(db_session)
    
    now = datetime.now()
    
    # Insert objects directly with controlled created_at dates
    obj1 = DBRegistryObject(
        object_type="note",
        title="Oldest Note",
        source_system="manual",
        status="active",
        created_at=now - timedelta(days=2)
    )
    obj2 = DBRegistryObject(
        object_type="note",
        title="Middle Note",
        source_system="manual",
        status="active",
        created_at=now - timedelta(days=1)
    )
    obj3 = DBRegistryObject(
        object_type="note",
        title="Newest Note",
        source_system="manual",
        status="active",
        created_at=now
    )
    # Exclude inactive/archived/missing objects from recent
    obj4 = DBRegistryObject(
        object_type="note",
        title="Archived New Note",
        source_system="manual",
        status="archived",
        created_at=now + timedelta(days=1)
    )
    
    db_session.add_all([obj1, obj2, obj3, obj4])
    db_session.commit()
    
    # 1. Verify ordering (newest first) and exclusion of archived
    recent = service.recent_objects(limit=5)
    assert len(recent) == 3
    assert recent[0].title == "Newest Note"
    assert recent[1].title == "Middle Note"
    assert recent[2].title == "Oldest Note"
    
    # 2. Verify limit parameter works
    recent_limited = service.recent_objects(limit=2)
    assert len(recent_limited) == 2
    assert recent_limited[0].title == "Newest Note"
    assert recent_limited[1].title == "Middle Note"
