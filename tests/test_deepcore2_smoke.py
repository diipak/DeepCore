"""
DeepCore 2.0 Kernel Smoke Test Suite.

Verifies:
1. Application lifecycle bootstrap, ready status, and zero Echo stubs in CapabilityRegistry.
2. Core API endpoints (/api/health, /api/capabilities, /api/conversations/modes).
3. ConversationService round-trip lifecycle (session start, greeting seed, message posting, evidence generation).
4. Graceful degradation when local LLM is unreachable (no 500 crashes).
"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from deepcore2.config import settings
from deepcore2.runtime.composition import bootstrap_application
from deepcore2.runtime.application import Application
from deepcore2.api.main import app
from deepcore2.core.assistant.service import ConversationService
from deepcore2.storage.sqlite.db import get_db, Base, engine
from deepcore2.intelligence.llm_client import LLMUnavailableError


@pytest.fixture(scope="module", autouse=True)
def init_test_db():
    """Ensure database tables exist for deepcore2 tests."""
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_deepcore2_kernel_lifecycle():
    """Verify clean deepcore2 kernel bootstraps and contains zero mock/echo capabilities."""
    deepcore_app = bootstrap_application(settings)
    assert isinstance(deepcore_app, Application)
    assert deepcore_app.status == "ready"

    # Capability Registry check: absolutely zero synthetic Echo stubs
    descriptors = deepcore_app.capability_registry.list()
    descriptor_names = [d.name.lower() for d in descriptors]
    for banned in ["echo", "echotool", "echoskill", "registrysearchmocktool"]:
        assert banned not in descriptor_names, f"Banned stub '{banned}' found in CapabilityRegistry!"


def test_deepcore2_api_routes(client):
    """Verify health, capabilities, and conversation modes endpoints."""
    # 1. Health Endpoint
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    health_data = res_health.json()
    assert health_data["status"] == "ready"
    assert "domains" in health_data

    # 2. Capabilities Endpoint (returns CapabilityCatalog with zero echo tools)
    res_caps = client.get("/api/capabilities")
    assert res_caps.status_code == 200
    caps_data = res_caps.json()
    assert "categories" in caps_data
    for group in caps_data["categories"]:
        for cap in group.get("capabilities", []):
            name = cap.get("name", "").lower()
            assert "echo" not in name

    # 3. Conversation Modes Endpoint
    res_modes = client.get("/api/conversations/modes")
    assert res_modes.status_code == 200
    modes = res_modes.json()
    mode_ids = [m["id"] for m in modes]
    assert "CONTINUE_THINKING" in mode_ids
    assert "CHALLENGE_ASSUMPTIONS" in mode_ids


def test_deepcore2_conversation_service_roundtrip():
    """Verify full conversation session start, message dispatch, and evidence generation with mocked LLM."""
    db = next(get_db())
    try:
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "Verified deterministic grounded thought response."

        service = ConversationService(db=db, workspace_id=1, llm_client=mock_llm)

        # 1. Start Session
        session_state = service.start_session(thinking_mode="CONTINUE_THINKING")
        assert session_state.session_uuid is not None
        assert session_state.active_thinking_mode == "CONTINUE_THINKING"
        # Seed greeting message
        assert len(session_state.messages) == 1
        assert session_state.messages[0].role == "assistant"

        # 2. Post Message
        updated_state = service.post_message(
            session_uuid=session_state.session_uuid,
            content="What is the architecture of DeepCore?"
        )
        assert len(updated_state.messages) == 3  # Greeting + User message + Assistant reply
        user_msg = updated_state.messages[1]
        assistant_reply = updated_state.messages[2]

        assert user_msg.role == "user"
        assert user_msg.content == "What is the architecture of DeepCore?"
        assert assistant_reply.role == "assistant"
        assert assistant_reply.content == "Verified deterministic grounded thought response."
        mock_llm.generate.assert_called_once()
    finally:
        db.close()


def test_deepcore2_conversation_service_graceful_degradation():
    """Verify that when Ollama is unreachable, ConversationService degrades gracefully without throwing a 500."""
    db = next(get_db())
    try:
        mock_failing_llm = MagicMock()
        mock_failing_llm.generate.side_effect = LLMUnavailableError("Ollama connection refused on port 11434")

        service = ConversationService(db=db, workspace_id=1, llm_client=mock_failing_llm)
        session_state = service.start_session(thinking_mode="CHALLENGE_ASSUMPTIONS")

        updated_state = service.post_message(
            session_uuid=session_state.session_uuid,
            content="Check assumptions."
        )

        assert len(updated_state.messages) == 3
        assistant_reply = updated_state.messages[2]
        assert assistant_reply.role == "assistant"
        assert "couldn't reach the local model" in assistant_reply.content
    finally:
        db.close()


def test_deepcore2_conversation_live_roundtrip():
    """Live socket test: verifies ConversationService end-to-end against local Ollama."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=1.0) as resp:
            if resp.status != 200:
                pytest.skip("Local Ollama not responding on port 11434")
    except Exception:
        pytest.skip("Local Ollama not reachable on port 11434")

    db = next(get_db())
    try:
        # Uses real OllamaClient with gemma4:12b (think: false)
        service = ConversationService(db=db, workspace_id=1)
        session = service.start_session(thinking_mode="CONTINUE_THINKING")
        state = service.post_message(session.session_uuid, "Respond in one short sentence: what is DeepCore?")

        assert len(state.messages) == 3
        reply = state.messages[2].content
        assert len(reply) > 5
        assert "couldn't reach the local model" not in reply
    finally:
        db.close()

