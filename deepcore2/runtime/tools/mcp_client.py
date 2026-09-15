"""
Stdio MCP (Model Context Protocol) Client & BaseTool Adapter for DeepCore.

Implements Invariant #8:
Capabilities stay dynamically discoverable via standard MCP protocol,
never baked into application code.

Enforces:
1. Pure synchronous blocking I/O (no nested asyncio event loops inside ToolRuntime).
2. Dynamic Pydantic class generation via pydantic.create_model so BaseTool.input_schema
   strictly fulfills Type[BaseModel] requirements.
3. Secret redaction on all tool outputs before context ingestion.
4. Bounded output truncation (max 3 items, max 500 chars per item).
"""

import json
import logging
import os
import select
import shlex
import subprocess
import time
import sys
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field, create_model

logger = logging.getLogger(__name__)

from deepcore2.core.security import redact_secrets
from deepcore2.runtime.tools.base import (
    BaseTool,
    SafetyDeclaration,
    ToolCapability,
    ToolDiagnostics,
    ToolRequest,
    ToolResult,
    ToolStatus,
)


class MCPError(Exception):
    """Raised when an MCP server returns an error or protocol violation."""
    pass


class StdioMCPClient:
    """Synchronous JSON-RPC 2.0 stdio client for Model Context Protocol servers with select watchdog."""

    def __init__(
        self,
        command: str,
        env: Optional[Dict[str, str]] = None,
        timeout_seconds: float = 10.0,
    ):
        self.command = command
        self.env = {**os.environ, **(env or {})}
        self.timeout_seconds = timeout_seconds
        self.process: Optional[subprocess.Popen] = None
        self._next_id = 1

    def __enter__(self):
        self.ensure_running()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def ensure_running(self) -> None:
        """Ensure subprocess is alive and initialized; auto-starts on demand."""
        if self.process is None or self.process.poll() is not None:
            self.start()

    def start(self) -> None:
        """Spawn the subprocess and complete JSON-RPC 2.0 initialize handshake."""
        self.close()
        args = shlex.split(self.command) if isinstance(self.command, str) else self.command
        try:
            self.process = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.env,
                text=True,
                bufsize=1,
            )
        except Exception as exc:
            raise MCPError(f"Failed to spawn MCP server '{self.command}': {exc}") from exc

        # 1. Send initialize request
        init_response = self._send_request(
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "DeepCore", "version": "0.1.0"},
            },
        )
        if "error" in init_response:
            self.close()
            raise MCPError(f"MCP initialize error: {init_response['error']}")

        # 2. Send initialized notification (no reply expected)
        self._send_notification(method="notifications/initialized")

    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send JSON-RPC request and read line response with hard select watchdog timeout."""
        if not self.process or self.process.poll() is not None:
            raise MCPError("MCP process is not running.")

        req_id = self._next_id
        self._next_id += 1

        msg = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }

        try:
            raw_msg = json.dumps(msg) + "\n"
            self.process.stdin.write(raw_msg)
            self.process.stdin.flush()
        except Exception as exc:
            self.close()
            raise MCPError(f"Error writing to MCP server stdin: {exc}") from exc

        # Watchdog: Wait for stdout using select to prevent worker threads from hanging on readline()
        rlist, _, _ = select.select([self.process.stdout], [], [], self.timeout_seconds)
        if not rlist:
            self.close()
            raise MCPError(
                f"MCP server timed out after {self.timeout_seconds}s waiting for response to '{method}'."
            )

        try:
            line = self.process.stdout.readline()
            if not line:
                stderr = self.process.stderr.read() if self.process.stderr else ""
                self.close()
                raise MCPError(f"MCP server closed stream unexpectedly. Stderr: {stderr[:300]}")
            return json.loads(line)
        except json.JSONDecodeError as exc:
            self.close()
            raise MCPError(f"Malformed JSON from MCP server: {line[:200]}") from exc
        except Exception as exc:
            self.close()
            raise MCPError(f"Error reading from MCP server: {exc}") from exc

    def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send JSON-RPC notification (no ID, no response expected)."""
        if not self.process or self.process.poll() is not None:
            return

        msg = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        try:
            raw_msg = json.dumps(msg) + "\n"
            self.process.stdin.write(raw_msg)
            self.process.stdin.flush()
        except Exception:
            pass

    def list_tools(self) -> List[Dict[str, Any]]:
        """Retrieve available tool descriptors from MCP server."""
        self.ensure_running()
        response = self._send_request(method="tools/list")
        if "error" in response:
            raise MCPError(f"Error listing tools: {response['error']}")
        return response.get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute tool on MCP server, redact secrets from response,
        and apply bounded truncation (max 3 items, max 500 chars).
        """
        self.ensure_running()
        response = self._send_request(
            method="tools/call",
            params={"name": name, "arguments": arguments},
        )
        if "error" in response:
            err_msg = redact_secrets(str(response["error"]))
            raise MCPError(f"Tool execution failed: {err_msg}")

        result_data = response.get("result", {})
        content_blocks = result_data.get("content", [])

        # Extract text blocks
        raw_texts = []
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                raw_texts.append(block.get("text", ""))

        combined_text = "\n".join(raw_texts)
        redacted = redact_secrets(combined_text)

        # Enforce Bounded Truncation: max 3 search result blocks, max 500 chars each
        lines = [ln.strip() for ln in redacted.split("\n") if ln.strip()]
        if len(lines) > 3:
            truncated_blocks = [ln[:500] for ln in lines[:3]]
            return "\n\n".join(truncated_blocks) + "\n\n[Results truncated to top 3 items]"

        return redacted[:1500]

    def close(self) -> None:
        """Gracefully terminate MCP server subprocess."""
        if self.process:
            try:
                if self.process.stdin:
                    self.process.stdin.close()
                self.process.terminate()
                self.process.wait(timeout=2.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            finally:
                self.process = None


def _build_pydantic_schema_from_mcp(tool_name: str, schema_dict: Dict[str, Any]) -> Type[BaseModel]:
    """
    Convert an MCP JSON Schema dict into a real Pydantic Model Class dynamically.
    Fulfills BaseTool.input_schema: Type[BaseModel] requirement.
    """
    properties = schema_dict.get("properties", {})
    required = set(schema_dict.get("required", []))
    fields: Dict[str, Any] = {}

    for prop_name, prop_def in properties.items():
        p_type = str
        t_name = prop_def.get("type", "string")
        if t_name == "integer":
            p_type = int
        elif t_name == "boolean":
            p_type = bool
        elif t_name == "array":
            p_type = list
        elif t_name == "number":
            p_type = float

        desc = prop_def.get("description", "")
        if prop_name in required:
            fields[prop_name] = (p_type, Field(..., description=desc))
        else:
            default_val = prop_def.get("default", None)
            fields[prop_name] = (Optional[p_type], Field(default=default_val, description=desc))

    if not fields:
        fields["query"] = (Optional[str], Field(default=None, description="Input query"))

    model_name = f"{tool_name.replace('-', '_').capitalize()}Input"
    return create_model(model_name, **fields)


class MCPDefaultOutput(BaseModel):
    content: str = ""


class MCPToolAdapter(BaseTool):
    """
    Adapts an MCP tool into DeepCore's existing BaseTool interface.
    Registers seamlessly into existing ToolRegistry and executes via ToolRuntime.
    """

    def __init__(
        self,
        mcp_client: StdioMCPClient,
        tool_info: Dict[str, Any],
    ):
        self.mcp_client = mcp_client
        self.tool_info = tool_info

        self.name = tool_info["name"]
        self.id = self.name
        self.description = tool_info.get("description", f"MCP Tool: {self.name}")
        self.category = "mcp"
        self.input_schema = _build_pydantic_schema_from_mcp(self.name, tool_info.get("inputSchema", {}))
        self.output_schema = MCPDefaultOutput

        # Explicit SafetyDeclaration and ToolCapabilities based on tool semantics
        is_write = any(w in self.name.lower() for w in ("write", "edit", "create", "delete", "move"))
        is_filesystem = any(f in self.name.lower() for f in ("file", "directory", "filesystem", "path"))

        if is_filesystem:
            self.capabilities = [ToolCapability.FILESYSTEM]
            if is_write:
                self.safety = SafetyDeclaration(
                    safe=False,
                    destructive=True,
                    requires_network=False,
                    requires_confirmation=True,
                )
            else:
                self.safety = SafetyDeclaration(
                    safe=True,
                    destructive=False,
                    requires_network=False,
                    requires_confirmation=False,
                )
        else:
            self.capabilities = [ToolCapability.NETWORK]
            self.safety = SafetyDeclaration(
                safe=True,
                destructive=False,
                requires_network=True,
                requires_confirmation=False,
            )
        self.estimated_latency_ms = 100.0
        self.resource_cost = "low"
        self.examples = []

    def execute(self, request: ToolRequest) -> ToolResult:
        """Synchronous execution invoked by ToolRuntime."""
        start_time = time.time()
        try:
            call_args = dict(request.inputs or {})
            if self.name == "search_files":
                if not call_args.get("path"):
                    from deepcore2.config import settings
                    call_args["path"] = getattr(settings, "MCP_FILESYSTEM_ROOT", ".")
                pat = call_args.get("pattern", "*")
                clean_pat = pat.strip("*")
                if clean_pat and not pat.startswith("**"):
                    ci_pat = "".join(f"[{c.lower()}{c.upper()}]" if c.isalpha() else c for c in clean_pat)
                    call_args["pattern"] = f"**/*{ci_pat}*"

            output = self.mcp_client.call_tool(self.name, call_args)
            exec_time_ms = (time.time() - start_time) * 1000.0

            return ToolResult(
                request_id=request.request_id,
                status=ToolStatus.SUCCESS,
                outputs={"content": output},
                diagnostics=ToolDiagnostics(
                    execution_time_ms=exec_time_ms,
                    system_resources_used={"client": "StdioMCPClient"},
                ),
            )
        except Exception as exc:
            exec_time_ms = (time.time() - start_time) * 1000.0
            clean_err = redact_secrets(str(exc))
            return ToolResult(
                request_id=request.request_id,
                status=ToolStatus.FAILURE,
                outputs={},
                diagnostics=ToolDiagnostics(
                    execution_time_ms=exec_time_ms,
                    errors_encountered=[clean_err],
                ),
                error_message=clean_err,
            )


def discover_and_register_mcp_tools(
    tool_registry: Any,
    capability_registry: Optional[Any] = None,
    config: Optional[Any] = None,
) -> List[str]:
    """
    Discovers external tools from configured MCP servers (Invariant #8) and registers
    them into DeepCore's operational ToolRegistry (and optionally CapabilityRegistry).
    """
    if config is None:
        try:
            from deepcore2.config import settings
            config = settings
        except Exception:
            return []

    servers_to_mount: List[Dict[str, Any]] = []

    # 1. DuckDuckGo MCP (Zero API key web search)
    if getattr(config, "MCP_DUCKDUCKGO_ENABLED", True):
        ddg_cmd = getattr(config, "MCP_DUCKDUCKGO_COMMAND", None)
        if not ddg_cmd:
            ddg_cmd = f"{sys.executable} -m deepcore2.runtime.tools.mcp_servers.ddg_server"
        servers_to_mount.append({
            "name": "DuckDuckGo",
            "command": ddg_cmd,
            "env": {},
        })

    # 2. Filesystem MCP (Jailed vault exploration)
    if getattr(config, "MCP_FILESYSTEM_ENABLED", True):
        vault_root = getattr(config, "MCP_FILESYSTEM_ROOT", getattr(config, "VAULT_ROOT", "~/Documents/Notes"))
        fs_cmd = getattr(config, "MCP_FILESYSTEM_COMMAND", None)
        if not fs_cmd:
            fs_cmd = f"npx -y @modelcontextprotocol/server-filesystem {vault_root}"
        servers_to_mount.append({
            "name": "Filesystem",
            "command": fs_cmd,
            "env": {},
        })

    # 3. Brave Search MCP (External token-based search)
    brave_key = getattr(config, "BRAVE_API_KEY", "") or os.getenv("BRAVE_API_KEY", "")
    if brave_key:
        brave_cmd = getattr(config, "BRAVE_MCP_COMMAND", "npx -y @modelcontextprotocol/server-brave-search")
        servers_to_mount.append({
            "name": "Brave",
            "command": brave_cmd,
            "env": {"BRAVE_API_KEY": brave_key},
        })

    registered_names: List[str] = []
    timeout_sec = float(getattr(config, "MCP_TIMEOUT_SECONDS", 10.0))

    for srv in servers_to_mount:
        try:
            client = StdioMCPClient(
                command=srv["command"],
                env=srv.get("env"),
                timeout_seconds=timeout_sec,
            )
            client.ensure_running()
            tools = client.list_tools()
            for tool_info in tools:
                name = tool_info.get("name")
                if not name:
                    continue
                if tool_registry.get(name) is None:
                    adapter = MCPToolAdapter(mcp_client=client, tool_info=tool_info)
                    tool_registry.register(adapter)
                    if capability_registry is not None:
                        try:
                            capability_registry.register(adapter.get_descriptor())
                        except Exception as cap_err:
                            logger.debug("Capability registration skipped or already present: %s", cap_err)
                    registered_names.append(name)
        except Exception as exc:
            clean_err = redact_secrets(str(exc))
            logger.warning("Failed to auto-register %s MCP tools: %s", srv["name"], clean_err)

    return registered_names

