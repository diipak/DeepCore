import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch
import httpx

from deepcore2.intelligence.openmemory_client import (
    OpenMemoryClient,
    OpenMemoryUnavailableError,
    OpenMemoryItem,
)
from deepcore2.intelligence.vault_service import (
    VaultService,
    VaultSecurityError,
)
from deepcore2.core.assistant.service import ConversationService


def test_openmemory_create_memory_enforces_deepcore_namespace():
    """Verify create_memory prepends [DeepCore/Category] tag if not already provided."""
    client = OpenMemoryClient(host="http://mock-memory:8765", user_id="test_user")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "mem-12345", "status": "success"}

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        item = client.create_memory("Configured activepieces tunnel on port 443", categories=["Infrastructure"])

        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]

        assert payload["user_id"] == "test_user"
        # Must enforce [DeepCore/Infrastructure] prefix
        assert payload["text"].startswith("[DeepCore/Infrastructure]")
        assert "Configured activepieces tunnel" in payload["text"]
        assert payload["metadata"]["app"] == "DeepCore"

        assert item.id == "mem-12345"
        assert item.content.startswith("[DeepCore/Infrastructure]")
        assert item.namespace == "DeepCore/Infrastructure"


def test_openmemory_create_memory_preserves_existing_deepcore_namespace():
    """Verify create_memory does not duplicate prefix if text already has [DeepCore/...] prefix."""
    client = OpenMemoryClient(host="http://mock-memory:8765", user_id="test_user")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "mem-existing"}

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        item = client.create_memory("[DeepCore/CustomTag] Explicitly tagged memory note")
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]

        # No double tagging
        assert payload["text"] == "[DeepCore/CustomTag] Explicitly tagged memory note"
        assert not payload["text"].startswith("[DeepCore/General] [DeepCore/CustomTag]")


def test_openmemory_create_memory_handles_unavailable_gracefully():
    """Verify network connection failures raise OpenMemoryUnavailableError."""
    client = OpenMemoryClient(host="http://mock-memory:8765", user_id="test_user")

    with patch("httpx.post", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(OpenMemoryUnavailableError) as exc_info:
            client.create_memory("Test memory")
        assert "Could not reach OpenMemory" in str(exc_info.value)


def test_vault_service_path_jail_write_rules():
    """Verify VaultService strictly permits writes to AI/ and rejects writes outside."""
    with tempfile.TemporaryDirectory() as temp_dir:
        vault_root = os.path.join(temp_dir, "Notes")
        ai_root = os.path.join(vault_root, "AI")
        dev_root = os.path.join(vault_root, "Dev")
        os.makedirs(ai_root, exist_ok=True)
        os.makedirs(dev_root, exist_ok=True)

        service = VaultService(vault_root=vault_root, ai_root=ai_root)

        # 1. Valid write inside AI/
        created_file = service.write_ai_note("Drafts/new_note.md", "# Valid AI Draft")
        assert os.path.exists(created_file)
        assert os.path.realpath(created_file).startswith(os.path.realpath(ai_root))
        with open(created_file, "r") as f:
            assert f.read() == "# Valid AI Draft"

        # 2. Write targeting Dev/ -> MUST FAIL
        with pytest.raises(VaultSecurityError):
            service.write_ai_note("../Dev/exploit.md", "# Malicious code in Dev")

        # 3. Write targeting Vault root -> MUST FAIL
        with pytest.raises(VaultSecurityError):
            service.write_ai_note("../root_note.md", "# Root overwrite")

        # 4. Write targeting parent of vault -> MUST FAIL
        with pytest.raises(VaultSecurityError):
            service.write_ai_note("../../../etc/passwd", "exploit")


def test_vault_service_symlink_escape_protection():
    """Verify symlink escapes targeting outside AI/ are caught by realpath resolution."""
    with tempfile.TemporaryDirectory() as temp_dir:
        vault_root = os.path.join(temp_dir, "Notes")
        ai_root = os.path.join(vault_root, "AI")
        outside_target = os.path.join(temp_dir, "OutsideSecret")
        os.makedirs(ai_root, exist_ok=True)
        os.makedirs(outside_target, exist_ok=True)

        # Create a symlink inside AI pointing outside
        symlink_path = os.path.join(ai_root, "escape_link")
        os.symlink(outside_target, symlink_path)

        service = VaultService(vault_root=vault_root, ai_root=ai_root)

        # Attempting to write through the symlink must trigger VaultSecurityError
        with pytest.raises(VaultSecurityError):
            service.write_ai_note("escape_link/pwned.md", "malicious write")


def test_vault_service_append_daily_log_atomic():
    """Verify append_daily_log creates and safely appends entries under AI/Daily."""
    with tempfile.TemporaryDirectory() as temp_dir:
        vault_root = os.path.join(temp_dir, "Notes")
        ai_root = os.path.join(vault_root, "AI")
        service = VaultService(vault_root=vault_root, ai_root=ai_root)

        log_path = service.append_daily_log(
            entry_text="- Milestone 1 reached.\n- Decision logged.",
            title="Session Milestone Test",
            date_str="2026-09-13"
        )

        assert os.path.exists(log_path)
        with open(log_path, "r") as f:
            content = f.read()

        assert "2026-09-13" in content
        assert "Session Milestone Test" in content
        assert "Milestone 1 reached." in content

        # Append a second block
        service.append_daily_log(
            entry_text="- Follow up task finished.",
            title="Second Milestone",
            date_str="2026-09-13"
        )

        with open(log_path, "r") as f:
            updated_content = f.read()

        assert "Milestone 1 reached." in updated_content
        assert "Second Milestone" in updated_content
        assert "Follow up task finished." in updated_content


def test_conversation_service_remember_and_log_daily(db_session):
    """Verify ConversationService exposes remember and log_daily_summary methods."""
    mock_om = MagicMock(spec=OpenMemoryClient)
    mock_om.create_memory.return_value = OpenMemoryItem(
        id="om-test-id",
        content="[DeepCore/Preferences] User prefers concise bullet points",
        app_name="DeepCore",
        categories=["Preferences"]
    )

    mock_vault = MagicMock(spec=VaultService)
    mock_vault.append_daily_log.return_value = "/path/to/AI/Daily/2026-09-13.md"

    conv_service = ConversationService(
        db=db_session,
        workspace_id=1,
        openmemory_client=mock_om,
        vault_service=mock_vault
    )

    item = conv_service.remember("User prefers concise bullet points", categories=["Preferences"])
    assert item.id == "om-test-id"
    mock_om.create_memory.assert_called_once_with(
        text="User prefers concise bullet points",
        categories=["Preferences"]
    )

    result_path = conv_service.log_daily_summary("- Accomplished Phase 4.2 Step A", title="Session Harvest")
    assert result_path == "/path/to/AI/Daily/2026-09-13.md"
    mock_vault.append_daily_log.assert_called_once_with("- Accomplished Phase 4.2 Step A", title="Session Harvest")
