import pytest
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from deepcore.runtime.skills.base import (
    BaseSkill,
    SkillStatus,
    SkillCapability,
    ExecutionCharacteristics,
    SkillArtifact,
    SkillDiagnostics,
    SkillRequest,
    SkillResult,
    SkillDescriptor,
    SkillRuntimeInterface
)
from deepcore.runtime.skills.registry import SkillRegistry
from deepcore.runtime.skills.runtime import SkillRuntime
from deepcore.runtime.skills.exceptions import (
    SkillNotFoundError,
    SkillValidationError,
    SkillExecutionError,
    SkillRecursionError
)
from deepcore.runtime.tools.base import ToolRequest, ToolStatus
from deepcore.runtime.tools.registry import ToolRegistry, ExecutionRegistry
from deepcore.runtime.tools.runtime import ToolRuntime
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObjectCreate, ObjectType
from deepcore.runtime.stubs.skills import (
    EchoSkill,
    EchoSkillInput,
    EchoSkillOutput,
    RegistrySearchEchoSkill,
    SearchEchoInput,
    SearchEchoOutput,
)

# Import mock tools from the canonical stubs package
from deepcore.runtime.stubs.tools import EchoTool, RegistrySearchMockTool


# EchoSkill, EchoSkillInput, EchoSkillOutput, RegistrySearchEchoSkill,
# SearchEchoInput, SearchEchoOutput are imported from
# deepcore.runtime.stubs.skills — the canonical single source of truth.


class CircularInput(BaseModel):
    target_skill: str
    depth: int = 1

class CircularOutput(BaseModel):
    message: str

class CircularSkill(BaseSkill):
    name = "circular_skill"
    description = "Mock skill to test recursion protection"
    input_schema = CircularInput
    output_schema = CircularOutput

    def __init__(self, runtime_interface: SkillRuntimeInterface):
        self.runtime_interface = runtime_interface

    def execute(self, request: SkillRequest) -> SkillResult:
        inputs_obj = self.input_schema(**request.inputs)
        
        if inputs_obj.depth <= 0:
            return SkillResult(
                request_id=request.request_id,
                status=SkillStatus.SUCCESS,
                outputs={"message": "reached bottom"},
                diagnostics=SkillDiagnostics(execution_time_ms=0.0)
            )
            
        # Call the target skill using runtime_interface (which propagates call stack)
        sub_req = SkillRequest(
            request_id=f"{request.request_id}-sub",
            inputs={"target_skill": inputs_obj.target_skill, "depth": inputs_obj.depth - 1},
            call_stack=request.call_stack  # propagate call stack
        )
        
        return self.runtime_interface.execute_skill(inputs_obj.target_skill, sub_req)


# ==========================================
# Test Suite
# ==========================================

@pytest.fixture
def registry_service(db_session):
    service = RegistryService(db_session)
    # Seed database objects for the RegistrySearchMockTool
    service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="DeepCore Architecture Spec",
        source_system="obsidian",
        location="/deepcore.md",
        description="DeepCore design files",
        status="active"
    ))
    service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="DeepCore Security Policy",
        source_system="obsidian",
        location="/security.md",
        description="Obsidian security parameters",
        status="active"
    ))
    return service

@pytest.fixture
def setup_runtimes(registry_service):
    # Setup Tool Runtime
    tool_registry = ToolRegistry()
    echo_tool = EchoTool()
    search_tool = RegistrySearchMockTool(registry_service)
    tool_registry.register(echo_tool)
    tool_registry.register(search_tool)
    
    exec_tool_registry = ExecutionRegistry(tool_registry)
    tool_runtime = ToolRuntime(exec_tool_registry)
    
    # Setup Skill Registry
    skill_registry = SkillRegistry()
    
    return {
        "skill_registry": skill_registry,
        "tool_runtime": tool_runtime
    }


def test_skills_registration_and_descriptor(setup_runtimes):
    skill_reg = setup_runtimes["skill_registry"]
    tool_runtime = setup_runtimes["tool_runtime"]
    
    echo_skill = EchoSkill(tool_runtime)
    skill_reg.register(echo_skill)
    
    # 1. Lookup registered skill
    assert skill_reg.get("echo_skill") == echo_skill
    
    # 2. Prevent duplicate registration
    with pytest.raises(ValueError, match="already registered"):
        skill_reg.register(EchoSkill(tool_runtime))
        
    # 3. List descriptors
    descriptors = skill_reg.list_skills()
    assert len(descriptors) == 1
    assert descriptors[0].name == "echo_skill"
    assert descriptors[0].capabilities == [SkillCapability.FILESYSTEM]
    
    # 4. Unregister skill
    skill_reg.unregister("echo_skill")
    assert skill_reg.get("echo_skill") is None
    
    with pytest.raises(SkillNotFoundError):
        skill_reg.unregister("echo_skill")


def test_echo_skill_execution(setup_runtimes):
    skill_reg = setup_runtimes["skill_registry"]
    tool_runtime = setup_runtimes["tool_runtime"]
    
    echo_skill = EchoSkill(tool_runtime)
    skill_reg.register(echo_skill)
    
    skill_runtime = SkillRuntime(skill_reg, tool_runtime)
    
    req = SkillRequest(
        request_id="req-skill-1",
        inputs={"message": "deepcore skills working"}
    )
    res = skill_runtime.execute("echo_skill", req)
    
    assert res.status == SkillStatus.SUCCESS
    assert res.outputs == {"result": "deepcore skills working"}
    assert res.diagnostics.steps_run == ["call_echo_tool"]
    assert len(res.diagnostics.tool_calls) == 1
    assert res.diagnostics.tool_calls[0]["tool"] == "echo_tool"
    assert res.diagnostics.tool_calls[0]["status"] == ToolStatus.SUCCESS


def test_skill_input_validation(setup_runtimes):
    skill_reg = setup_runtimes["skill_registry"]
    tool_runtime = setup_runtimes["tool_runtime"]
    
    echo_skill = EchoSkill(tool_runtime)
    skill_reg.register(echo_skill)
    
    skill_runtime = SkillRuntime(skill_reg, tool_runtime)
    
    # Missing required inputs
    req = SkillRequest(request_id="req-skill-val", inputs={})
    res = skill_runtime.execute("echo_skill", req)
    assert res.status == SkillStatus.INVALID_INPUT
    assert "validation" in res.error_message.lower()


def test_registry_search_echo_orchestration(setup_runtimes):
    skill_reg = setup_runtimes["skill_registry"]
    tool_runtime = setup_runtimes["tool_runtime"]
    
    search_echo = RegistrySearchEchoSkill(tool_runtime)
    skill_reg.register(search_echo)
    
    skill_runtime = SkillRuntime(skill_reg, tool_runtime)
    
    req = SkillRequest(
        request_id="req-orch",
        inputs={"query": "DeepCore"}
    )
    res = skill_runtime.execute("registry_search_echo_skill", req)
    
    assert res.status == SkillStatus.SUCCESS
    processed = res.outputs.get("processed_results", [])
    assert len(processed) == 2
    assert "Echo: DeepCore Architecture Spec" in processed
    assert "Echo: DeepCore Security Policy" in processed
    
    tool_calls = res.diagnostics.tool_calls
    assert len(tool_calls) == 3
    assert tool_calls[0]["tool"] == "registry_search_mock"
    assert tool_calls[1]["tool"] == "echo_tool"
    assert tool_calls[2]["tool"] == "echo_tool"


def test_recursion_protection(setup_runtimes):
    skill_reg = setup_runtimes["skill_registry"]
    tool_runtime = setup_runtimes["tool_runtime"]
    
    skill_runtime = SkillRuntime(skill_reg, tool_runtime)
    
    # Register circular skill
    circ = CircularSkill(skill_runtime)
    skill_reg.register(circ)
    
    # 1. Test direct circular execution (circular_skill calling circular_skill)
    req = SkillRequest(
        request_id="req-circ",
        inputs={"target_skill": "circular_skill", "depth": 2}
    )
    res = skill_runtime.execute("circular_skill", req)
    assert res.status == SkillStatus.FAILURE
    assert "circular skill execution detected" in res.error_message.lower()
    
    # 2. Test max depth limit of 4
    # Register helper skills that act as intermediate chain hops
    class ChainSkill(BaseSkill):
        name = "chain_skill"
        description = "Chains to another skill"
        input_schema = CircularInput
        output_schema = CircularOutput
        
        def __init__(self, r):
            self.r = r
        def execute(self, request):
            inputs_obj = self.input_schema(**request.inputs)
            sub_req = SkillRequest(
                request_id=request.request_id,
                inputs=request.inputs,
                call_stack=request.call_stack
            )
            return self.r.execute_skill(inputs_obj.target_skill, sub_req)

    # Let's create chain_skill_a, chain_skill_b, chain_skill_c
    skill_a = ChainSkill(skill_runtime)
    skill_a.name = "skill_a"
    skill_reg.register(skill_a)
    
    skill_b = ChainSkill(skill_runtime)
    skill_b.name = "skill_b"
    skill_reg.register(skill_b)
    
    skill_c = ChainSkill(skill_runtime)
    skill_c.name = "skill_c"
    skill_reg.register(skill_c)
    
    # Execute a clean chain (no circularity but exceeds max depth limit)
    # chain: circular_skill -> skill_a -> skill_b -> skill_c -> echo_skill
    # Call stack depth at echo_skill resolver will be 4 (circular_skill, skill_a, skill_b, skill_c)
    # This exceeds limit=4 because call_stack length is 4.
    req = SkillRequest(
        request_id="req-depth",
        inputs={"target_skill": "skill_a", "depth": 1}
    )
    # Setup chain
    # circular_skill inputs: target_skill="skill_a"
    # skill_a inputs will redirect to target_skill="skill_b"
    # skill_b inputs will redirect to target_skill="skill_c"
    # skill_c inputs will redirect to target_skill="echo_skill"
    # To test this, we override the inputs dynamically in the test or keep inputs simple
    
    # Let's redefine execute of ChainSkill to dynamically resolve target_skill from input list or simple chain
    # We can create a simple chain runner skill instead
    class ChainInput(BaseModel):
        chain: List[str]

    class ChainOutput(BaseModel):
        status: str

    class CustomChainSkill(BaseSkill):
        name = "custom_chain"
        description = "Executes next skill in chain list"
        input_schema = ChainInput
        output_schema = ChainOutput
        
        def __init__(self, r):
            self.r = r
            
        def execute(self, request):
            chain = request.inputs["chain"]
            if not chain:
                return SkillResult(
                    request_id=request.request_id,
                    status=SkillStatus.SUCCESS,
                    outputs={"status": "completed"},
                    diagnostics=SkillDiagnostics(execution_time_ms=0.0)
                )
            next_target = chain[0]
            next_chain = chain[1:]
            
            sub_req = SkillRequest(
                request_id=request.request_id,
                inputs={"chain": next_chain},
                call_stack=request.call_stack
            )
            return self.r.execute_skill(next_target, sub_req)

    # Register 5 instances of CustomChainSkill with unique names
    skills_chain = []
    for i in range(5):
        s = CustomChainSkill(skill_runtime)
        s.name = f"chain_{i}"
        skill_reg.register(s)
        skills_chain.append(s.name)
        
    # Execute chain of depth 5: chain_0 -> chain_1 -> chain_2 -> chain_3 -> chain_4
    # The 5th execution (chain_4) should be rejected because the stack size is 4.
    req_chain = SkillRequest(
        request_id="req-chain-depth",
        inputs={"chain": skills_chain[1:]} # chain_0 calls chain_1, which calls chain_2, etc.
    )
    res_chain = skill_runtime.execute("chain_0", req_chain)
    
    assert res_chain.status == SkillStatus.FAILURE
    assert "max skill execution depth exceeded" in res_chain.error_message.lower()
