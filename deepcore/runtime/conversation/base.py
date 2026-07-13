from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Import existing core contracts to prevent duplication
from deepcore.runtime.execution.base import ExecutionArtifact
from deepcore.runtime.planner.base import PlannerResult

class ConversationMode(str, Enum):
    DIRECT = "direct"
    PLANNING = "planning"

class ConversationStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"
    CANCELLED = "cancelled"

class ConversationMessage(BaseModel):
    role: str  # "user", "assistant", etc.
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConversationRequest(BaseModel):
    conversation_id: str
    message: ConversationMessage
    mode: ConversationMode = ConversationMode.DIRECT
    history: List[ConversationMessage] = Field(default_factory=list)
    context_object_uuid: Optional[str] = None

class ConversationDiagnostics(BaseModel):
    execution_time_ms: float
    context_retrieved: bool = False
    planner_invoked: bool = False

class ConversationResponse(BaseModel):
    conversation_id: str
    status: ConversationStatus
    response_message: ConversationMessage
    planner_result: Optional[PlannerResult] = None
    artifacts: List[ExecutionArtifact] = Field(default_factory=list)
    diagnostics: ConversationDiagnostics
    error_message: Optional[str] = None

from deepcore.runtime.descriptors import BaseDescriptor

class ConversationDescriptor(BaseDescriptor):
    supported_modes: List[ConversationMode]
    supports_context: bool
    supports_planning: bool
    supports_streaming: bool
    supports_models: List[str]

