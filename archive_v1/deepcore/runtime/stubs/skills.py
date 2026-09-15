"""
deepcore.runtime.stubs.skills

Canonical stub Skill implementations:

- EchoSkill                — invokes EchoTool and returns the echoed result.
- RegistrySearchEchoSkill  — searches the registry then echoes each result title.

These are used by the Capability Discovery bootstrap and in automated tests.
They must not depend on the test package.
"""

from typing import List
from pydantic import BaseModel
from deepcore.runtime.skills.base import (
    BaseSkill,
    SkillCapability,
    SkillDiagnostics,
    SkillRequest,
    SkillResult,
    SkillStatus,
)
from deepcore.runtime.tools.base import ToolRequest, ToolStatus
from deepcore.runtime.tools.runtime import ToolRuntime


# ────────────────────────────────────────────────
# EchoSkill
# ────────────────────────────────────────────────

class EchoSkillInput(BaseModel):
    message: str

class EchoSkillOutput(BaseModel):
    result: str

class EchoSkill(BaseSkill):
    """Calls EchoTool and returns its output. Used to exercise the skill → tool execution chain."""
    name = "echo_skill"
    description = "Simple skill that echoes through EchoTool"
    input_schema = EchoSkillInput
    output_schema = EchoSkillOutput
    capabilities = [SkillCapability.FILESYSTEM]

    def __init__(self, tool_runtime: ToolRuntime):
        self.tool_runtime = tool_runtime

    def execute(self, request: SkillRequest) -> SkillResult:
        inputs_obj = self.input_schema(**request.inputs)
        tool_req = ToolRequest(
            request_id=f"{request.request_id}-tool",
            inputs={"message": inputs_obj.message}
        )
        tool_res = self.tool_runtime.execute("echo_tool", tool_req)

        if tool_res.status == ToolStatus.SUCCESS:
            return SkillResult(
                request_id=request.request_id,
                status=SkillStatus.SUCCESS,
                outputs={"result": tool_res.outputs["message"]},
                diagnostics=SkillDiagnostics(
                    execution_time_ms=0.0,
                    steps_run=["call_echo_tool"],
                    tool_calls=[{"tool": "echo_tool", "status": tool_res.status}]
                )
            )
        return SkillResult(
            request_id=request.request_id,
            status=SkillStatus.FAILURE,
            outputs={},
            diagnostics=SkillDiagnostics(
                execution_time_ms=0.0,
                steps_run=["call_echo_tool"],
                tool_calls=[{"tool": "echo_tool", "status": tool_res.status}]
            ),
            error_message=tool_res.error_message
        )


# ────────────────────────────────────────────────
# RegistrySearchEchoSkill
# ────────────────────────────────────────────────

class SearchEchoInput(BaseModel):
    query: str

class SearchEchoOutput(BaseModel):
    processed_results: List[str]

class RegistrySearchEchoSkill(BaseSkill):
    """Searches the registry via RegistrySearchMockTool, then echoes each result title."""
    name = "registry_search_echo_skill"
    description = "Searches registry and echoes result titles"
    input_schema = SearchEchoInput
    output_schema = SearchEchoOutput
    capabilities = [SkillCapability.REGISTRY, SkillCapability.FILESYSTEM]

    def __init__(self, tool_runtime: ToolRuntime):
        self.tool_runtime = tool_runtime

    def execute(self, request: SkillRequest) -> SkillResult:
        inputs_obj = self.input_schema(**request.inputs)

        search_req = ToolRequest(
            request_id=f"{request.request_id}-search",
            inputs={"query": inputs_obj.query}
        )
        search_res = self.tool_runtime.execute("registry_search_mock", search_req)

        if search_res.status != ToolStatus.SUCCESS:
            return SkillResult(
                request_id=request.request_id,
                status=SkillStatus.FAILURE,
                outputs={},
                diagnostics=SkillDiagnostics(
                    execution_time_ms=0.0,
                    steps_run=["search"],
                    tool_calls=[{"tool": "registry_search_mock", "status": search_res.status}]
                ),
                error_message=f"Search failed: {search_res.error_message}"
            )

        results = search_res.outputs.get("results", [])
        processed = []
        tool_calls = [{"tool": "registry_search_mock", "status": search_res.status}]

        for idx, item in enumerate(results):
            echo_req = ToolRequest(
                request_id=f"{request.request_id}-echo-{idx}",
                inputs={"message": f"Echo: {item['title']}"}
            )
            echo_res = self.tool_runtime.execute("echo_tool", echo_req)
            tool_calls.append({"tool": "echo_tool", "status": echo_res.status})
            if echo_res.status == ToolStatus.SUCCESS:
                processed.append(echo_res.outputs["message"])

        return SkillResult(
            request_id=request.request_id,
            status=SkillStatus.SUCCESS,
            outputs={"processed_results": processed},
            diagnostics=SkillDiagnostics(
                execution_time_ms=0.0,
                steps_run=["search", "echo_loop"],
                tool_calls=tool_calls
            )
        )
