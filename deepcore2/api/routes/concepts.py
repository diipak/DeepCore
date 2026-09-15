from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from deepcore2.storage.sqlite.db import get_db
from deepcore2.core.objects import schemas
from deepcore2.core.concepts.service import ConceptService
from deepcore2.api.dependencies import get_execution_context

router = APIRouter(prefix="/concepts", tags=["concepts"])

class ConceptListEntry(BaseModel):
    concept: schemas.RegistryObject
    connection_count: int

class ConceptDetailResponse(BaseModel):
    concept: schemas.RegistryObject
    connected_memories: List[schemas.RegistryObject]

class ApproveConceptRequest(BaseModel):
    type: Optional[str] = None


@router.get("", response_model=List[ConceptListEntry])
def list_concepts_api(
    limit: int = 50,
    show_ignored: bool = False,
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """Concept browser API endpoint scoped to the workspace."""
    service = ConceptService(db, context.workspace_id)
    results = service.list_concepts(limit=limit, show_ignored=show_ignored)
    return [ConceptListEntry(concept=concept, connection_count=count) for concept, count in results]

@router.get("/{name}", response_model=ConceptDetailResponse)
def get_concept_details_api(
    name: str,
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """Concept detail screen API endpoint scoped to the workspace."""
    service = ConceptService(db, context.workspace_id)
    concept = service.get_concept_by_name(name)
    if not concept:
        raise HTTPException(status_code=404, detail=f"Concept '{name}' not found")
    memories = service.get_connected_memories(concept.id)
    return ConceptDetailResponse(concept=concept, connected_memories=memories)

@router.post("/{name}/approve", response_model=schemas.RegistryObject)
def approve_concept_api(
    name: str,
    request: ApproveConceptRequest,
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """Approve concept API endpoint scoped to the workspace."""
    service = ConceptService(db, context.workspace_id)
    try:
        return service.approve_concept(name, request.type)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{name}/ignore", response_model=schemas.RegistryObject)
def ignore_concept_api(
    name: str,
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """Ignore concept API endpoint scoped to the workspace."""
    service = ConceptService(db, context.workspace_id)
    try:
        return service.ignore_concept(name)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
