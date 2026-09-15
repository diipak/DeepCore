from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from deepcore2.storage.sqlite.db import get_db
from deepcore2.api.dependencies import get_execution_context
from deepcore2.core.objects import schemas
from deepcore2.core.assistant.schema import ConversationState, ThinkingModeDescriptor, BUILTIN_THINKING_MODES
from deepcore2.core.assistant.service import ConversationService

router = APIRouter(tags=["conversations"])

class StartSessionRequest(BaseModel):
    thinking_mode: str
    active_object_uuid: Optional[str] = None

class PostMessageRequest(BaseModel):
    content: str

def get_conversation_service(
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
) -> ConversationService:
    """Dependency provider injecting wired ConversationService from running Application."""
    try:
        from deepcore2.runtime.composition import get_application
        app = get_application()
        return app.get_conversation_service(db, workspace_id=context.workspace_id)
    except Exception:
        return ConversationService(db, workspace_id=context.workspace_id)


@router.get("/conversations/modes", response_model=List[ThinkingModeDescriptor])
def get_thinking_modes():
    """Retrieve all dynamically registered and built-in thinking mode descriptors."""
    return BUILTIN_THINKING_MODES

@router.post("/conversations/start", response_model=ConversationState)
def start_thinking_session(
    request: StartSessionRequest,
    service: ConversationService = Depends(get_conversation_service)
):
    """Start a new Thinking Session and its associated conversation."""
    try:
        return service.start_session(request.thinking_mode, request.active_object_uuid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/conversations/{uuid}/messages", response_model=ConversationState)
def continue_conversation(
    uuid: str,
    request: PostMessageRequest,
    service: ConversationService = Depends(get_conversation_service)
):
    """Post a message and evolve the active Thinking Session conversation."""
    try:
        return service.post_message(uuid, request.content)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/conversations/{uuid}", response_model=ConversationState)
def restore_conversation(
    uuid: str,
    service: ConversationService = Depends(get_conversation_service)
):
    """Retrieve current state and messages history for a Thinking Session."""
    try:
        return service.get_session_state(uuid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/conversations/{uuid}/audio")
async def process_conversation_audio(
    uuid: str,
    file: UploadFile = File(...),
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Process an audio turn: transcribes speech, posts to ConversationService,
    and returns synthesized voice reply as WAV audio with transcript metadata in headers.
    """
    import urllib.parse
    from deepcore2.runtime.audio.service import AudioService

    audio_service = AudioService(service)

    audio_bytes = await file.read()
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "wav"

    from starlette.concurrency import run_in_threadpool

    try:
        state, audio_reply_bytes, transcript = await run_in_threadpool(
            audio_service.process_voice_turn,
            session_uuid=uuid,
            audio_bytes=audio_bytes,
            audio_format=ext
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio turn processing failed: {e}")

    headers = {
        "X-User-Transcript": urllib.parse.quote(transcript),
        "X-Session-UUID": state.session_uuid,
        "X-Assistant-Message-UUID": state.messages[-1].uuid if state.messages else "",
    }
    return Response(content=audio_reply_bytes, media_type="audio/wav", headers=headers)
