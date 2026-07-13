from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from deepcore.storage.sqlite.db import get_db
from deepcore.core.objects import schemas
from deepcore.core.registry.service import RegistryService
from deepcore.storage.sqlite.models import RegistryObject as DBRegistryObject, RegistryRelationship as DBRegistryRelationship
from deepcore.api.routes.concepts import ConceptListEntry

router = APIRouter(tags=["system"])

class SystemStatsResponse(BaseModel):
    total_objects: int
    by_type: dict[str, int]
    by_source: dict[str, int]
    concept_count: int
    relationship_count: int

class DashboardSummary(BaseModel):
    memory_count: int
    concept_count: int
    approved_concepts: int
    relationship_count: int

class RecentlyConnectedEntry(BaseModel):
    uuid: str
    title: str
    object_type: str
    total_connected: int
    repo_connected: int
    video_connected: int
    doc_connected: int

class DashboardResponse(BaseModel):
    summary: DashboardSummary
    top_concepts: List[ConceptListEntry]
    recent_memories: List[schemas.RegistryObject]
    recently_connected: List[RecentlyConnectedEntry] = []

@router.get("/stats", response_model=SystemStatsResponse)
def get_system_stats_api(db: Session = Depends(get_db)):
    """System statistics API endpoint."""
    registry_service = RegistryService(db)
    stats_data = registry_service.get_statistics()
    
    concept_count = db.query(DBRegistryObject).filter(DBRegistryObject.object_type == "concept").count()
    relationship_count = db.query(DBRegistryRelationship).count()
    
    return SystemStatsResponse(
        total_objects=stats_data["total_objects"],
        by_type=stats_data["by_type"],
        by_source=stats_data["by_source"],
        concept_count=concept_count,
        relationship_count=relationship_count
    )

@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard_api(db: Session = Depends(get_db)):
    """Dashboard overview API endpoint for the UI home screen."""
    from deepcore.core.concepts.service import ConceptService
    
    registry_service = RegistryService(db)
    concept_service = ConceptService(db)
    
    counts = registry_service.get_dashboard_counts()
    summary = DashboardSummary(
        memory_count=counts["memory_count"],
        concept_count=counts["concept_count"],
        approved_concepts=counts["approved_concepts"],
        relationship_count=counts["relationship_count"]
    )
    
    # Get top 5 concepts ordered by connections (and approved status)
    top_concepts_raw = concept_service.list_concepts(limit=5)
    top_concepts = [
        ConceptListEntry(concept=concept, connection_count=count)
        for concept, count in top_concepts_raw
    ]
    
    # Get top 5 recent memories (note, video, document)
    recent_memories = registry_service.recent_memories(limit=5)

    # Get recently connected parent memories
    recently_connected = registry_service.get_recently_connected(limit=5)
    
    return DashboardResponse(
        summary=summary,
        top_concepts=top_concepts,
        recent_memories=recent_memories,
        recently_connected=recently_connected
    )


@router.get("/health")
def health_endpoint():
    """Exposes hierarchical domain-based health and diagnostics of the application."""
    from deepcore.runtime.composition import get_application
    app = get_application()
    return app.health_info

