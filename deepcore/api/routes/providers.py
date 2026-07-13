import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from deepcore.storage.sqlite.db import get_db
from deepcore.core.objects import schemas
from deepcore.core.registry.service import RegistryService
from deepcore.core.content.service import ContentService
from deepcore.core.providers.markdown import MarkdownProvider

router = APIRouter(prefix="/providers", tags=["providers"])

class ProviderSyncRequest(BaseModel):
    path: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

@router.post("/{provider}/sync", response_model=schemas.SyncRun)
def sync_provider_endpoint(
    provider: str,
    request: ProviderSyncRequest,
    db: Session = Depends(get_db)
):
    """
    Trigger synchronization for a specific provider.
    Specifically supports 'markdown' for local folder ingestion.
    """
    if provider.lower() != "markdown":
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{provider}' is not supported for synchronization. Supported providers: ['markdown']"
        )

    if not request.path:
        raise HTTPException(
            status_code=400,
            detail="The 'path' parameter is required for the markdown provider sync."
        )

    if not os.path.isdir(request.path):
        raise HTTPException(
            status_code=400,
            detail=f"Directory path '{request.path}' does not exist or is not a directory."
        )

    # 1. Instantiate the Markdown Provider and Registry Service
    prov = MarkdownProvider(root_path=request.path)
    registry_service = RegistryService(db)

    # 2. Run sync (which creates/updates Canonical Objects in the DB)
    # The provider is kept pure; it does not do content indexing.
    synced_objs = prov.sync(registry_service)

    # 3. Downstream Processing: Index the content of newly registered, updated, or active objects
    content_service = ContentService(db)
    # Re-evaluate and index newly created or updated objects to verify text preview availability
    active_objs = registry_service.list_objects(filters={
        "source_system": "markdown",
        "status": "active"
    })
    for obj in active_objs:
        if obj.location and os.path.exists(obj.location):
            # Index object (this updates or creates ContentIndex record)
            content_service.index_object(obj.id)

    # 4. Fetch and return the latest sync run details for audit verification
    runs = registry_service.list_sync_runs()
    latest_run = next((r for r in runs if r.provider == "markdown" and r.source_location == request.path), None)
    if not latest_run:
        raise HTTPException(
            status_code=500,
            detail="Sync completed, but no sync run record was persisted in the database."
        )

    return latest_run
