import json
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from deepcore2.storage.sqlite.models import (
    ThinkingSession as DBThinkingSession,
    Conversation as DBConversation,
    Message as DBMessage,
    RegistryObject as DBRegistryObject
)
from deepcore2.core.awareness.service import AwarenessService
from deepcore2.core.evidence.schemas import Evidence
from deepcore2.core.assistant.schema import ConversationState, Message as SchemaMessage
from deepcore2.core.content.service import ContentService
from deepcore2.intelligence import ContextEngine, ContextRequest, GroundedPromptBuilder
from deepcore2.intelligence.llm_client import OllamaClient, LLMUnavailableError
from deepcore2.intelligence.openmemory_client import (
    OpenMemoryClient,
    OpenMemoryUnavailableError,
    OpenMemoryItem,
)
from deepcore2.intelligence.vault_service import VaultService, VaultSecurityError
from deepcore2.runtime.tools.registry import ToolRegistry, ExecutionRegistry
from deepcore2.runtime.tools.runtime import ToolRuntime
from deepcore2.runtime.tools.base import ToolRequest
from deepcore2.core.security import redact_secrets
from uuid import uuid4


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
    def __init__(
        self,
        db: Session,
        workspace_id: int = 1,
        llm_client: Optional[OllamaClient] = None,
        openmemory_client: Optional[OpenMemoryClient] = None,
        vault_service: Optional[VaultService] = None,
        tool_registry: Optional[ToolRegistry] = None,
        tool_runtime: Optional[ToolRuntime] = None,
    ):
        self.repo = ConversationRepository(db, workspace_id)
        self.awareness = AwarenessService(db, workspace_id)
        self._llm_client = llm_client
        self._openmemory_client = openmemory_client
        self._vault_service = vault_service
        self._tool_registry = tool_registry
        self._tool_runtime = tool_runtime
        self.prompt_builder = GroundedPromptBuilder()

    @property
    def llm_client(self) -> OllamaClient:
        """Lazily construct the default OllamaClient so tests can inject a mock instead."""
        if self._llm_client is None:
            self._llm_client = OllamaClient()
        return self._llm_client

    @property
    def openmemory_client(self) -> OpenMemoryClient:
        """Lazily construct the default OpenMemoryClient so tests can inject a mock instead."""
        if self._openmemory_client is None:
            self._openmemory_client = OpenMemoryClient()
        return self._openmemory_client

    @property
    def vault_service(self) -> VaultService:
        """Lazily construct the default VaultService so tests can inject a mock instead."""
        if self._vault_service is None:
            self._vault_service = VaultService()
        return self._vault_service

    @property
    def tool_registry(self) -> ToolRegistry:
        """Lazily construct or return ToolRegistry."""
        if self._tool_registry is None:
            try:
                from deepcore2.runtime.composition import get_application
                app = get_application()
                if app and app.tool_registry is not None:
                    self._tool_registry = app.tool_registry
                    return self._tool_registry
            except Exception:
                pass

            self._tool_registry = ToolRegistry()
            try:
                from deepcore2.runtime.tools.mcp_client import discover_and_register_mcp_tools
                discover_and_register_mcp_tools(self._tool_registry)
            except Exception:
                pass

        return self._tool_registry

    @property
    def tool_runtime(self) -> ToolRuntime:
        """Lazily construct or return ToolRuntime wrapping ExecutionRegistry."""
        if self._tool_runtime is None:
            try:
                from deepcore2.runtime.composition import get_application
                app = get_application()
                if app and app.tool_runtime is not None:
                    self._tool_runtime = app.tool_runtime
                    return self._tool_runtime
            except Exception:
                pass

            exec_reg = ExecutionRegistry(self.tool_registry)
            self._tool_runtime = ToolRuntime(exec_reg)
        return self._tool_runtime

    def remember(self, text: str, categories: Optional[List[str]] = None) -> OpenMemoryItem:
        """Persist an atomic fact or preference to OpenMemory with [DeepCore/...] tagging."""
        return self.openmemory_client.create_memory(text=text, categories=categories)

    def log_daily_summary(self, summary_text: str, title: Optional[str] = None) -> str:
        """Safely append a timestamped milestone block to AI/Daily/YYYY-MM-DD.md."""
        return self.vault_service.append_daily_log(summary_text, title=title)

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
        # 0. OpenMemory Cross-Agent Semantic Recall (Bounded, Privacy Filtered, Graceful Fallback)
        openmemory_items: List[OpenMemoryItem] = []
        try:
            openmemory_items = self.openmemory_client.search_memories(query=query, limit=3)
        except OpenMemoryUnavailableError as exc:
            import logging
            logging.getLogger(__name__).warning(f"OpenMemory unavailable, continuing with local notes only: {exc}")

        openmemory_blocks = [
            f"- [{item.app_name} | {','.join(item.categories)}] {item.content}"
            for item in openmemory_items
        ]

        # 1. Deterministic Context Retrieval
        ctx_engine = ContextEngine(self.repo.db, workspace_id=self.repo.workspace_id)
        context_package = ctx_engine.build_context(ContextRequest(query=query))
        content_service = ContentService(self.repo.db)

        # 2. Build Bounded Grounded Prompt
        prompt = self.prompt_builder.build_prompt(
            query=query,
            context_package=context_package,
            content_service=content_service,
            history_messages=history_messages,
            openmemory_blocks=openmemory_blocks,
        )

        # 3. Local LLM Generation with Bounded Tool Execution Loop (Invariant #8)
        reply = ""
        evidence: List[Evidence] = []

        # Prepare tool descriptors if tools are registered
        registered_descriptors = self.tool_registry.list_tools()
        ollama_tools = []
        for desc in registered_descriptors:
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": desc.name,
                    "description": desc.description,
                    "parameters": desc.input_schema,
                }
            })

        try:
            if ollama_tools:
                system_instruction = (
                    "You are DeepCore, the user's personal knowledge and homelab intelligence assistant.\n"
                    "You have direct access to tools for web search (duckduckgo_web_search, brave_web_search) and local filesystem access for notes and files (search_files, list_directory, read_text_file, get_file_info).\n\n"
                    "AUTONOMOUS TOOL USAGE RULES:\n"
                    "1. The user will ask in plain, natural conversational English without mentioning tool names or file paths (e.g., 'Look for latest iphone specs', 'See for the creator profile in notes', 'What is the news on SpaceX?').\n"
                    "2. If the user asks about external, real-time, or public information, autonomously call `duckduckgo_web_search` or `brave_web_search`.\n"
                    "3. If the user asks about notes, profiles, or files, autonomously call `search_files` (e.g. pattern='profile' or 'creator') or `list_directory` to find them, and `read_text_file` to inspect their contents. User profiles live in `AI/Profiles` (e.g. `Profile - Tech & Architecture.md`) and project specs in `AI/Specs`.\n"
                    "4. Never tell the user you lack information if you have an available tool that can find it. Call the tool first.\n"
                    "5. Only answer directly without calling tools if the verified context memories below already contain the complete, definitive answer."
                )
                messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ]
                msg_resp = self.llm_client.chat(messages=messages, tools=ollama_tools)
                if isinstance(msg_resp, dict):
                    msg = msg_resp
                    # Bounded tool-calling loop: maximum 2 iterations per turn
                    tool_rounds = 0
                    while isinstance(msg.get("tool_calls"), list) and msg.get("tool_calls") and tool_rounds < 2:
                        tool_rounds += 1
                        messages.append(msg)

                        for call in msg["tool_calls"]:
                            fn = call.get("function", {}) if isinstance(call, dict) else {}
                            func_name = fn.get("name", "")
                            args = fn.get("arguments", {})

                            # Execute via ToolRuntime
                            req = ToolRequest(request_id=uuid4().hex, inputs=args)
                            try:
                                tool_result = self.tool_runtime.execute(func_name, req)
                                raw_out = tool_result.outputs.get("content", "")
                                if not raw_out and tool_result.error_message:
                                    raw_out = f"Error: {tool_result.error_message}"
                            except Exception as exc:
                                raw_out = f"Tool execution failed: {exc}"

                            cleaned_out = redact_secrets(raw_out)

                            # Record Evidence citation for WorkspaceCanvas
                            evidence.append(Evidence(
                                source_uuid=f"mcp-{func_name}",
                                target_uuid=f"mcp-{func_name}",
                                relationship_path=["tool", func_name],
                                reason=f"Live tool execution ({func_name}): {cleaned_out[:80]}",
                                confidence=0.95
                            ))

                            messages.append({
                                "role": "tool",
                                "name": func_name,
                                "content": cleaned_out,
                            })

                        # Follow-up synthesis call
                        next_resp = self.llm_client.chat(messages=messages, tools=ollama_tools)
                        if isinstance(next_resp, dict):
                            msg = next_resp
                        else:
                            break

                    reply_content = msg.get("content")
                    if isinstance(reply_content, str):
                        reply = reply_content.strip()

            if not reply or not isinstance(reply, str):
                gen_reply = self.llm_client.generate(prompt)
                reply = str(gen_reply) if gen_reply is not None else ""

            if not reply:
                reply = (
                    "The local model returned an empty response. "
                    "Check that the configured Ollama model is pulled and running."
                )
        except LLMUnavailableError as exc:
            reply = f"I couldn't reach the local model: {exc}"

        # 4. Construct Evidence References (OpenMemory + SQLite notes + Tool Executions)
        for item in openmemory_items:
            evidence.append(Evidence(
                source_uuid=item.id,
                target_uuid=item.id,
                relationship_path=["openmemory"] + item.categories,
                reason=f"OpenMemory semantic recall ({item.app_name}): {item.content[:80]}",
                confidence=0.90
            ))

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


