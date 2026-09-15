from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from deepcore2.storage.sqlite.db import get_db
from deepcore2.core.objects import schemas
from deepcore2.core.registry.service import RegistryService

router = APIRouter(prefix="/objects", tags=["objects"])

@router.post("", response_model=schemas.RegistryObject, status_code=201)
def create_object(obj: schemas.RegistryObjectCreate, db: Session = Depends(get_db)):
    """Register a new object in the DeepCore registry."""
    service = RegistryService(db)
    try:
        return service.register_object(obj)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=List[schemas.RegistryObject])
def list_objects(
    object_type: Optional[schemas.ObjectType] = None,
    source_system: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieve list of registry objects, optionally filtered."""
    service = RegistryService(db)
    filters = {
        "object_type": object_type.value if object_type else None,
        "source_system": source_system,
        "status": status
    }
    # Filter out None keys for cleaner queries
    active_filters = {k: v for k, v in filters.items() if v is not None}
    return service.list_objects(filters=active_filters)

@router.get("/{id_or_uuid}", response_model=schemas.RegistryObject)
def get_object(id_or_uuid: str, db: Session = Depends(get_db)):
    """Retrieve a single registry object by its numeric ID or string UUID."""
    service = RegistryService(db)
    obj = service.get_object(id_or_uuid)
    if not obj:
        raise HTTPException(status_code=404, detail=f"Object '{id_or_uuid}' not found")
    return obj


capture_router = APIRouter(tags=["capture"])

@capture_router.post("/capture", response_model=schemas.RegistryObject, status_code=201)
def capture_content(request: schemas.CaptureRequest, db: Session = Depends(get_db)):
    """Universal intake endpoint for capturing new assets."""
    from deepcore2.core.capture.service import CaptureService, UnsupportedInputError
    service = CaptureService(db)
    try:
        return service.capture(request.content)
    except UnsupportedInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
