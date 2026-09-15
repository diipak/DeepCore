from typing import List, Optional
from pydantic import BaseModel
from deepcore2.core.evidence.schemas import Evidence

class ThinkingModeDescriptor(BaseModel):
    id: str
    name: str
    description: str
    icon: str

class Message(BaseModel):
    uuid: str
    role: str
    content: str
    evidence: Optional[List[Evidence]] = None
    created_at: str

class ConversationState(BaseModel):
    session_uuid: str
    conversation_uuid: str
    active_thinking_mode: str
    focus_intent: List[dict]
    awareness: dict
    context_package: dict
    title: str
    messages: List[Message]
    created_at: str
    updated_at: str

# Default built-in thinking modes
BUILTIN_THINKING_MODES = [
    ThinkingModeDescriptor(
        id="CONTINUE_THINKING",
        name="Continue Thinking",
        description="Focuses on restoring context and developing the current thought.",
        icon="Brain"
    ),
    ThinkingModeDescriptor(
        id="RECOVER_CONTEXT",
        name="Recover Context",
        description="Recalls what was active during a past time window.",
        icon="Clock"
    ),
    ThinkingModeDescriptor(
        id="EXPLORE_RELATIONSHIPS",
        name="Explore Relationships",
        description="Maps connections between themes and notes.",
        icon="Link"
    ),
    ThinkingModeDescriptor(
        id="CHALLENGE_ASSUMPTIONS",
        name="Challenge Assumptions",
        description="Scans for conflicts or contradictions in the knowledge web.",
        icon="AlertTriangle"
    ),
    ThinkingModeDescriptor(
        id="SUMMARIZE_THEME",
        name="Summarize Theme",
        description="Compiles conceptual definitions.",
        icon="FileText"
    )
]
