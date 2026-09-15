from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from deepcore2.storage.sqlite.db import get_db
from deepcore2.intelligence import ContextRequest, ContextPackage

router = APIRouter(prefix="/assistant", tags=["assistant"])

@router.get("/chat")
@router.post("/chat")
def assistant_chat_placeholder():
    """Placeholder for future Assistant Chat API."""
    raise HTTPException(status_code=501, detail="Assistant chat API is not implemented yet")

@router.post("/context", response_model=ContextPackage)
def build_context_api_post(
    request: ContextRequest,
    db: Session = Depends(get_db)
):
    """
    Build context package using ContextRequest payload.
    """
    from deepcore2.runtime.composition import get_application
    app = get_application()
    engine = app.get_context_service(db)
    return engine.build_context(request)

@router.get("/context", response_model=ContextPackage)
def build_context_api_get(
    trigger_uuid: Optional[str] = None,
    query: Optional[str] = None,
    max_concepts: int = 10,
    max_memories: int = 10,
    db: Session = Depends(get_db)
):
    """
    Build context package using query parameters.
    """
    request = ContextRequest(
        trigger_object_uuid=trigger_uuid,
        query=query,
        max_concepts=max_concepts,
        max_memories=max_memories
    )
    from deepcore2.runtime.composition import get_application
    app = get_application()
    engine = app.get_context_service(db)
    return engine.build_context(request)

