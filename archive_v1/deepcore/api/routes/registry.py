from typing import List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from deepcore.storage.sqlite.db import get_db
from deepcore.core.objects import schemas
from deepcore.core.registry.service import RegistryService
from deepcore.api.dependencies import get_execution_context

router = APIRouter(prefix="/objects", tags=["objects"])

class ConceptShort(BaseModel):
    id: int
    uuid: str
    title: str

class ReferencedObjectShort(BaseModel):
    id: int
    uuid: str
    title: str
    object_type: str
    location: Optional[str] = None

class RelationshipDetailResponse(BaseModel):
    uuid: str
    target_object_uuid: str
    target_object_title: str
    target_object_type: str
    relationship_type: str
    confidence: float
    evidence: Optional[Any] = None
    created_at: datetime
    updated_at: datetime

class SignalDetailResponse(BaseModel):
    uuid: str
    signal_type: str
    value: Optional[str] = None
    confidence: float
    generated_by: str
    evidence: Optional[Any] = None
    created_at: datetime
    updated_at: datetime

class ObjectDetailsResponse(BaseModel):
    uuid: str
    type: str
    title: str
    source: str
    location: Optional[str] = None
    status: str
    metadata_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    connected_concepts: List[ConceptShort] = []
    referenced_objects: List[ReferencedObjectShort] = []
    relationships: List[RelationshipDetailResponse] = []
    signals: List[SignalDetailResponse] = []


@router.get("", response_model=List[schemas.RegistryObject])
def list_objects_api(
    search: Optional[str] = None,
    type: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """Memory explorer API endpoint scoped to the workspace."""
    service = RegistryService(db, context.workspace_id)
    return service.search_objects(
        query=search or "",
        object_type=type,
        source_system=source,
        limit=limit
    )

@router.get("/recent", response_model=List[schemas.RegistryObject])
def recent_objects_api(
    limit: int = 10,
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """Home screen recent objects section API endpoint scoped to the workspace."""
    service = RegistryService(db, context.workspace_id)
    return service.recent_objects(limit=limit)

@router.get("/{id_or_uuid}", response_model=ObjectDetailsResponse)
def get_object_details_api(
    id_or_uuid: str,
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """Object detail screen API endpoint scoped to the workspace."""
    service = RegistryService(db, context.workspace_id)
    details = service.get_object_details(id_or_uuid)
    if not details:
        raise HTTPException(status_code=404, detail=f"Object '{id_or_uuid}' not found")
    return details
