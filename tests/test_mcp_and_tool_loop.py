import sys
import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel

from deepcore2.core.security import redact_secrets
from deepcore2.runtime.tools.base import ToolRequest, ToolStatus
from deepcore2.runtime.tools.registry import ToolRegistry, ExecutionRegistry
from deepcore2.runtime.tools.runtime import ToolRuntime
from deepcore2.runtime.tools.mcp_client import (
    StdioMCPClient,
    MCPToolAdapter,
    _build_pydantic_schema_from_mcp,
    MCPError,
)
from deepcore2.intelligence.llm_client import OllamaClient
from deepcore2.core.assistant.service import ConversationService


def test_redact_secrets_masks_keys_and_tokens():
    """Verify redact_secrets masks API keys, tokens, and configured secrets."""
    sample_text = (
        "Server response failed with api_key: 'BSAx8372019482018471928' "
        "and Authorization: Bearer abcdef123456789012345678. "
        "Also sk-proj12345678901234567890."
    )
    redacted = redact_secrets(sample_text)

    assert "BSAx8372019482018471928" not in redacted
    assert "abcdef123456789012345678" not in redacted
    assert "sk-proj12345678901234567890" not in redacted
    assert "[REDACTED" in redacted


def test_build_pydantic_schema_from_mcp_creates_valid_basemodel():
    """Verify dynamic Pydantic class generation creates a real Type[BaseModel]."""
    mcp_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "count": {"type": "integer", "description": "Number of results", "default": 5},
            "fresh": {"type": "boolean", "description": "Filter freshness"}
        },
        "required": ["query"]
    }

    schema_class = _build_pydantic_schema_from_mcp("brave_web_search", mcp_schema)

    assert issubclass(schema_class, BaseModel)
    json_schema = schema_class.model_json_schema()

    assert "query" in json_schema["properties"]
    assert "count" in json_schema["properties"]
    assert "fresh" in json_schema["properties"]
    assert "query" in json_schema["required"]


def test_mcp_tool_adapter_registers_and_executes_via_tool_runtime():
    """Verify MCPToolAdapter conforms to BaseTool and executes via ToolRuntime."""
    mock_client = MagicMock(spec=StdioMCPClient)
    mock_client.call_tool.return_value = "Result: DeepCore is an intelligence operating system."

    tool_info = {
        "name": "mock_search",
        "description": "Mock search tool",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    }

    adapter = MCPToolAdapter(mcp_client=mock_client, tool_info=tool_info)
    assert issubclass(adapter.input_schema, BaseModel)
    assert adapter.name == "mock_search"
    assert adapter.safety.requires_network is True

    # Register into existing ToolRegistry
    registry = ToolRegistry()
    registry.register(adapter)
    assert len(registry.list_tools()) == 1

    # Execute via ToolRuntime
    runtime = ToolRuntime(ExecutionRegistry(registry))
    req = ToolRequest(request_id="req-1", inputs={"query": "DeepCore"})
    result = runtime.execute("mock_search", req)

    assert result.status == ToolStatus.SUCCESS
    assert "DeepCore is an intelligence operating system" in result.outputs["content"]
    mock_client.call_tool.assert_called_once_with("mock_search", {"query": "DeepCore"})


def test_conversation_service_react_tool_loop(db_session):
    """Verify ConversationService executes tool calls from LLM and synthesizes final answer."""
    # 1. Setup mock tool in registry
    mock_client = MagicMock(spec=StdioMCPClient)
    mock_client.call_tool.return_value = "Brave Search result: Apple Silicon M4 Pro has 48GB unified memory."

    adapter = MCPToolAdapter(
        mcp_client=mock_client,
        tool_info={
            "name": "brave_web_search",
            "description": "Search the web via Brave",
            "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}}
        }
    )
    tool_reg = ToolRegistry()
    tool_reg.register(adapter)
    tool_run = ToolRuntime(ExecutionRegistry(tool_reg))

    # 2. Setup mock LLM chat returns: Turn 1 returns tool_call, Turn 2 returns final text
    mock_llm = MagicMock(spec=OllamaClient)
    mock_llm.chat.side_effect = [
        # Turn 1: Model asks to call tool
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "brave_web_search",
                        "arguments": {"query": "M4 Pro unified memory"}
                    }
                }
            ]
        },
        # Turn 2: Model answers using tool observation
        {
            "role": "assistant",
            "content": "Based on web search, Apple Silicon M4 Pro features 48GB unified memory."
        }
    ]

    service = ConversationService(
        db=db_session,
        workspace_id=1,
        llm_client=mock_llm,
        tool_registry=tool_reg,
        tool_runtime=tool_run
    )

    session = service.start_session("CONTINUE_THINKING")
    state = service.post_message(session.session_uuid, "What memory does M4 Pro have?")

    # Verify tool was called
    mock_client.call_tool.assert_called_once_with("brave_web_search", {"query": "M4 Pro unified memory"})

    # Verify assistant answer
    last_msg = state.messages[-1]
    assert last_msg.role == "assistant"
    assert "features 48GB unified memory" in last_msg.content

    # Verify Evidence was captured with tool citation
    tool_ev = [ev for ev in last_msg.evidence if "tool" in ev.relationship_path]
    assert len(tool_ev) == 1
    assert tool_ev[0].source_uuid == "mcp-brave_web_search"
    assert "Live tool execution" in tool_ev[0].reason


def test_conversation_service_react_loop_bounds_to_two_iterations(db_session):
    """Verify tool loop terminates after 2 rounds even if model repeatedly requests tools."""
    mock_client = MagicMock(spec=StdioMCPClient)
    mock_client.call_tool.return_value = "Search result"

    adapter = MCPToolAdapter(
        mcp_client=mock_client,
        tool_info={
            "name": "loop_tool",
            "description": "Looping tool",
            "inputSchema": {"type": "object", "properties": {}}
        }
    )
    tool_reg = ToolRegistry()
    tool_reg.register(adapter)
    tool_run = ToolRuntime(ExecutionRegistry(tool_reg))

    # Model endlessly requests tool calls
    endless_tool_call = {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "loop_tool", "arguments": {}}}]
    }

    mock_llm = MagicMock(spec=OllamaClient)
    mock_llm.chat.return_value = endless_tool_call
    mock_llm.generate.return_value = "Fallback final text after bounded loop."

    service = ConversationService(
        db=db_session,
        workspace_id=1,
        llm_client=mock_llm,
        tool_registry=tool_reg,
        tool_runtime=tool_run
    )

    session = service.start_session("CONTINUE_THINKING")
    state = service.post_message(session.session_uuid, "Trigger endless loop")

    # Should call tool at most twice (bounded limit)
    assert mock_client.call_tool.call_count == 2
    assert state.messages[-1].content == "Fallback final text after bounded loop."


def test_stdio_mcp_client_watchdog_timeout_kills_process():
    """Verify select.select watchdog enforces timeout, closes connection, and kills hung process."""
    client = StdioMCPClient(command="mock-cmd", timeout_seconds=0.01)

    mock_process = MagicMock()
    mock_process.poll.return_value = None
    mock_process.stdin = MagicMock()
    mock_process.stdout = MagicMock()
    mock_process.stderr = MagicMock()
    client.process = mock_process

    with patch("select.select", return_value=([], [], [])):
        with pytest.raises(MCPError) as exc_info:
            client._send_request("tools/list")

        assert "timed out after" in str(exc_info.value)
        # Verify process was terminated/killed on timeout
        assert mock_process.terminate.called or mock_process.kill.called
        assert client.process is None


def test_discover_and_register_mcp_tools_with_config():
    """Verify discover_and_register_mcp_tools inspects config and mounts tools into ToolRegistry."""
    from deepcore2.runtime.tools.mcp_client import discover_and_register_mcp_tools

    mock_config = MagicMock()
    mock_config.BRAVE_API_KEY = "mock-brave-api-key"
    mock_config.BRAVE_MCP_COMMAND = "mock-brave-command"
    mock_config.MCP_TIMEOUT_SECONDS = 5.0

    mock_tools_data = [
        {
            "name": "brave_web_search",
            "description": "Brave search tool",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        }
    ]

    with patch("deepcore2.runtime.tools.mcp_client.StdioMCPClient") as mock_client_cls:
        mock_instance = MagicMock()
        mock_instance.list_tools.return_value = mock_tools_data
        mock_client_cls.return_value = mock_instance

        registry = ToolRegistry()
        registered = discover_and_register_mcp_tools(tool_registry=registry, config=mock_config)

        assert registered == ["brave_web_search"]
        assert registry.get("brave_web_search") is not None

        # Verify idempotency: calling a second time does not re-register or fail
        registered_second = discover_and_register_mcp_tools(tool_registry=registry, config=mock_config)
        assert registered_second == []


def test_application_wires_conversation_service_with_tool_registry(db_session):
    """Verify Application.get_conversation_service injects its tool_registry and tool_runtime."""
    from deepcore2.runtime.application import Application

    mock_tool_reg = ToolRegistry()
    mock_tool_run = ToolRuntime(ExecutionRegistry(mock_tool_reg))

    app = Application(
        config=MagicMock(),
        capability_registry=MagicMock(),
        discovery_service=MagicMock(),
        tool_registry=mock_tool_reg,
        skill_registry=MagicMock(),
        execution_registry=MagicMock(),
        tool_runtime=mock_tool_run,
        skill_runtime=MagicMock(),
        execution_runtime=MagicMock(),
        planner_runtime=MagicMock(),
        ingestion_runtime=MagicMock(),
        processing_runtime=MagicMock(),
    )

    conv_service = app.get_conversation_service(db_session)
    assert conv_service.tool_registry is mock_tool_reg
    assert conv_service.tool_runtime is mock_tool_run


def test_real_subprocess_mcp_client_roundtrip_and_discovery():
    """
    Live subprocess integration test: Spawns a real Python child process
    implementing MCP JSON-RPC 2.0 over real OS pipes (no MagicMock on StdioMCPClient).
    Verifies ensure_running(), initialize handshake, list_tools(), dynamic adapter,
    and call_tool() end-to-end.
    """
    import sys
    import textwrap
    from deepcore2.runtime.tools.mcp_client import discover_and_register_mcp_tools

    server_code = (
        "import sys, json\n"
        "while True:\n"
        "    line = sys.stdin.readline()\n"
        "    if not line:\n"
        "        break\n"
        "    req = json.loads(line)\n"
        "    m = req.get('method')\n"
        "    rid = req.get('id')\n"
        "    if m == 'initialize':\n"
        "        resp = {'jsonrpc': '2.0', 'id': rid, 'result': {'protocolVersion': '2024-11-05', 'capabilities': {}, 'serverInfo': {'name': 'stub', 'version': '1.0'}}}\n"
        "        sys.stdout.write(json.dumps(resp) + '\\n')\n"
        "        sys.stdout.flush()\n"
        "    elif m == 'notifications/initialized':\n"
        "        pass\n"
        "    elif m == 'tools/list':\n"
        "        resp = {'jsonrpc': '2.0', 'id': rid, 'result': {'tools': [{'name': 'brave_web_search', 'description': 'Search web', 'inputSchema': {'type': 'object', 'properties': {'query': {'type': 'string'}}, 'required': ['query']}}]}}\n"
        "        sys.stdout.write(json.dumps(resp) + '\\n')\n"
        "        sys.stdout.flush()\n"
        "    elif m == 'tools/call':\n"
        "        q = req.get('params', {}).get('arguments', {}).get('query', '')\n"
        "        resp = {'jsonrpc': '2.0', 'id': rid, 'result': {'content': [{'type': 'text', 'text': f'Results for: {q}. Found 42 items.'}]}}\n"
        "        sys.stdout.write(json.dumps(resp) + '\\n')\n"
        "        sys.stdout.flush()\n"
    )

    cmd = [sys.executable, "-c", server_code]

    # 1. Test StdioMCPClient directly against real subprocess
    client = StdioMCPClient(command=cmd, timeout_seconds=5.0)
    assert client.process is None  # initially not started

    # list_tools() should auto-start the subprocess and complete handshake
    tools = client.list_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "brave_web_search"
    assert client.process is not None
    assert client.process.poll() is None

    # call_tool() should execute against real subprocess
    result_text = client.call_tool("brave_web_search", {"query": "Apple Silicon M4"})
    assert "Results for: Apple Silicon M4" in result_text

    client.close()
    assert client.process is None

    # 2. Test discover_and_register_mcp_tools end-to-end against real subprocess
    mock_config = MagicMock()
    mock_config.BRAVE_API_KEY = "real-test-token"
    mock_config.BRAVE_MCP_COMMAND = cmd
    mock_config.MCP_TIMEOUT_SECONDS = 5.0

    registry = ToolRegistry()
    registered = discover_and_register_mcp_tools(tool_registry=registry, config=mock_config)

    assert registered == ["brave_web_search"]
    tool_adapter = registry.get("brave_web_search")
    assert tool_adapter is not None
    assert tool_adapter.name == "brave_web_search"

    # Execute through real ToolRuntime
    runtime = ToolRuntime(ExecutionRegistry(registry))
    req = ToolRequest(request_id="req-live-1", inputs={"query": "DeepCore Architecture"})
    exec_result = runtime.execute("brave_web_search", req)
    assert exec_result.status.value == "success"
    assert "Results for: DeepCore Architecture" in exec_result.outputs["content"]

    # Clean up child process
    tool_adapter.mcp_client.close()


def test_duckduckgo_mcp_server_stdio_roundtrip():
    """Verify ddg_server.py stdio MCP server executes initialize, tools/list, and call_tool."""
    import sys
    from deepcore2.runtime.tools.mcp_client import StdioMCPClient

    cmd = [sys.executable, "-m", "deepcore2.runtime.tools.mcp_servers.ddg_server"]
    client = StdioMCPClient(command=cmd, timeout_seconds=15.0)

    try:
        tools = client.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "duckduckgo_web_search"
        assert "query" in tools[0]["inputSchema"]["properties"]

        # Call tool with query
        result = client.call_tool("duckduckgo_web_search", {"query": "Python Programming", "max_results": 2})
        assert isinstance(result, str)
        assert len(result) > 0
    finally:
        client.close()


def test_multi_server_mcp_discovery_safety_classification():
    """Verify discover_and_register_mcp_tools registers tools and classifies safety correctly."""
    from deepcore2.runtime.tools.mcp_client import discover_and_register_mcp_tools
    from deepcore2.runtime.tools.registry import ToolRegistry

    mock_config = MagicMock()
    mock_config.MCP_DUCKDUCKGO_ENABLED = True
    mock_config.MCP_DUCKDUCKGO_COMMAND = f"{sys.executable} -m deepcore2.runtime.tools.mcp_servers.ddg_server"
    mock_config.MCP_FILESYSTEM_ENABLED = False
    mock_config.BRAVE_API_KEY = ""
    mock_config.MCP_TIMEOUT_SECONDS = 5.0

    reg = ToolRegistry()
    registered = discover_and_register_mcp_tools(reg, config=mock_config)

    assert "duckduckgo_web_search" in registered
    tool = reg.get("duckduckgo_web_search")
    assert tool is not None
    assert tool.safety.safe is True
    assert tool.safety.destructive is False



