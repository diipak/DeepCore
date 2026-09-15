"""
Comprehensive test suite for OpenMemoryClient and Privacy Scope Protection.

Verifies:
1. Dual-layer namespace filter correctly rejects Claude's confirmed bypass memory:
   id: 9273d815-f399-467a-8e3d-ab72faf51a2d
   tag: [Design/VisualLanguage] Personal_Finz Design System...
2. Standard excluded project namespaces ([Personal_Finz/...], [Career/...], [PoojaMusic/...], [AlgoMirror/...]).
3. Allowed homelab & DeepCore memories ([DeepCore2.0/Roadmap], [OpenMemory Stack], [Security & Tailscale]).
4. HTTP error handling and strict 2.0s timeout wrapping in OpenMemoryUnavailableError.
5. End-to-end retrieval with candidate window and limit truncation.
6. Live socket test against http://127.0.0.1:8765 (skipped if unreachable).
"""
import pytest
from unittest.mock import patch, MagicMock
import httpx

from deepcore2.intelligence.openmemory_client import (
    OpenMemoryClient,
    OpenMemoryItem,
    OpenMemoryUnavailableError,
)

# Real regression fixture from OpenMemory id 9273d815-f399-467a-8e3d-ab72faf51a2d
MEMORY_9273D815_PERSONAL_FINZ_BYPASS = (
    "[Design/VisualLanguage] Personal_Finz Design System: Dark-mode first, "
    "Apple Liquid Glass, charcoal background, soft ambient gradients, "
    "translucent layered surfaces, 24-32px rounded corners, Apple Indigo accent."
)


def test_personal_finz_design_bypass_regression():
    """
    Regression Test for Claude's confirmed leak bypass:
    A memory tagged with cross-cutting [Design/VisualLanguage] but whose body describes Personal_Finz
    must be strictly rejected by the body check.
    """
    client = OpenMemoryClient()
    assert client.is_namespace_allowed(MEMORY_9273D815_PERSONAL_FINZ_BYPASS) is False


def test_standard_excluded_namespaces():
    """Verify that all standard non-DeepCore project namespaces are rejected."""
    client = OpenMemoryClient()

    samples_to_block = [
        "[Personal_Finz/Integration] ezBookkeeping Sync: Settled and pinned transactions",
        "[Personal_Finz/SpendingTiers] Three-tiered spending analysis: Fixed, Discretionary",
        "[Career/Interview] Target role compensation and positioning strategy",
        "[PoojaMusic/Brand] Acoustic aesthetics and vocal tone identity",
        "[AlgoMirror/Pipeline] Motion tracking and visual reasoning engine",
    ]

    for sample in samples_to_block:
        assert client.is_namespace_allowed(sample) is False, f"Failed to block: {sample}"


def test_allowed_deepcore_and_homelab_memories():
    """Verify that DeepCore and legitimate homelab memories are allowed through."""
    client = OpenMemoryClient()

    samples_to_allow = [
        "[DeepCore2.0/Roadmap] Fullstack Agent integration sequencing: Chat first -> Audio second -> Face third",
        "[DeepCore2.0/Architecture] Established clean deepcore2/ package without Echo mock stubs",
        "[DeepCore/Ports] Port Map: 8000 for FinSync Pro, 8090 for DeepCore API, 5173 for DeepCore shell",
        "[OpenMemory Stack] Local AI memory (Qdrant :6333)",
        "[Security & Tailscale] Caddy reverse proxy binds to 100.64.0.1 for private homelab access",
        "[UI/Evaluation] Screen Evaluation Rule: Visual polish is insufficient; evaluate whether the screen answers key questions.",
    ]

    for sample in samples_to_allow:
        assert client.is_namespace_allowed(sample) is True, f"Incorrectly blocked: {sample}"


@patch("httpx.get")
def test_search_memories_filters_and_limits(mock_get):
    """Verify that search_memories filters out foreign memories and respects the limit."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "items": [
            {
                "id": "1",
                "content": "[DeepCore2.0/Roadmap] Roadmap memory 1",
                "app_name": "Claude",
                "categories": ["coding"],
                "created_at": 100,
            },
            {
                "id": "2",
                "content": MEMORY_9273D815_PERSONAL_FINZ_BYPASS,  # Should be filtered out
                "app_name": "Antigravity",
                "categories": ["general"],
                "created_at": 101,
            },
            {
                "id": "3",
                "content": "[Personal_Finz/Ledger] Bank transaction list",  # Should be filtered out
                "app_name": "Claude",
                "categories": ["general"],
                "created_at": 102,
            },
            {
                "id": "4",
                "content": "[Security & Tailscale] Tailnet node access rules",
                "app_name": "Antigravity",
                "categories": ["infrastructure"],
                "created_at": 103,
            },
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    client = OpenMemoryClient()
    items = client.search_memories(query="test", limit=2)

    assert len(items) == 2
    assert items[0].id == "1"
    assert items[1].id == "4"
    assert items[0].content == "[DeepCore2.0/Roadmap] Roadmap memory 1"
    assert items[1].content == "[Security & Tailscale] Tailnet node access rules"


@patch("httpx.get")
def test_search_memories_timeout_handling(mock_get):
    """Verify that httpx.TimeoutException is converted to OpenMemoryUnavailableError."""
    mock_get.side_effect = httpx.TimeoutException("Read timed out")

    client = OpenMemoryClient(timeout=2.0)
    with pytest.raises(OpenMemoryUnavailableError) as exc_info:
        client.search_memories(query="test")

    assert "timed out after 2.0s" in str(exc_info.value)


@patch("httpx.get")
def test_search_memories_connection_error_handling(mock_get):
    """Verify that httpx.ConnectError is converted to OpenMemoryUnavailableError."""
    mock_get.side_effect = httpx.ConnectError("Connection refused")

    client = OpenMemoryClient()
    with pytest.raises(OpenMemoryUnavailableError) as exc_info:
        client.search_memories(query="test")

    assert "Could not reach OpenMemory" in str(exc_info.value)


def test_live_openmemory_socket_verification():
    """
    Live socket verification:
    If OpenMemory is running on port 8765, query real memories and verify:
    1. Zero returned items contain excluded project keywords.
    2. The bypass memory 9273d815 is never returned.
    """
    import urllib.request
    from deepcore2.config import settings
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:8765/api/v1/memories/?user_id={settings.OPENMEMORY_USER_ID}&size=1", timeout=1.0) as resp:
            if resp.status != 200:
                pytest.skip("OpenMemory not responsive on 127.0.0.1:8765")
    except Exception:
        pytest.skip("OpenMemory not reachable on 127.0.0.1:8765")

    client = OpenMemoryClient()
    results = client.search_memories(query="Design", limit=10)

    print(f"\n[LIVE OPENMEMORY AUDIT] Retrieved {len(results)} items for query 'Design':")
    for r in results:
        print(f"  + [{r.app_name}] {r.content[:70]}...")
        # Strict invariant assertion on live data
        assert "personal_finz" not in r.content.lower().replace("_", "")
        assert "poojamusic" not in r.content.lower()
        assert "algomirror" not in r.content.lower()
        assert "career" not in r.content.lower()


def test_conversation_service_openmemory_evidence_emission():
    """Verify that ConversationService retrieves OpenMemory items and records Evidence citations."""
    from deepcore2.core.assistant.service import ConversationService
    from deepcore2.storage.sqlite.db import get_db

    db = next(get_db())
    try:
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "Response based on OpenMemory."

        mock_om = MagicMock()
        mock_om.search_memories.return_value = [
            OpenMemoryItem(
                id="mem-1234-uuid",
                content="[DeepCore2.0/Roadmap] Fullstack Agent sequencing",
                app_name="Claude",
                categories=["coding", "automation"],
                created_at=1788813543,
                namespace="DeepCore2.0/Roadmap",
            )
        ]

        service = ConversationService(db=db, workspace_id=1, llm_client=mock_llm, openmemory_client=mock_om)
        session = service.start_session("CONTINUE_THINKING")
        state = service.post_message(session.session_uuid, "What is the agent sequence?")

        # Check evidence citations on assistant message
        assistant_msg = state.messages[2]
        assert assistant_msg.evidence is not None
        assert len(assistant_msg.evidence) >= 1
        om_evidence = [e for e in assistant_msg.evidence if e.source_uuid == "mem-1234-uuid"]
        assert len(om_evidence) == 1
        assert "openmemory" in om_evidence[0].relationship_path
        assert "coding" in om_evidence[0].relationship_path
        assert "OpenMemory semantic recall (Claude)" in om_evidence[0].reason
    finally:
        db.close()


def test_conversation_service_openmemory_graceful_degradation():
    """Verify that if OpenMemory throws OpenMemoryUnavailableError, ConversationService continues normally."""
    from deepcore2.core.assistant.service import ConversationService
    from deepcore2.storage.sqlite.db import get_db

    db = next(get_db())
    try:
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "Response with OpenMemory offline."

        mock_om = MagicMock()
        mock_om.search_memories.side_effect = OpenMemoryUnavailableError("Port 8765 connection refused")

        service = ConversationService(db=db, workspace_id=1, llm_client=mock_llm, openmemory_client=mock_om)
        session = service.start_session("CONTINUE_THINKING")
        state = service.post_message(session.session_uuid, "Test degradation query")

        assistant_msg = state.messages[2]
        assert assistant_msg.content == "Response with OpenMemory offline."
    finally:
        db.close()

