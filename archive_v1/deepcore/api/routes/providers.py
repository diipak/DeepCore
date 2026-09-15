import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from deepcore.storage.sqlite.db import get_db
from deepcore.core.objects import schemas
from deepcore.api.dependencies import get_execution_context

router = APIRouter(prefix="/providers", tags=["providers"])

class ProviderSyncRequest(BaseModel):
    path: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

@router.post("/{provider}/sync", response_model=schemas.SyncRun)
def sync_provider_endpoint(
    provider: str,
    request: ProviderSyncRequest,
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """
    Trigger synchronization for a specific provider.
    Delegates all provider instantiation, execution, and downstream callbacks to IngestionRuntime.
    """
    if not request.path:
        raise HTTPException(
            status_code=400,
            detail="The 'path' parameter is required for provider synchronization."
        )

    if not os.path.isdir(request.path):
        raise HTTPException(
            status_code=400,
            detail=f"Directory path '{request.path}' does not exist or is not a directory."
        )

    from deepcore.runtime.composition import get_application
    app = get_application()

    try:
        return app.ingestion_service.sync_provider(
            provider_name=provider,
            db=db,
            path=request.path,
            workspace_id=context.workspace_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

