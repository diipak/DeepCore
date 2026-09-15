from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from deepcore2.storage.sqlite.db import get_db
from deepcore2.core.objects import schemas
from deepcore2.core.content.service import ContentService

router = APIRouter(prefix="/content", tags=["content"])

class ContentSearchResult(BaseModel):
    object: schemas.RegistryObject
    content: schemas.ContentIndex

@router.get("/search", response_model=List[ContentSearchResult])
def search_content_api(
    query: str,
    db: Session = Depends(get_db)
):
    """Search indexed content endpoint."""
    service = ContentService(db)
    results = service.search_content(query)
    # Map the list of tuples (DBRegistryObject, DBContentIndex) to the Pydantic schema
    return [ContentSearchResult(object=obj, content=idx) for obj, idx in results]

@router.get("/{object_id}", response_model=schemas.ContentIndex)
def get_content_api(
    object_id: str,
    db: Session = Depends(get_db)
):
    """Retrieve indexed content for a registry object endpoint."""
    service = ContentService(db)
    idx = service.get_content(object_id)
    if not idx:
        raise HTTPException(status_code=404, detail=f"Content for object '{object_id}' not found")
    return idx
