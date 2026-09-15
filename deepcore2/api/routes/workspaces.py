from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from deepcore2.storage.sqlite.db import get_db
from deepcore2.storage.sqlite.models import Workspace as DBWorkspace, KnowledgeSource as DBKnowledgeSource
from deepcore2.core.objects import schemas
from deepcore2.api.dependencies import get_execution_context
from deepcore2.runtime.composition import get_application

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

@router.get("", response_model=List[schemas.Workspace])
def list_workspaces(db: Session = Depends(get_db)):
    """List all workspaces."""
    return db.query(DBWorkspace).all()

@router.post("", response_model=schemas.Workspace)
def create_workspace(workspace_in: schemas.WorkspaceCreate, db: Session = Depends(get_db)):
    """Create a new workspace."""
    existing = db.query(DBWorkspace).filter(DBWorkspace.name == workspace_in.name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Workspace with name '{workspace_in.name}' already exists."
        )
    ws = DBWorkspace(name=workspace_in.name)
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws

@router.get("/{workspace_uuid}/sources", response_model=List[schemas.KnowledgeSource])
def list_workspace_sources(workspace_uuid: str, db: Session = Depends(get_db)):
    """List all knowledge sources for a workspace."""
    ws = db.query(DBWorkspace).filter(DBWorkspace.uuid == workspace_uuid).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return db.query(DBKnowledgeSource).filter(DBKnowledgeSource.workspace_id == ws.id).all()

@router.post("/{workspace_uuid}/sources", response_model=schemas.KnowledgeSource)
def create_workspace_source(
    workspace_uuid: str,
    source_in: schemas.KnowledgeSourceCreate,
    db: Session = Depends(get_db)
):
    """Register a new KnowledgeSource within a workspace."""
    ws = db.query(DBWorkspace).filter(DBWorkspace.uuid == workspace_uuid).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if source_in.kind == "filesystem":
        import os
        if not os.path.exists(source_in.location):
            raise HTTPException(
                status_code=400,
                detail=f"Local filesystem location '{source_in.location}' does not exist."
            )
            
    source = DBKnowledgeSource(
        workspace_id=ws.id,
        provider_id=source_in.provider_id,
        kind=source_in.kind,
        name=source_in.name,
        location=source_in.location,
        config_json=source_in.config_json
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


sources_router = APIRouter(prefix="/sources", tags=["sources"])

@sources_router.post("/{source_uuid}/sync", response_model=schemas.SyncRun)
def sync_source_endpoint(
    source_uuid: str,
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """
    Trigger synchronization for a specific KnowledgeSource.
    """
    source = db.query(DBKnowledgeSource).filter(
        DBKnowledgeSource.uuid == source_uuid,
        DBKnowledgeSource.workspace_id == context.workspace_id
    ).first()
    if not source:
        raise HTTPException(
            status_code=404,
            detail=f"KnowledgeSource with UUID '{source_uuid}' not found in active workspace."
        )

    if source.kind == "filesystem":
        import os
        if not os.path.exists(source.location):
            raise HTTPException(
                status_code=400,
                detail=f"Local filesystem location '{source.location}' does not exist or is inaccessible."
            )

    app = get_application()
    try:
        return app.ingestion_service.sync_provider(
            provider_name=source.provider_id,
            db=db,
            path=source.location,
            workspace_id=context.workspace_id,
            source_id=source.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
