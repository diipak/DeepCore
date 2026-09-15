import json
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from deepcore.storage.sqlite.models import (
    ThinkingSession as DBThinkingSession,
    Conversation as DBConversation,
    Message as DBMessage,
    RegistryObject as DBRegistryObject
)
from deepcore.core.awareness.service import AwarenessService
from deepcore.core.evidence.schemas import Evidence
from deepcore.core.assistant.schema import ConversationState, Message as SchemaMessage
from deepcore.core.content.service import ContentService
from deepcore.intelligence import ContextEngine, ContextRequest, GroundedPromptBuilder
from deepcore.intelligence.llm_client import OllamaClient, LLMUnavailableError


class ConversationRepository:
    """Isolates all SQLAlchemy persistence details from conversation orchestration."""
    def __init__(self, db: Session, workspace_id: int = 1):
        self.db = db
        self.workspace_id = workspace_id

    def create_session(self, title: str, active_thinking_mode: str) -> DBThinkingSession:
        session = DBThinkingSession(
            title=title,
            active_thinking_mode=active_thinking_mode,
            workspace_id=self.workspace_id
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, uuid: str) -> Optional[DBThinkingSession]:
        return self.db.query(DBThinkingSession).filter(
            DBThinkingSession.uuid == uuid,
            DBThinkingSession.workspace_id == self.workspace_id
        ).first()

    def create_conversation(self, thinking_session_id: int) -> DBConversation:
        conversation = DBConversation(
            thinking_session_id=thinking_session_id,
            workspace_id=self.workspace_id
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_conversation_by_session_id(self, session_id: int) -> Optional[DBConversation]:
        return self.db.query(DBConversation).filter(
            DBConversation.thinking_session_id == session_id,
            DBConversation.workspace_id == self.workspace_id
        ).first()

    def get_object_by_uuid(self, uuid: str) -> Optional[DBRegistryObject]:
        return self.db.query(DBRegistryObject).filter(
            DBRegistryObject.uuid == uuid,
            DBRegistryObject.workspace_id == self.workspace_id
        ).first()

    def add_message(self, conversation_id: int, role: str, content: str, evidence_json: Optional[str] = None) -> DBMessage:
        msg = DBMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            evidence_json=evidence_json
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_messages(self, conversation_id: int) -> List[DBMessage]:
        return self.db.query(DBMessage).filter(
            DBMessage.conversation_id == conversation_id
        ).order_by(DBMessage.created_at.asc()).all()


class ConversationService:
    """Orchestrates Thinking Sessions and Conversations, feeding them with AwarenessState and grounded LLM replies."""
    def __init__(self, db: Session, workspace_id: int = 1, llm_client: Optional[OllamaClient] = None):
        self.repo = ConversationRepository(db, workspace_id)
        self.awareness = AwarenessService(db, workspace_id)
        self._llm_client = llm_client
        self.prompt_builder = GroundedPromptBuilder()

    @property
    def llm_client(self) -> OllamaClient:
        """Lazily construct the default OllamaClient so tests can inject a mock instead."""
        if self._llm_client is None:
            self._llm_client = OllamaClient()
        return self._llm_client

    def start_session(self, thinking_mode: str, active_object_uuid: Optional[str] = None) -> ConversationState:
        # Determine Title
        title = "Reflective Thought Session"
        if active_object_uuid:
            obj = self.repo.get_object_by_uuid(active_object_uuid)
            if obj:
                title = f"Exploring: {obj.title}"

        # Create session & conversation
        session = self.repo.create_session(title, thinking_mode)
        conversation = self.repo.create_conversation(session.id)

        # Pre-seed Assistant initial greetings based on Thinking Mode
        self._seed_greet_message(conversation.id, thinking_mode, title)

        return self.get_session_state(session.uuid)

    def get_session_state(self, session_uuid: str) -> ConversationState:
        session = self.repo.get_session(session_uuid)
        if not session:
            raise ValueError(f"Thinking Session '{session_uuid}' not found.")

        conversation = self.repo.get_conversation_by_session_id(session.id)
        if not conversation:
            raise ValueError(f"No conversation associated with Thinking Session '{session_uuid}'.")

        # Compile platform context & awareness details
        awareness_data = self.awareness.get_awareness_state()
        focus_intent = awareness_data["focus"]
        
        # Build ContextPackage
        context_package = {
            "focus_count": len(focus_intent),
            "observations_count": len(awareness_data["understanding"]),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Format Messages
        messages = []
        db_messages = self.repo.get_messages(conversation.id)
        for msg in db_messages:
            evidence_list = []
            if msg.evidence_json:
                try:
                    ev_data = json.loads(msg.evidence_json)
                    evidence_list = [Evidence(**e) for e in ev_data]
                except Exception:
                    pass

            messages.append(SchemaMessage(
                uuid=msg.uuid,
                role=msg.role,
                content=msg.content,
                evidence=evidence_list,
                created_at=msg.created_at.isoformat()
            ))

        return ConversationState(
            session_uuid=session.uuid,
            conversation_uuid=conversation.uuid,
            active_thinking_mode=session.active_thinking_mode,
            focus_intent=focus_intent,
            awareness={
                "summary": awareness_data["summary"],
                "observations": awareness_data["understanding"]
            },
            context_package=context_package,
            title=session.title,
            messages=messages,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat()
        )

    def post_message(self, session_uuid: str, content: str) -> ConversationState:
        session = self.repo.get_session(session_uuid)
        if not session:
            raise ValueError(f"Thinking Session '{session_uuid}' not found.")

        conversation = self.repo.get_conversation_by_session_id(session.id)
        if not conversation:
            raise ValueError(f"No conversation associated with Thinking Session '{session_uuid}'.")

        # Fetch prior message history BEFORE adding current user message
        history_messages = self.repo.get_messages(conversation.id)

        # Save User Message
        self.repo.add_message(conversation.id, "user", content)

        # Generate Assistant Answer (Grounded thinking response)
        reply, evidence = self._generate_thoughtful_reply(content, conversation.id, history_messages)

        # Save Assistant Message
        evidence_json = json.dumps([e.model_dump() for e in evidence]) if evidence else None
        self.repo.add_message(conversation.id, "assistant", reply, evidence_json)

        return self.get_session_state(session_uuid)

    def _seed_greet_message(self, conversation_id: int, mode: str, focus_title: str):
        greetings = {
            "CONTINUE_THINKING": f"Welcome back. Let's continue thinking about {focus_title}. Where should we deepen our focus?",
            "RECOVER_CONTEXT": "Restoring your recent focus context. Here are your active notes and events from the past days. What would you like to review?",
            "EXPLORE_RELATIONSHIPS": "Ready to map relationships. Let's trace how your notes connect to core concepts. Tell me a concept or note to start from.",
            "CHALLENGE_ASSUMPTIONS": "System observations loaded. Let's examine contradictions, orphaned notes, or gaps in your thinking.",
            "SUMMARIZE_THEME": "Theme compilation active. Give me a group of notes or a concept, and I will compile its definitions and key findings."
        }
        greet = greetings.get(mode, f"Thinking Session started on mode {mode}.")
        self.repo.add_message(conversation_id, "assistant", greet)

    def _generate_thoughtful_reply(
        self,
        query: str,
        conversation_id: int,
        history_messages: Optional[List[DBMessage]] = None
    ) -> tuple[str, List[Evidence]]:
        # 1. Deterministic Context Retrieval
        ctx_engine = ContextEngine(self.repo.db, workspace_id=self.repo.workspace_id)
        context_package = ctx_engine.build_context(ContextRequest(query=query))
        content_service = ContentService(self.repo.db)

        # 2. Build Bounded Grounded Prompt
        prompt = self.prompt_builder.build_prompt(
            query=query,
            context_package=context_package,
            content_service=content_service,
            history_messages=history_messages
        )

        # 3. Local LLM Generation with Graceful Failure Handling
        try:
            reply = self.llm_client.generate(prompt)
            if not reply:
                reply = (
                    "The local model returned an empty response. "
                    "Check that the configured Ollama model is pulled and running."
                )
        except LLMUnavailableError as exc:
            reply = f"I couldn't reach the local model: {exc}"

        # 4. Construct Evidence References
        evidence = []
        if context_package and context_package.memories:
            for ctx_mem in context_package.memories:
                ref = ctx_mem.memory
                evidence.append(Evidence(
                    source_uuid=ref.uuid,
                    target_uuid=ref.uuid,
                    relationship_path=["note", ref.object_type],
                    reason=f"Retrieved note '{ref.title}' relevant to query",
                    confidence=0.95
                ))

        return reply, evidence


