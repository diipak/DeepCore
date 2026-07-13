from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from deepcore.storage.sqlite.db import get_db
from deepcore.core.objects import schemas
from deepcore.core.registry.service import RegistryService

router = APIRouter(prefix="/memories", tags=["memories"])

@router.get("/recent", response_model=List[schemas.RegistryObject])
def recent_memories_api(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Retrieve newest active human-created knowledge sources ordered by created_at descending."""
    service = RegistryService(db)
    return service.recent_memories(limit=limit)
