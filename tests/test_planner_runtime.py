import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

from deepcore.runtime.planner.base import (
    ExecutionPlan,
    ExecutionStep,
    PlannerRequest,
    PlannerResult,
    PlannerStatus,
    PlannerDiagnostics,
    TimelineEvent,
    StepStatus,
    PlanStatus,
    RetryPolicy,
    StepCondition
)
from deepcore.runtime.planner.runtime import (
    PlannerRuntime,
    extract_and_normalize_references,
    resolve_and_bind_references,
    evaluate_condition_deterministically
)
from deepcore.runtime.planner.scheduler import PlannerScheduler
from deepcore.runtime.planner.exceptions import (
    PlannerValidationError,
    PlannerDependencyError,
    PlannerExecutionError
)

from deepcore.runtime.execution.base import ExecutionRequest, ExecutionResult, ExecutionStatus, ExecutionDiagnostics
from deepcore.runtime.execution.registry import ExecutionRegistry
from deepcore.runtime.execution.runtime import ExecutionRuntime
from deepcore.runtime.skills.registry import SkillRegistry
from deepcore.runtime.skills.runtime import SkillRuntime
from deepcore.runtime.tools.registry import ToolRegistry, ExecutionRegistry as ToolExecRegistry
from deepcore.runtime.tools.runtime import ToolRuntime
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObjectCreate, ObjectType

from tests.test_tool_runtime import EchoTool, RegistrySearchMockTool, CalculatorTool
from tests.test_skill_runtime import EchoSkill, RegistrySearchEchoSkill


# ==========================================
# Mock Flaky Executable for Retries Testing
# ==========================================

class FlakyExecutable:
    """Mock executable that fails N times before succeeding."""
    def __init__(self, fail_count: int):
        self.fail_count = fail_count
        self.attempts = 0

    def get_descriptor(self):
        return type("Desc", (), {
            "name": "flaky_executable",
            "description": "Fails N times before succeeding",
            "input_schema": type("In", (), {"model_json_schema": lambda: {}}),
            "output_schema": type("Out", (), {"model_json_schema": lambda: {}}),
            "capabilities": []
        })()

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            return ExecutionResult(
                request_id=request.request_id,
                status=ExecutionStatus.FAILURE,
                outputs={},
                diagnostics=ExecutionDiagnostics(execution_time_ms=0.0),
                error_message=f"Flaky failure attempt {self.attempts}"
            )
        return ExecutionResult(
            request_id=request.request_id,
            status=ExecutionStatus.SUCCESS,
            outputs={"success": True, "attempts": self.attempts},
            diagnostics=ExecutionDiagnostics(execution_time_ms=0.0)
        )


# ==========================================
# Test Suite Setup
# ==========================================

@pytest.fixture
def registry_service(db_session):
    service = RegistryService(db_session)
    service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Planner Blueprint Spec",
        source_system="obsidian",
        location="/planner.md",
        description="Planner spec",
        status="active"
    ))
    return service

@pytest.fixture
def runtime_setup(registry_service):
    # 1. Tool Runtime
    tool_registry = ToolRegistry()
    echo_tool = EchoTool()
    search_tool = RegistrySearchMockTool(registry_service)
    calc_tool = CalculatorTool()
    tool_registry.register(echo_tool)
    tool_registry.register(search_tool)
    tool_registry.register(calc_tool)
    
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
    execution_registry.register("echo_skill", echo_skill)
    execution_registry.register("registry_search_echo_skill", search_skill)
    
    # Generic direct flaky executable
    flaky_exe = FlakyExecutable(fail_count=2)
    execution_registry.register("flaky_executable", flaky_exe)
    
    execution_runtime = ExecutionRuntime(execution_registry, skill_runtime)
    
    # 4. Planner Runtime
    planner_runtime = PlannerRuntime(execution_runtime)
    
    return {
        "planner_runtime": planner_runtime,
        "flaky_exe": flaky_exe,
        "execution_registry": execution_registry
    }


# ==========================================
# Unit Tests for Helper Logics
# ==========================================

def test_variable_normalization_parsing():
    inputs = {
        "message": "Start processing",
        "nested": {
            "query_count": "{{steps.step_1.outputs.count}}",
            "status": "{{step.step_2.status}}"
        },
        "list_items": ["{{steps.step_3.outputs.item_id}}", 42]
    }
    
    refs = extract_and_normalize_references(inputs)
    
    assert len(refs) == 3
    assert refs[("nested", "query_count")].step_id == "step_1"
    assert refs[("nested", "query_count")].attribute == "outputs"
    assert refs[("nested", "query_count")].field_name == "count"
    
    assert refs[("nested", "status")].step_id == "step_2"
    assert refs[("nested", "status")].attribute == "status"
    assert refs[("nested", "status")].field_name is None
    
    assert refs[("list_items", 0)].step_id == "step_3"
    assert refs[("list_items", 0)].attribute == "outputs"
    assert refs[("list_items", 0)].field_name == "item_id"


def test_variable_resolution_binding():
    inputs = {
        "message": "Placeholder",
        "nested": {
            "query_count": "{{steps.step_1.outputs.count}}",
            "status": "{{step.step_2.status}}"
        }
    }
    refs = extract_and_normalize_references(inputs)
    
    context = {
        "step_1": {"status": "completed", "outputs": {"count": 10}},
        "step_2": {"status": "completed", "outputs": {}}
    }
    
    resolved = resolve_and_bind_references(inputs, refs, context)
    assert resolved["nested"]["query_count"] == 10
    assert resolved["nested"]["status"] == "completed"
    assert resolved["message"] == "Placeholder"  # Unchanged


def test_deterministic_condition_evaluator():
    context = {
        "search": {
            "status": "completed",
            "outputs": {"count": 5, "results": ["a", "b"]}
        },
        "download": {
            "status": "failed",
            "outputs": {}
        }
    }
    
    # 1. Step status checks
    assert evaluate_condition_deterministically("step.search.completed", context) is True
    assert evaluate_condition_deterministically("steps.download.failed", context) is True
    assert evaluate_condition_deterministically("steps.search.failed", context) is False
    
    # 2. Exists checks
    assert evaluate_condition_deterministically("exists(steps.search.outputs.results)", context) is True
    assert evaluate_condition_deterministically("exists(steps.download.outputs.results)", context) is False
    
    # 3. Numeric Comparisons
    assert evaluate_condition_deterministically("steps.search.outputs.count > 0", context) is True
    assert evaluate_condition_deterministically("steps.search.outputs.count >= 5", context) is True
    assert evaluate_condition_deterministically("steps.search.outputs.count < 3", context) is False
    assert evaluate_condition_deterministically("steps.search.outputs.count != 10", context) is True
    assert evaluate_condition_deterministically("steps.search.outputs.count == 5", context) is True


# ==========================================
# Planner Runtime Execution Tests
# ==========================================

def test_simple_plan_execution(runtime_setup):
    planner = runtime_setup["planner_runtime"]
    
    step = ExecutionStep(
        step_id="step_1",
        handler_name="echo_skill",
        inputs={"message": "hello planner execution"}
    )
    plan = ExecutionPlan(
        plan_id="plan-simple",
        goal="Run a simple echo step",
        origin="user",
        steps=[step],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    req = PlannerRequest(request_id="req-plan-1", plan=plan)
    res = planner.execute(req)
    
    assert res.status == PlannerStatus.SUCCESS
    assert res.plan.status == PlanStatus.SUCCEEDED
    assert step.status == StepStatus.COMPLETED
    assert step.outputs == {"result": "hello planner execution"}
    
    # Verify timeline audits
    timeline = res.plan.timeline
    assert len(timeline) == 4
    assert timeline[0].event_type == "plan_started"
    assert timeline[1].event_type == "step_started"
    assert timeline[2].event_type == "step_finished"
    assert timeline[3].event_type == "plan_finished"


def test_chain_plan_execution(runtime_setup):
    planner = runtime_setup["planner_runtime"]
    
    step_1 = ExecutionStep(
        step_id="step_search",
        handler_name="registry_search_echo_skill",
        inputs={"query": "Blueprint"}
    )
    step_2 = ExecutionStep(
        step_id="step_echo",
        handler_name="echo_skill",
        inputs={"message": "Matches: {{steps.step_search.outputs.processed_results}}"}
    )
    plan = ExecutionPlan(
        plan_id="plan-chain",
        goal="Run a two-step dependency chain",
        origin="user",
        steps=[step_1, step_2],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    req = PlannerRequest(request_id="req-plan-chain", plan=plan)
    res = planner.execute(req)
    
    assert res.status == PlannerStatus.SUCCESS
    assert step_1.status == StepStatus.COMPLETED
    assert "Planner Blueprint Spec" in str(step_2.outputs["result"])



def test_dependency_validation_and_sorting():
    # Circular: 1 -> 2 -> 1
    step_1 = ExecutionStep(
        step_id="step_1",
        handler_name="echo_skill",
        inputs={"message": "{{steps.step_2.outputs.res}}"}
    )
    step_2 = ExecutionStep(
        step_id="step_2",
        handler_name="echo_skill",
        inputs={"message": "{{steps.step_1.outputs.res}}"}
    )
    plan = ExecutionPlan(
        plan_id="plan-circular",
        goal="Test circularity cycle rejection",
        origin="user",
        steps=[step_1, step_2],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    with pytest.raises(PlannerDependencyError, match="Circular dependency"):
        PlannerScheduler.get_execution_order(plan)


def test_condition_evaluation_and_skipping(runtime_setup):
    planner = runtime_setup["planner_runtime"]
    
    # Step 1 succeeds but output count is 0
    # Step 2 has condition "steps.step_1.outputs.count > 0" so it should skip
    step_1 = ExecutionStep(
        step_id="step_1",
        handler_name="echo_skill",
        inputs={"message": "ignore"}
    )
    # Mocking outputs to set count=0 since echo_skill doesn't output count
    # We will execute step_1, then manually set count outputs in test or mock it
    # E.g. we use echo_skill, but condition relies on exist(step_1.outputs.count)
    step_2 = ExecutionStep(
        step_id="step_2",
        handler_name="echo_skill",
        inputs={"message": "won't run"},
        conditions=[StepCondition(expression="steps.step_1.outputs.count > 0")]
    )
    
    # We alter the step_1 execute mapping, or we just write a direct executable
    class MockCounter:
        def get_descriptor(self):
            return type("Desc", (), {
                "name": "counter", "description": "",
                "input_schema": type("In", (), {"model_json_schema": lambda: {}}),
                "output_schema": type("Out", (), {"model_json_schema": lambda: {}}),
                "capabilities": []
            })()
        def execute(self, request):
            return ExecutionResult(
                request_id=request.request_id,
                status=ExecutionStatus.SUCCESS,
                outputs={"count": 0},
                diagnostics=ExecutionDiagnostics(execution_time_ms=0.0)
            )

    runtime_setup["execution_registry"].register("counter", MockCounter())
    step_1.handler_name = "counter"
    
    plan = ExecutionPlan(
        plan_id="plan-skip",
        goal="Test conditional skips",
        origin="user",
        steps=[step_1, step_2],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    req = PlannerRequest(request_id="req-plan-skip", plan=plan)
    res = planner.execute(req)
    
    assert res.status == PlannerStatus.SUCCESS
    assert step_1.status == StepStatus.COMPLETED
    assert step_2.status == StepStatus.SKIPPED
    
    # Check skip timeline logging
    skipped_events = [e for e in res.plan.timeline if e.event_type == "step_skipped"]
    assert len(skipped_events) == 1
    assert "skipped step 'step_2'" in skipped_events[0].message.lower()


def test_retry_policy_execution(runtime_setup):
    planner = runtime_setup["planner_runtime"]
    flaky = runtime_setup["flaky_exe"]
    
    step = ExecutionStep(
        step_id="flaky_step",
        handler_name="flaky_executable",
        inputs={},
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.01, exponential=False)
    )
    plan = ExecutionPlan(
        plan_id="plan-flaky",
        goal="Test step retries",
        origin="user",
        steps=[step],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    # flaky needs 2 failures before success, so it will succeed on the 3rd attempt
    req = PlannerRequest(request_id="req-flaky", plan=plan)
    res = planner.execute(req)
    
    assert res.status == PlannerStatus.SUCCESS
    assert step.status == StepStatus.COMPLETED
    assert step.outputs["attempts"] == 3
    
    # Verify timeline includes retry events
    retries = [e for e in res.plan.timeline if e.event_type == "step_retry"]
    assert len(retries) == 2


def test_flaky_exhaustion_failure(runtime_setup):
    planner = runtime_setup["planner_runtime"]
    
    # Re-register or set flaky limit higher
    flaky = FlakyExecutable(fail_count=5)
    runtime_setup["execution_registry"].unregister("flaky_executable")
    runtime_setup["execution_registry"].register("flaky_executable", flaky)
    
    step = ExecutionStep(
        step_id="flaky_step",
        handler_name="flaky_executable",
        inputs={},
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.01)
    )
    plan = ExecutionPlan(
        plan_id="plan-flaky-fail",
        goal="Test step retry exhaustion",
        origin="user",
        steps=[step],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    req = PlannerRequest(request_id="req-flaky-fail", plan=plan)
    res = planner.execute(req)
    
    assert res.status == PlannerStatus.FAILURE
    assert step.status == StepStatus.FAILED
    assert "flaky failure attempt 3" in res.error_message.lower()


def test_plan_cancellation(runtime_setup):
    planner = runtime_setup["planner_runtime"]
    
    step_1 = ExecutionStep(
        step_id="step_1",
        handler_name="echo_skill",
        inputs={"message": "run first"}
    )
    step_2 = ExecutionStep(
        step_id="step_2",
        handler_name="echo_skill",
        inputs={"message": "won't run due to cancellation"}
    )
    plan = ExecutionPlan(
        plan_id="plan-cancel",
        goal="Test cancellation propagation",
        origin="user",
        steps=[step_1, step_2],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    # Cancel the plan right before executing it (e.g. simulating intermediate cancellation signal)
    planner.cancel_plan("plan-cancel")
    
    req = PlannerRequest(request_id="req-cancel", plan=plan)
    res = planner.execute(req)
    
    assert res.status == PlannerStatus.CANCELLED
    assert res.plan.status == PlanStatus.CANCELLED
    assert step_1.status == StepStatus.FAILED  # Marked failed due to cancellation
    assert step_1.error_message == "Execution cancelled."


def test_planner_runtime_build_and_execute_plan(runtime_setup):
    planner = runtime_setup["planner_runtime"]
    plan = planner.build_plan_for_goal("Search for Blueprint")
    
    req = PlannerRequest(request_id="req-build-exec", plan=plan)
    res = planner.execute(req)
    
    assert res.status == PlannerStatus.SUCCESS
    assert res.plan.status == PlanStatus.SUCCEEDED
    assert "Planner Blueprint Spec" in str(res.plan.steps[-1].outputs.get("result"))


