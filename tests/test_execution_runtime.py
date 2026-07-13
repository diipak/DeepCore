import pytest
from typing import Dict, Any, List
from pydantic import BaseModel

from deepcore.runtime.execution.base import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionDiagnostics,
    ExecutionDescriptor
)
from deepcore.runtime.execution.registry import ExecutionRegistry
from deepcore.runtime.execution.runtime import ExecutionRuntime
from deepcore.runtime.execution.exceptions import (
    ExecutionError,
    ExecutableNotFoundError,
    ExecutionValidationError
)

from deepcore.runtime.skills.registry import SkillRegistry
from deepcore.runtime.skills.runtime import SkillRuntime
from deepcore.runtime.tools.registry import ToolRegistry, ExecutionRegistry as ToolExecRegistry
from deepcore.runtime.tools.runtime import ToolRuntime
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObjectCreate, ObjectType

# Reuse tools/skills from previous phases
from tests.test_tool_runtime import EchoTool, RegistrySearchMockTool
from tests.test_skill_runtime import EchoSkill, RegistrySearchEchoSkill


# ==========================================
# Mock Executable (Duck-typed, no inheritance)
# ==========================================

class EchoInputs(BaseModel):
    message: str

class EchoExecutable:
    """Generic Executable target verifying duck-typing resolution."""
    input_schema = EchoInputs
    
    def get_descriptor(self) -> ExecutionDescriptor:
        return ExecutionDescriptor(
            name="echo_executable",
            description="Mock direct executable echoing messages",
            input_schema=self.input_schema.model_json_schema(),
            output_schema=self.input_schema.model_json_schema(),
            capabilities=["filesystem"],
            examples=[]
        )

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        # Validate inputs
        inputs_obj = self.input_schema(**request.inputs)
        return ExecutionResult(
            request_id=request.request_id,
            status=ExecutionStatus.SUCCESS,
            outputs={"message": inputs_obj.message},
            diagnostics=ExecutionDiagnostics(execution_time_ms=0.0)
        )


# ==========================================
# Test Suite
# ==========================================

@pytest.fixture
def registry_service(db_session):
    service = RegistryService(db_session)
    service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Execution Engine Blueprint",
        source_system="obsidian",
        location="/exec.md",
        description="Specifications for Execution Runtime",
        status="active"
    ))
    return service

@pytest.fixture
def full_runtime_setup(registry_service):
    # 1. Tool Runtime
    tool_registry = ToolRegistry()
    echo_tool = EchoTool()
    search_tool = RegistrySearchMockTool(registry_service)
    tool_registry.register(echo_tool)
    tool_registry.register(search_tool)
    
    exec_tool_reg = ToolExecRegistry(tool_registry)
    tool_runtime = ToolRuntime(exec_tool_reg)
    
    # 2. Skill Runtime
    skill_registry = SkillRegistry()
    echo_skill = EchoSkill(tool_runtime)
    search_skill = RegistrySearchEchoSkill(tool_runtime)
    skill_registry.register(echo_skill)
    skill_registry.register(search_skill)
    skill_runtime = SkillRuntime(skill_registry, tool_runtime)
    
    # 3. Execution Runtime
    execution_registry = ExecutionRegistry()
    
    # Register skills as executables
    execution_registry.register("echo_skill", echo_skill)
    execution_registry.register("registry_search_echo_skill", search_skill)
    
    # Register generic non-skill executable
    echo_exe = EchoExecutable()
    execution_registry.register("echo_executable", echo_exe)
    
    execution_runtime = ExecutionRuntime(execution_registry, skill_runtime)
    
    return {
        "execution_registry": execution_registry,
        "execution_runtime": execution_runtime,
        "skills": {
            "echo": echo_skill,
            "search": search_skill
        },
        "executables": {
            "echo_exe": echo_exe
        }
    }


def test_executable_registration_and_descriptor(full_runtime_setup):
    reg = full_runtime_setup["execution_registry"]
    
    # 1. Lookup
    exe = reg.get("echo_executable")
    assert exe is not None
    assert exe.get_descriptor().name == "echo_executable"
    
    # 2. Duplicate prevention
    with pytest.raises(ValueError, match="already registered"):
        reg.register("echo_executable", EchoExecutable())
        
    # 3. List descriptors
    descriptors = reg.list_descriptors()
    assert len(descriptors) == 3
    names = [d.name for d in descriptors]
    assert "echo_executable" in names
    assert "echo_skill" in names
    assert "registry_search_echo_skill" in names
    
    # Verify capability list mapping in descriptor
    search_desc = next(d for d in descriptors if d.name == "registry_search_echo_skill")
    assert "registry" in search_desc.capabilities
    
    # 4. Unregister
    reg.unregister("echo_executable")
    assert reg.get("echo_executable") is None
    
    with pytest.raises(ExecutableNotFoundError):
        reg.unregister("echo_executable")


def test_direct_executable_routing(full_runtime_setup):
    runtime = full_runtime_setup["execution_runtime"]
    
    req = ExecutionRequest(
        request_id="req-exec-1",
        handler_name="echo_executable",
        inputs={"message": "hello direct executable"}
    )
    res = runtime.execute(req)
    
    assert res.status == ExecutionStatus.SUCCESS
    assert res.outputs == {"message": "hello direct executable"}
    assert res.diagnostics.execution_time_ms >= 0.0


def test_direct_executable_validation(full_runtime_setup):
    runtime = full_runtime_setup["execution_runtime"]
    
    # Missing required inputs
    req = ExecutionRequest(
        request_id="req-exec-val",
        handler_name="echo_executable",
        inputs={}
    )
    res = runtime.execute(req)
    assert res.status == ExecutionStatus.INVALID_INPUT
    assert "validation" in res.error_message.lower()


def test_skill_routing_and_mapping(full_runtime_setup):
    runtime = full_runtime_setup["execution_runtime"]
    
    # 1. Route to echo_skill
    req = ExecutionRequest(
        request_id="req-skill-exec-1",
        handler_name="echo_skill",
        inputs={"message": "hello skill execution"}
    )
    res = runtime.execute(req)
    
    assert res.status == ExecutionStatus.SUCCESS
    assert res.outputs == {"result": "hello skill execution"}
    
    # 2. Route to compound registry search skill
    req_search = ExecutionRequest(
        request_id="req-skill-exec-2",
        handler_name="registry_search_echo_skill",
        inputs={"query": "Blueprint"}
    )
    res_search = runtime.execute(req_search)
    
    assert res_search.status == ExecutionStatus.SUCCESS
    processed = res_search.outputs.get("processed_results", [])
    assert len(processed) == 1
    assert "Echo: Execution Engine Blueprint" in processed


def test_unregistered_executable_raises_error(full_runtime_setup):
    runtime = full_runtime_setup["execution_runtime"]
    
    req = ExecutionRequest(
        request_id="req-missing",
        handler_name="missing_executable",
        inputs={}
    )
    with pytest.raises(ExecutableNotFoundError, match="not found"):
        runtime.execute(req)
