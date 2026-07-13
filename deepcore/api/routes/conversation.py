from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from deepcore.storage.sqlite.db import get_db

from deepcore.runtime.tools.registry import ToolRegistry, ExecutionRegistry as ToolExecRegistry
from deepcore.runtime.tools.runtime import ToolRuntime
from deepcore.runtime.skills.registry import SkillRegistry
from deepcore.runtime.skills.runtime import SkillRuntime
from deepcore.runtime.execution.registry import ExecutionRegistry
from deepcore.runtime.execution.runtime import ExecutionRuntime
from deepcore.runtime.planner.runtime import PlannerRuntime
from deepcore.runtime.conversation.base import ConversationRequest, ConversationResponse, ConversationDescriptor
from deepcore.runtime.conversation.runtime import ConversationRuntime

from deepcore.runtime.composition import get_application

router = APIRouter(prefix="/conversation", tags=["conversation"])


@router.post("", response_model=ConversationResponse)
def execute_conversation(
    request: ConversationRequest,
    db: Session = Depends(get_db)
):
    """Process a conversation request using the runtime pipeline."""
    app = get_application()
    return app.conversation_service.execute(request, db)


@router.get("/capabilities", response_model=ConversationDescriptor)
def get_capabilities():
    """Exposes the conversation capabilities descriptor."""
    app = get_application()
    return app.conversation_service.get_descriptor()
