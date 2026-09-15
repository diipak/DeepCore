import json
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from deepcore.storage.sqlite.models import (
    ThinkingSession as DBThinkingSession,
    Conversation as DBConversation,
    Message as DBMessage,
    RegistryObject as DBRegistryObject,
    Workspace as DBWorkspace
)
from deepcore.core.assistant.service import ConversationService, ConversationRepository
from deepcore.core.assistant.schema import BUILTIN_THINKING_MODES

def test_conversation_repository_creation(db_session: Session):
    """Verify repository decoupled CRUD details (Amendment 4)."""
    # Ensure workspace exists
    ws = db_session.query(DBWorkspace).filter(DBWorkspace.id == 1).first()
    if not ws:
        ws = DBWorkspace(id=1, name="Workspace 1")
        db_session.add(ws)
        db_session.commit()

    repo = ConversationRepository(db_session, workspace_id=1)
    
    # 1. Create Thinking Session
    session = repo.create_session("Exploring Quantum", "CONTINUE_THINKING")
    assert session.id is not None
    assert session.title == "Exploring Quantum"
    assert session.active_thinking_mode == "CONTINUE_THINKING"

    # 2. Create Conversation
    conversation = repo.create_conversation(session.id)
    assert conversation.id is not None
    assert conversation.thinking_session_id == session.id

    # 3. Add message
    msg = repo.add_message(conversation.id, "user", "What is quantum?")
    assert msg.id is not None
    assert msg.role == "user"
    assert msg.content == "What is quantum?"

    # 4. Fetch session
    fetched_session = repo.get_session(session.uuid)
    assert fetched_session is not None
    assert fetched_session.title == "Exploring Quantum"


def test_conversation_service_flow(db_session: Session):
    """Verify service orchestrates and composes ConversationState (Amendment 1 & 2)."""
    # Ensure workspace exists
    ws = db_session.query(DBWorkspace).filter(DBWorkspace.id == 1).first()
    if not ws:
        ws = DBWorkspace(id=1, name="Workspace 1")
        db_session.add(ws)
        db_session.commit()

    stub_llm = StubLLMClient(response="Stubbed response for flow test.")
    service = ConversationService(db_session, workspace_id=1, llm_client=stub_llm)
    
    # 1. Start thinking session
    state = service.start_session("EXPLORE_RELATIONSHIPS")
    assert state.title == "Reflective Thought Session"
    assert state.active_thinking_mode == "EXPLORE_RELATIONSHIPS"
    
    # Greet message should be added automatically
    assert len(state.messages) == 1
    assert state.messages[0].role == "assistant"
    assert "Ready to map relationships" in state.messages[0].content

    # Register a note in workspace 1 matching quantum
    from deepcore.core.registry.service import RegistryService
    from deepcore.core.objects.schemas import RegistryObjectCreate, ObjectType
    reg_service = RegistryService(db_session, workspace_id=1)
    note_obj = reg_service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Quantum Compute Note",
        description="Tell me about quantum compute.",
        source_system="markdown",
        location="/tmp/quantum_note.md",
        status="active"
    ))


    # 2. Post user message referencing quantum
    updated_state = service.post_message(state.session_uuid, "Tell me about quantum compute.")
    assert len(updated_state.messages) == 3 # Greet, User query, Assistant reply
    assert updated_state.messages[1].role == "user"
    assert updated_state.messages[2].role == "assistant"
    
    # Check that evidence was generated from real retrieved note
    assistant_msg = updated_state.messages[2]
    assert assistant_msg.evidence is not None
    assert len(assistant_msg.evidence) == 1
    assert assistant_msg.evidence[0].source_uuid == note_obj.uuid
    assert assistant_msg.evidence[0].target_uuid == note_obj.uuid
    assert "Quantum Compute Note" in assistant_msg.evidence[0].reason
    assert assistant_msg.evidence[0].confidence == 0.95



from deepcore.intelligence.llm_client import OllamaClient, LLMUnavailableError


class StubLLMClient:
    """Deterministic stand-in for OllamaClient in tests."""

    def __init__(self, response: str = "Grounded stubbed answer.", raise_unavailable: bool = False):
        self.response = response
        self.raise_unavailable = raise_unavailable
        self.last_prompt = None

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        if self.raise_unavailable:
            raise LLMUnavailableError("Ollama is not reachable in tests.")
        return self.response


def test_conversation_service_grounded_llm_reply(db_session: Session):
    """Verify ConversationService uses StubLLMClient and grounds answers in prompt."""
    ws = db_session.query(DBWorkspace).filter(DBWorkspace.id == 1).first()
    if not ws:
        db_session.add(DBWorkspace(id=1, name="Workspace 1"))
        db_session.commit()

    stub_llm = StubLLMClient(response="Answer grounded in notes.")
    service = ConversationService(db_session, workspace_id=1, llm_client=stub_llm)

    state = service.start_session("CONTINUE_THINKING")
    updated_state = service.post_message(state.session_uuid, "Explain deepcore concepts")

    assert len(updated_state.messages) == 3
    assert updated_state.messages[2].role == "assistant"
    assert updated_state.messages[2].content == "Answer grounded in notes."
    assert stub_llm.last_prompt is not None
    assert "Explain deepcore concepts" in stub_llm.last_prompt
    assert "ONLY the context below" in stub_llm.last_prompt


def test_conversation_service_multi_turn_history_in_prompt(db_session: Session):
    """Verify prior conversation history is included in the LLM prompt."""
    ws = db_session.query(DBWorkspace).filter(DBWorkspace.id == 1).first()
    if not ws:
        db_session.add(DBWorkspace(id=1, name="Workspace 1"))
        db_session.commit()

    stub_llm = StubLLMClient(response="Follow-up answer.")
    service = ConversationService(db_session, workspace_id=1, llm_client=stub_llm)

    state = service.start_session("CONTINUE_THINKING")
    service.post_message(state.session_uuid, "First question about architecture")
    service.post_message(state.session_uuid, "Second follow-up query")

    assert stub_llm.last_prompt is not None
    assert "First question about architecture" in stub_llm.last_prompt
    assert "Second follow-up query" in stub_llm.last_prompt


def test_conversation_service_llm_unavailable_handling(db_session: Session):
    """Verify LLMUnavailableError produces clean failure message without crashing."""
    ws = db_session.query(DBWorkspace).filter(DBWorkspace.id == 1).first()
    if not ws:
        db_session.add(DBWorkspace(id=1, name="Workspace 1"))
        db_session.commit()

    failing_llm = StubLLMClient(raise_unavailable=True)
    service = ConversationService(db_session, workspace_id=1, llm_client=failing_llm)

    state = service.start_session("CONTINUE_THINKING")
    updated_state = service.post_message(state.session_uuid, "Query when model is down")

    assert len(updated_state.messages) == 3
    assert updated_state.messages[2].role == "assistant"
    assert "couldn't reach the local model" in updated_state.messages[2].content


def test_assistant_api_endpoints(client: TestClient, db_session: Session, monkeypatch):
    """Verify client endpoints map thinking sessions correctly (Amendment 3)."""
    monkeypatch.setattr(OllamaClient, "generate", lambda self, prompt: "Verified response.")

    # 1. Get thinking modes
    res_modes = client.get("/api/conversations/modes")
    assert res_modes.status_code == 200
    modes = res_modes.json()
    assert len(modes) == len(BUILTIN_THINKING_MODES)
    assert modes[0]["id"] == "CONTINUE_THINKING"

    # 2. Start Thinking Session
    res_start = client.post("/api/conversations/start", json={
        "thinking_mode": "CHALLENGE_ASSUMPTIONS"
    })
    assert res_start.status_code == 200
    session_data = res_start.json()
    assert "session_uuid" in session_data
    assert session_data["active_thinking_mode"] == "CHALLENGE_ASSUMPTIONS"
    session_uuid = session_data["session_uuid"]

    # 3. Post Message
    res_msg = client.post(f"/api/conversations/{session_uuid}/messages", json={
        "content": "Verify my assumptions"
    })
    assert res_msg.status_code == 200
    updated_data = res_msg.json()
    assert len(updated_data["messages"]) == 3 # Greet, user, assistant

    # 4. Restore Session
    res_restore = client.get(f"/api/conversations/{session_uuid}")
    assert res_restore.status_code == 200
    restored_data = res_restore.json()
    assert restored_data["title"] == "Reflective Thought Session"
    assert len(restored_data["messages"]) == 3


def test_conversation_service_workspace_scoping(db_session: Session):
    """Verify ContextEngine/RegistryService constructed via ConversationService is scoped to specified workspace_id."""
    from deepcore.core.registry.service import RegistryService
    from deepcore.core.objects.schemas import RegistryObjectCreate, ObjectType

    # Create workspace 99 and workspace 100
    ws99 = DBWorkspace(id=99, name="Workspace 99")
    ws100 = DBWorkspace(id=100, name="Workspace 100")
    db_session.add_all([ws99, ws100])
    db_session.commit()

    # Add a note to workspace 99
    reg99 = RegistryService(db_session, workspace_id=99)
    note99 = reg99.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Secret Project Alpha Note",
        description="Tell me about Secret Project",
        source_system="markdown",
        location="/tmp/alpha.md",
        status="active"
    ))

    # Add a note to workspace 100
    reg100 = RegistryService(db_session, workspace_id=100)
    note100 = reg100.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Secret Project Beta Note",
        description="Tell me about Secret Project",
        source_system="markdown",
        location="/tmp/beta.md",
        status="active"
    ))


    # Construct ConversationService scoped to workspace 99
    stub_llm = StubLLMClient(response="Workspace 99 reply.")
    service99 = ConversationService(db_session, workspace_id=99, llm_client=stub_llm)

    state = service99.start_session("CONTINUE_THINKING")
    updated_state = service99.post_message(state.session_uuid, "Tell me about Secret Project")

    # Evidence in workspace 99 should ONLY contain note99, not note100
    assistant_msg = updated_state.messages[2]
    assert assistant_msg.evidence is not None
    evidence_uuids = [e.source_uuid for e in assistant_msg.evidence]
    assert note99.uuid in evidence_uuids
    assert note100.uuid not in evidence_uuids



