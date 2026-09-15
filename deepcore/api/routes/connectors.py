import os
import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from deepcore.storage.sqlite.db import get_db
from deepcore.storage.sqlite.models import KnowledgeSource as DBKnowledgeSource, SyncRun as DBSyncRun, RegistryObject as DBRegistryObject
from deepcore.core.objects.schemas import PreviewArtifact, PreviewArtifactType, SyncStatus, SyncRunState
from deepcore.runtime.composition import get_application

router = APIRouter(prefix="/connectors", tags=["connectors"])

class PreviewRequest(BaseModel):
    provider_id: str
    location: str
    config: Optional[dict] = None

class SyncRequest(BaseModel):
    provider_id: str
    location: str
    source_id: Optional[int] = None

class DisconnectRequest(BaseModel):
    source_id: int
    option: str  # "purge" or "freeze"

import json

class ConnectorCreateRequest(BaseModel):
    name: str
    provider_id: str
    location: str
    kind: str = "filesystem"
    config_json: Optional[str] = None

@router.post("", response_model=dict)
def register_connector(request: ConnectorCreateRequest, db: Session = Depends(get_db)):
    try:
        app = get_application()
        
        # Load and parse config context if supplied
        config_dct = None
        if request.config_json:
            try:
                config_dct = json.loads(request.config_json)
            except Exception:
                pass
                
        app.preview_service.validate_source(request.provider_id, request.location, config_dct)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    existing = db.query(DBKnowledgeSource).filter(
        DBKnowledgeSource.provider_id == request.provider_id,
        DBKnowledgeSource.location == request.location
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="A connector for this source is already registered.")
        
    from deepcore.storage.sqlite.models import Workspace
    personal_ws = db.query(Workspace).filter(Workspace.name == "Personal Workspace").first()
    workspace_id = personal_ws.id if personal_ws else 1
    
    # Save config_json
    config_json = request.config_json
    if not config_json:
        if request.provider_id == "calendar":
            config_json = json.dumps({"mock_file_path": request.location})
        elif request.provider_id == "spotlight":
            config_json = json.dumps({"search_path": request.location, "file_types": [".md"]})
        else:
            config_json = json.dumps({"path": request.location})
            
    src = DBKnowledgeSource(
        workspace_id=workspace_id,
        provider_id=request.provider_id,
        kind=request.kind,
        name=request.name,
        location=request.location,
        config_json=config_json,
        status="Configured"
    )
    db.add(src)
    db.commit()
    db.refresh(src)
    
    return {
        "id": src.id,
        "uuid": src.uuid,
        "provider_id": src.provider_id,
        "kind": src.kind,
        "name": src.name,
        "location": src.location,
        "status": src.status,
        "created_at": src.created_at.isoformat(),
        "updated_at": src.updated_at.isoformat()
    }

# GET /api/connectors
@router.get("", response_model=List[dict])
def get_connectors(db: Session = Depends(get_db)):
    sources = db.query(DBKnowledgeSource).all()
    results = []
    for src in sources:
        # Get last sync run for this source
        last_run = db.query(DBSyncRun).filter(DBSyncRun.source_id == src.id).order_by(DBSyncRun.started_at.desc()).first()
        results.append({
            "id": src.id,
            "uuid": src.uuid,
            "provider_id": src.provider_id,
            "kind": src.kind,
            "name": src.name,
            "location": src.location,
            "status": src.status,
            "created_at": src.created_at,
            "updated_at": src.updated_at,
            "last_sync_time": last_run.finished_at.isoformat() if last_run and last_run.finished_at else (last_run.started_at.isoformat() if last_run else None),
            "last_sync_status": last_run.status if last_run else None,
            "last_run_uuid": last_run.uuid if last_run else None,
        })
    return results

# POST /api/connectors/preview
@router.post("/preview")
def preview_connector(request: PreviewRequest):
    app = get_application()
    try:
        total = app.preview_service.estimate_import(request.provider_id, request.location, request.config)
        preview_items = app.preview_service.enumerate_preview(request.provider_id, request.location, request.config)
        return {
            "total_artifacts": total,
            "preview": preview_items
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal scan failure: {e}")

# POST /api/connectors/sync
@router.post("/sync", response_model=SyncStatus)
def trigger_sync(request: SyncRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    app = get_application()
    
    # 1. Validate source path first using PreviewService
    try:
        app.preview_service.validate_source(request.provider_id, request.location)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Check for duplicate sync (already running)
    active_run = db.query(DBSyncRun).filter(
        DBSyncRun.provider == request.provider_id,
        DBSyncRun.source_location == request.location,
        DBSyncRun.status == "running"
    ).first()
    if active_run:
        raise HTTPException(status_code=409, detail="A synchronization task is already active for this source.")

    # 3. Resolve or create KnowledgeSource
    src = None
    if request.source_id:
        src = db.query(DBKnowledgeSource).filter(DBKnowledgeSource.id == request.source_id).first()
    if not src:
        src = db.query(DBKnowledgeSource).filter(
            DBKnowledgeSource.provider_id == request.provider_id,
            DBKnowledgeSource.location == request.location
        ).first()
    if not src:
        from deepcore.storage.sqlite.models import Workspace
        personal_ws = db.query(Workspace).filter(Workspace.name == "Personal Workspace").first()
        workspace_id = personal_ws.id if personal_ws else 1
        src = DBKnowledgeSource(
            workspace_id=workspace_id,
            provider_id=request.provider_id,
            kind="filesystem" if request.provider_id in ("markdown", "markdown_provider") else "api",
            name=os.path.basename(request.location) or request.provider_id,
            location=request.location,
            status="Configured"
        )
        db.add(src)
        db.commit()
        db.refresh(src)

    # 4. Create SyncRun record initially in RUNNING state
    import uuid
    run_uuid = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    
    # Estimate total artifacts
    total_artifacts = 0
    try:
        total_artifacts = app.preview_service.estimate_import(request.provider_id, request.location)
    except Exception:
        pass

    db_run = DBSyncRun(
        uuid=run_uuid,
        provider=request.provider_id,
        source_location=request.location,
        started_at=started_at,
        status="running",
        progress=0.0,
        objects_scanned=total_artifacts,
        source_id=src.id,
        workspace_id=src.workspace_id
    )
    db.add(db_run)
    db.commit()
    db.refresh(db_run)

    # 5. Launch sync task in background
    background_tasks.add_task(
        run_sync_worker,
        provider_id=request.provider_id,
        location=request.location,
        workspace_id=src.workspace_id,
        source_id=src.id,
        run_uuid=run_uuid
    )

    return SyncStatus(
        run_id=run_uuid,
        state=SyncRunState.RUNNING,
        processed=0,
        total=total_artifacts,
        progress=0.0,
        current_artifact=None,
        started_at=started_at,
        updated_at=started_at,
        warnings=[],
        errors=[]
    )

# POST /api/connectors/sync/{run_uuid}/cancel
@router.post("/sync/{run_uuid}/cancel", response_model=SyncStatus)
def cancel_sync(run_uuid: str, db: Session = Depends(get_db)):
    run = db.query(DBSyncRun).filter(DBSyncRun.uuid == run_uuid).first()
    if not run:
        raise HTTPException(status_code=404, detail="Sync run not found.")
    
    if run.status == "running":
        run.status = "cancelled"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
    
    warnings = []
    errors = []
    if run.errors_json:
        try:
            parsed = json.loads(run.errors_json)
            if isinstance(parsed, list):
                errors = parsed
            elif isinstance(parsed, dict):
                errors = [parsed.get("error") or str(parsed)]
            else:
                errors = [str(parsed)]
        except Exception:
            errors = [run.errors_json]

    # Map status string to Enum
    state_map = {
        "running": SyncRunState.RUNNING,
        "success": SyncRunState.COMPLETED,
        "completed": SyncRunState.COMPLETED,
        "failed": SyncRunState.FAILED,
        "cancelled": SyncRunState.CANCELLED,
        "paused": SyncRunState.PAUSED,
        "syncing": SyncRunState.RUNNING,
        "finished": SyncRunState.COMPLETED,
        "error": SyncRunState.FAILED
    }
    state = state_map.get(run.status.lower(), SyncRunState.FAILED)

    return SyncStatus(
        run_id=run.uuid,
        state=state,
        processed=run.objects_created + run.objects_existing + run.objects_updated,
        total=run.objects_scanned,
        progress=run.progress or 0.0,
        current_artifact=None,
        started_at=run.started_at,
        updated_at=run.finished_at or datetime.now(timezone.utc),
        warnings=warnings,
        errors=errors
    )

# GET /api/connectors/sync/{run_uuid}
@router.get("/sync/{run_uuid}", response_model=SyncStatus)
@router.get("/sync/status/{run_uuid}", response_model=SyncStatus)
def get_sync_status(run_uuid: str, db: Session = Depends(get_db)):
    run = db.query(DBSyncRun).filter(DBSyncRun.uuid == run_uuid).first()
    if not run:
        raise HTTPException(status_code=404, detail="Sync run not found.")
    
    # Map status string to Enum
    state_map = {
        "running": SyncRunState.RUNNING,
        "success": SyncRunState.COMPLETED,
        "completed": SyncRunState.COMPLETED,
        "failed": SyncRunState.FAILED,
        "cancelled": SyncRunState.CANCELLED,
        "paused": SyncRunState.PAUSED,
        "syncing": SyncRunState.RUNNING,
        "finished": SyncRunState.COMPLETED,
        "error": SyncRunState.FAILED
    }
    state = state_map.get(run.status.lower(), SyncRunState.FAILED)
    
    errors = []
    if run.errors_json:
        try:
            parsed = json.loads(run.errors_json)
            if isinstance(parsed, list):
                errors = parsed
            elif isinstance(parsed, dict):
                errors = [parsed.get("error") or str(parsed)]
            else:
                errors = [str(parsed)]
        except Exception:
            errors = [run.errors_json]

    if run.error_message:
        errors.append(run.error_message)

    current_art = None
    if run.telemetry_json:
        try:
            telemetry = json.loads(run.telemetry_json)
            current_art = telemetry.get("current_artifact")
        except Exception:
            pass

    return SyncStatus(
        run_id=run.uuid,
        state=state,
        processed=run.objects_created + run.objects_existing + run.objects_updated,
        total=run.objects_scanned,
        progress=run.progress or 0.0,
        current_artifact=current_art,
        started_at=run.started_at,
        updated_at=run.finished_at or datetime.now(timezone.utc),
        warnings=[],
        errors=errors
    )

# POST /api/connectors/{source_id}/disconnect
@router.post("/{source_id}/disconnect")
def disconnect_connector(source_id: int, option: str = "freeze", db: Session = Depends(get_db)):
    src = db.query(DBKnowledgeSource).filter(DBKnowledgeSource.id == source_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="Knowledge source not found.")
    
    if option == "purge":
        # Delete all registry objects associated with this source
        db.query(DBRegistryObject).filter(DBRegistryObject.source_id == src.id).delete(synchronize_session=False)
        db.delete(src)
        db.commit()
    elif option == "freeze":
        # Keep objects but decouple them from the source system
        db.query(DBRegistryObject).filter(DBRegistryObject.source_id == src.id).update(
            {"source_id": None}, synchronize_session=False
        )
        db.delete(src)
        db.commit()
    else:
        raise HTTPException(status_code=400, detail="Invalid disconnect option. Must be 'purge' or 'freeze'.")
    
    return {"status": "success", "message": f"Source disconnected with option '{option}'."}

# Background worker
def run_sync_worker(provider_id: str, location: str, workspace_id: int, source_id: int, run_uuid: str):
    from deepcore.storage.sqlite.db import SessionLocal
    db = SessionLocal()
    try:
        app = get_application()
        app.ingestion_service.sync_provider_v2(
            provider_name=provider_id,
            db=db,
            path=location,
            workspace_id=workspace_id,
            source_id=source_id,
            run_uuid=run_uuid
        )
    except Exception as e:
        run = db.query(DBSyncRun).filter(DBSyncRun.uuid == run_uuid).first()
        if run and run.status == "running":
            run.status = "failed"
            run.finished_at = datetime.now(timezone.utc)
            run.error_message = str(e)
            db.commit()
    finally:
        db.close()
