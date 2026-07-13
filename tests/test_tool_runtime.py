import pytest
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from deepcore.runtime.tools.base import (
    BaseTool,
    ToolStatus,
    ToolArtifact,
    ToolDiagnostics,
    ToolRequest,
    ToolResult,
    ToolCapability,
    SafetyDeclaration
)
from deepcore.runtime.tools.registry import ToolRegistry, ExecutionRegistry
from deepcore.runtime.tools.runtime import ToolRuntime
from deepcore.runtime.tools.exceptions import (
    ToolNotFoundError,
    ToolValidationError,
    ToolExecutionError,
    ToolTimeoutError
)
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObjectCreate, ObjectType
from deepcore.runtime.stubs.tools import (
    EchoTool,
    EchoInput,
    EchoOutput,
    RegistrySearchMockTool,
    RegistrySearchInput,
    RegistrySearchOutput,
)


# ==========================================
# Mock Tools for Runtime Testing
# ==========================================
# EchoTool, EchoInput, EchoOutput, RegistrySearchMockTool,
# RegistrySearchInput, RegistrySearchOutput are imported from
# deepcore.runtime.stubs.tools — the canonical single source of truth.


class DelayInput(BaseModel):
    delay_seconds: float

class DelayOutput(BaseModel):
    completed: bool

class DelayTool(BaseTool):
    name = "delay_tool"
    description = "Simulates a slow call to test timeout behavior"
    category = "OS"
    input_schema = DelayInput
    output_schema = DelayOutput
    
    def execute(self, request: ToolRequest) -> ToolResult:
        inputs_obj = self.input_schema(**request.inputs)
        time.sleep(inputs_obj.delay_seconds)
        return ToolResult(
            request_id=request.request_id,
            status=ToolStatus.SUCCESS,
            outputs={"completed": True},
            diagnostics=ToolDiagnostics(execution_time_ms=inputs_obj.delay_seconds * 1000.0)
        )


class CalculatorInput(BaseModel):
    a: float
    b: float
    operation: str = Field(description="One of: add, subtract, multiply, divide")

class CalculatorOutput(BaseModel):
    result: float

class CalculatorTool(BaseTool):
    name = "calculator_tool"
    description = "Performs basic math operation"
    category = "Query"
    input_schema = CalculatorInput
    output_schema = CalculatorOutput
    
    def execute(self, request: ToolRequest) -> ToolResult:
        inputs_obj = self.input_schema(**request.inputs)
        op = inputs_obj.operation
        a = inputs_obj.a
        b = inputs_obj.b
        if op == "add":
            res = a + b
        elif op == "subtract":
            res = a - b
        elif op == "multiply":
            res = a * b
        elif op == "divide":
            if b == 0:
                raise ZeroDivisionError("Division by zero is not allowed.")
            res = a / b
        else:
            raise ValueError(f"Unknown operation: {op}")
        return ToolResult(
            request_id=request.request_id,
            status=ToolStatus.SUCCESS,
            outputs={"result": res},
            diagnostics=ToolDiagnostics(execution_time_ms=0.0)
        )


# RegistrySearchMockTool is imported from deepcore.runtime.stubs.tools above.


# ==========================================
# Test Suite
# ==========================================

@pytest.fixture
def registry_service(db_session):
    service = RegistryService(db_session)
    # Register a default memory object to verify registry search mock tool
    service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Pytest Testing Guide",
        source_system="obsidian",
        location="/pytest.md",
        description="How to write pytest tests",
        status="active"
    ))
    return service

@pytest.fixture
def runtime_setup(registry_service):
    # Initialize registries and runtime
    tool_reg = ToolRegistry()
    
    # Instantiate tools
    echo = EchoTool()
    delay = DelayTool()
    calc = CalculatorTool()
    search = RegistrySearchMockTool(registry_service)
    
    # Register them
    tool_reg.register(echo)
    tool_reg.register(delay)
    tool_reg.register(calc)
    tool_reg.register(search)
    
    exec_reg = ExecutionRegistry(tool_reg)
    runtime = ToolRuntime(exec_reg)
    
    return {
        "tool_registry": tool_reg,
        "execution_registry": exec_reg,
        "runtime": runtime,
        "tools": {
            "echo": echo,
            "delay": delay,
            "calc": calc,
            "search": search
        }
    }


def test_registration_and_lookup(runtime_setup):
    tool_reg = runtime_setup["tool_registry"]
    exec_reg = runtime_setup["execution_registry"]
    
    # 1. Lookup existing tool
    resolved = exec_reg.resolve("echo_tool")
    assert resolved.name == "echo_tool"
    
    # 2. Duplicate registration should raise error
    with pytest.raises(ValueError, match="already registered"):
        tool_reg.register(EchoTool())
        
    # 3. Resolve missing tool should raise ToolNotFoundError
    with pytest.raises(ToolNotFoundError, match="not found"):
        exec_reg.resolve("missing_tool")
        
    # 4. Unregistration works
    tool_reg.unregister("echo_tool")
    assert tool_reg.get("echo_tool") is None
    with pytest.raises(ToolNotFoundError, match="not found"):
        exec_reg.resolve("echo_tool")
        
    # Test unregister non-existent raises ToolNotFoundError
    with pytest.raises(ToolNotFoundError, match="not registered"):
        tool_reg.unregister("echo_tool")


def test_descriptor_generation(runtime_setup):
    tool_reg = runtime_setup["tool_registry"]
    descriptors = tool_reg.list_tools()
    
    assert len(descriptors) == 4
    names = [d.name for d in descriptors]
    assert "echo_tool" in names
    assert "delay_tool" in names
    
    # Verify properties of EchoTool descriptor
    echo_desc = next(d for d in descriptors if d.name == "echo_tool")
    assert echo_desc.description == "Echoes inputs back"
    from deepcore.runtime.descriptors import DescriptorCategory
    assert echo_desc.category == DescriptorCategory.TOOL
    assert echo_desc.metadata["tool_category"] == "ReadWrite"
    assert "message" in echo_desc.input_schema["properties"]
    assert "message" in echo_desc.output_schema["properties"]


def test_successful_execution(runtime_setup):
    runtime = runtime_setup["runtime"]
    
    req = ToolRequest(
        request_id="req-001",
        inputs={"message": "hello world"}
    )
    res = runtime.execute("echo_tool", req)
    
    assert res.request_id == "req-001"
    assert res.status == ToolStatus.SUCCESS
    assert res.outputs == {"message": "hello world"}
    assert res.diagnostics.execution_time_ms >= 0.0


def test_input_validation(runtime_setup):
    runtime = runtime_setup["runtime"]
    
    # 1. Missing required parameter "message" for EchoTool
    req = ToolRequest(
        request_id="req-002",
        inputs={}
    )
    res = runtime.execute("echo_tool", req)
    assert res.status == ToolStatus.INVALID_INPUT
    assert "validation" in res.error_message.lower()
    
    # 2. Incorrect parameter type (passing dict instead of float) for DelayTool
    req = ToolRequest(
        request_id="req-003",
        inputs={"delay_seconds": "not-a-float"}
    )
    res = runtime.execute("delay_tool", req)
    assert res.status == ToolStatus.INVALID_INPUT


def test_timeout_enforcement(runtime_setup):
    runtime = runtime_setup["runtime"]
    
    # 1. Delay exceeds timeout_seconds
    req = ToolRequest(
        request_id="req-004",
        inputs={"delay_seconds": 0.5},
        timeout_seconds=0.1
    )
    res = runtime.execute("delay_tool", req)
    assert res.status == ToolStatus.TIMEOUT
    assert "timed out" in res.error_message
    
    # 2. Delay is within timeout_seconds
    req = ToolRequest(
        request_id="req-005",
        inputs={"delay_seconds": 0.05},
        timeout_seconds=1.0
    )
    res = runtime.execute("delay_tool", req)
    assert res.status == ToolStatus.SUCCESS
    assert res.outputs == {"completed": True}


def test_exception_mapping(runtime_setup):
    runtime = runtime_setup["runtime"]
    
    # Division by zero should map to ToolStatus.FAILURE
    req = ToolRequest(
        request_id="req-006",
        inputs={"a": 10.0, "b": 0.0, "operation": "divide"}
    )
    res = runtime.execute("calculator_tool", req)
    assert res.status == ToolStatus.FAILURE
    assert "Division by zero" in res.error_message
    assert len(res.diagnostics.errors_encountered) == 1
    assert "division by zero" in res.diagnostics.errors_encountered[0].lower()


def test_runtime_lifecycle_hooks(runtime_setup):
    # Create a custom subclass of ToolRuntime to spy on hooks
    hook_calls = {"before": 0, "after": 0}
    
    class SpyingToolRuntime(ToolRuntime):
        def before_execute(self, tool, request):
            hook_calls["before"] += 1
            
        def after_execute(self, tool, request, result):
            hook_calls["after"] += 1
            
    exec_reg = runtime_setup["execution_registry"]
    runtime = SpyingToolRuntime(exec_reg)
    
    req = ToolRequest(request_id="req-hook", inputs={"message": "hook test"})
    res = runtime.execute("echo_tool", req)
    
    assert res.status == ToolStatus.SUCCESS
    assert hook_calls["before"] == 1
    assert hook_calls["after"] == 1


def test_registry_search_mock_tool(runtime_setup):
    runtime = runtime_setup["runtime"]
    
    # Search for the "Pytest" memory object we registered in the fixture setup
    req = ToolRequest(
        request_id="req-search",
        inputs={"query": "Pytest"}
    )
    res = runtime.execute("registry_search_mock", req)
    
    assert res.status == ToolStatus.SUCCESS
    results = res.outputs.get("results", [])
    assert len(results) == 1
    assert results[0]["title"] == "Pytest Testing Guide"
    assert results[0]["location"] == "/pytest.md"
