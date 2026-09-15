from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from deepcore.storage.sqlite.db import get_db
from deepcore.api.dependencies import get_execution_context
from deepcore.core.objects import schemas
from deepcore.core.assistant.schema import ConversationState, ThinkingModeDescriptor, BUILTIN_THINKING_MODES
from deepcore.core.assistant.service import ConversationService

router = APIRouter(tags=["conversations"])

class StartSessionRequest(BaseModel):
    thinking_mode: str
    active_object_uuid: Optional[str] = None

class PostMessageRequest(BaseModel):
    content: str

@router.get("/conversations/modes", response_model=List[ThinkingModeDescriptor])
def get_thinking_modes():
    """Retrieve all dynamically registered and built-in thinking mode descriptors."""
    return BUILTIN_THINKING_MODES

@router.post("/conversations/start", response_model=ConversationState)
def start_thinking_session(
    request: StartSessionRequest,
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """Start a new Thinking Session and its associated conversation."""
    service = ConversationService(db, context.workspace_id)
    try:
        return service.start_session(request.thinking_mode, request.active_object_uuid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/conversations/{uuid}/messages", response_model=ConversationState)
def continue_conversation(
    uuid: str,
    request: PostMessageRequest,
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """Post a message and evolve the active Thinking Session conversation."""
    service = ConversationService(db, context.workspace_id)
    try:
        return service.post_message(uuid, request.content)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/conversations/{uuid}", response_model=ConversationState)
def restore_conversation(
    uuid: str,
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """Retrieve current state and messages history for a Thinking Session."""
    service = ConversationService(db, context.workspace_id)
    try:
        return service.get_session_state(uuid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
