import pytest
import time
import copy
from datetime import datetime, timezone

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
from deepcore.runtime.planner.runtime import PlannerRuntime
from deepcore.runtime.planner.scheduler import PlannerScheduler
from deepcore.runtime.planner.exceptions import PlannerDependencyError

from deepcore.runtime.execution.base import ExecutionRequest, ExecutionResult, ExecutionStatus, ExecutionDiagnostics
from deepcore.runtime.execution.registry import ExecutionRegistry
from deepcore.runtime.execution.runtime import ExecutionRuntime
from deepcore.runtime.skills.registry import SkillRegistry
from deepcore.runtime.skills.runtime import SkillRuntime
from deepcore.runtime.tools.registry import ToolRegistry, ExecutionRegistry as ToolExecRegistry
from deepcore.runtime.tools.runtime import ToolRuntime
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObjectCreate, ObjectType
from deepcore.runtime.health import KernelHealthReport

from tests.test_tool_runtime import EchoTool, RegistrySearchMockTool
from tests.test_skill_runtime import EchoSkill, RegistrySearchEchoSkill
from tests.test_planner_runtime import FlakyExecutable


@pytest.fixture
def registry_service(db_session):
    service = RegistryService(db_session)
    service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="DeepCore Integration Spec",
        source_system="obsidian",
        location="/integration.md",
        description="Integration testing spec document",
        status="active"
    ))
    return service


@pytest.fixture
def kernel_setup(registry_service):
    # 1. Tool Layer
    tool_registry = ToolRegistry()
    echo_tool = EchoTool()
    search_tool = RegistrySearchMockTool(registry_service)
    tool_registry.register(echo_tool)
    tool_registry.register(search_tool)
    
    exec_tool_reg = ToolExecRegistry(tool_registry)
    tool_runtime = ToolRuntime(exec_tool_reg)
    
    # 2. Skill Layer
    skill_registry = SkillRegistry()
    echo_skill = EchoSkill(tool_runtime)
    search_skill = RegistrySearchEchoSkill(tool_runtime)
    skill_registry.register(echo_skill)
    skill_registry.register(search_skill)
    skill_runtime = SkillRuntime(skill_registry, tool_runtime)
    
    # 3. Execution Layer (Gateway)
    execution_registry = ExecutionRegistry()
    execution_registry.register("echo_skill", echo_skill)
    execution_registry.register("registry_search_echo_skill", search_skill)
    
    # Add flaky executable for Scenario B
    flaky_exe = FlakyExecutable(fail_count=2)
    execution_registry.register("flaky_executable", flaky_exe)
    
    execution_runtime = ExecutionRuntime(execution_registry, skill_runtime)
    
    # 4. Planner Layer (Orchestrator)
    planner_runtime = PlannerRuntime(execution_runtime)
    
    return {
        "tool_registry": tool_registry,
        "skill_registry": skill_registry,
        "execution_registry": execution_registry,
        "planner_runtime": planner_runtime,
        "flaky_exe": flaky_exe
    }


# ==========================================
# Scenario A: End-to-End Query-Echo
# ==========================================

def test_scenario_a_query_echo_flow(kernel_setup):
    planner = kernel_setup["planner_runtime"]
    
    step_search = ExecutionStep(
        step_id="search_step",
        handler_name="registry_search_echo_skill",
        inputs={"query": "Integration"}
    )
    step_echo = ExecutionStep(
        step_id="echo_step",
        handler_name="echo_skill",
        inputs={"message": "Result found: {{steps.search_step.outputs.processed_results}}"}
    )
    
    plan = ExecutionPlan(
        plan_id="scenario-a-plan",
        goal="Search database and echo results",
        origin="integration_test",
        steps=[step_search, step_echo],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    req = PlannerRequest(request_id="req-scenario-a", plan=plan)
    res = planner.execute(req)
    
    assert res.status == PlannerStatus.SUCCESS
    assert res.plan.status == PlanStatus.SUCCEEDED
    
    # Check outputs and artifacts
    assert step_search.status == StepStatus.COMPLETED
    assert step_echo.status == StepStatus.COMPLETED
    assert "DeepCore Integration Spec" in str(step_echo.outputs["result"])
    
    # Check timeline auditing
    timeline_events = [e.event_type for e in res.plan.timeline]
    assert "plan_started" in timeline_events
    assert "step_started" in timeline_events
    assert "step_finished" in timeline_events
    assert "plan_finished" in timeline_events


# ==========================================
# Scenario B: Tool Failure & Retry Recovery
# ==========================================

def test_scenario_b_failure_recovery_flow(kernel_setup):
    planner = kernel_setup["planner_runtime"]
    
    step_flaky = ExecutionStep(
        step_id="flaky_step",
        handler_name="flaky_executable",
        inputs={},
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.01, exponential=False)
    )
    
    plan = ExecutionPlan(
        plan_id="scenario-b-plan",
        goal="Run a step that is flaky but recovers",
        origin="integration_test",
        steps=[step_flaky],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    req = PlannerRequest(request_id="req-scenario-b", plan=plan)
    res = planner.execute(req)
    
    assert res.status == PlannerStatus.SUCCESS
    assert step_flaky.status == StepStatus.COMPLETED
    assert step_flaky.outputs["attempts"] == 3
    
    # Check retries registered on the timeline
    retry_events = [e for e in res.plan.timeline if e.event_type == "step_retry"]
    assert len(retry_events) == 2
    assert res.diagnostics.steps_executed == 1
    assert res.diagnostics.steps_failed == 0


# ==========================================
# Scenario C: Conditional Branching & Skipping
# ==========================================

def test_scenario_c_conditional_branching(kernel_setup):
    planner = kernel_setup["planner_runtime"]
    
    # Step 1 does a search that will find objects
    step_search = ExecutionStep(
        step_id="search_step",
        handler_name="registry_search_echo_skill",
        inputs={"query": "Integration"}
    )
    
    # Step 2 only runs if steps.search_step.outputs has processed_results
    step_conditional_run = ExecutionStep(
        step_id="run_step",
        handler_name="echo_skill",
        inputs={"message": "FoundSpec"},
        conditions=[StepCondition(expression="exists(steps.search_step.outputs.processed_results)")]
    )
    
    # Step 3 only runs if condition "step.search_step.failed" (which is false)
    step_conditional_skip = ExecutionStep(
        step_id="skip_step",
        handler_name="echo_skill",
        inputs={"message": "FailureRecoveryRun"},
        conditions=[StepCondition(expression="step.search_step.failed")]
    )
    
    plan = ExecutionPlan(
        plan_id="scenario-c-plan",
        goal="Test branching and skipping logic",
        origin="integration_test",
        steps=[step_search, step_conditional_run, step_conditional_skip],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    req = PlannerRequest(request_id="req-scenario-c", plan=plan)
    res = planner.execute(req)
    
    assert res.status == PlannerStatus.SUCCESS
    assert step_search.status == StepStatus.COMPLETED
    assert step_conditional_run.status == StepStatus.COMPLETED
    assert step_conditional_skip.status == StepStatus.SKIPPED
    
    assert res.diagnostics.steps_executed == 2
    assert res.diagnostics.steps_skipped == 1


# ==========================================
# Scenario D: Plan Cancellation Flow
# ==========================================

def test_scenario_d_cancellation(kernel_setup):
    planner = kernel_setup["planner_runtime"]
    
    step_1 = ExecutionStep(
        step_id="step_1",
        handler_name="echo_skill",
        inputs={"message": "first"}
    )
    step_2 = ExecutionStep(
        step_id="step_2",
        handler_name="echo_skill",
        inputs={"message": "second"}
    )
    
    plan = ExecutionPlan(
        plan_id="scenario-d-plan",
        goal="Test intermediate cancellation",
        origin="integration_test",
        steps=[step_1, step_2],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    # Send cancellation signal before running
    planner.cancel_plan("scenario-d-plan")
    
    req = PlannerRequest(request_id="req-scenario-d", plan=plan)
    res = planner.execute(req)
    
    assert res.status == PlannerStatus.CANCELLED
    assert res.plan.status == PlanStatus.CANCELLED
    
    # Verify timeline logged the cancellation
    cancel_events = [e for e in res.plan.timeline if e.event_type == "plan_cancelled"]
    assert len(cancel_events) == 1


# ==========================================
# Scenario E: Determinism Verification
# ==========================================

def test_scenario_e_determinism_verification(kernel_setup):
    planner = kernel_setup["planner_runtime"]
    
    step_search = ExecutionStep(
        step_id="search_step",
        handler_name="registry_search_echo_skill",
        inputs={"query": "Integration"}
    )
    step_echo = ExecutionStep(
        step_id="echo_step",
        handler_name="echo_skill",
        inputs={"message": "Matches: {{steps.search_step.outputs.processed_results}}"}
    )
    
    # Run the identical plan 50 times
    results = []
    for i in range(50):
        # We need a clean deep copy of steps to start from PENDING state for each run
        step_1_copy = copy.deepcopy(step_search)
        step_2_copy = copy.deepcopy(step_echo)
        
        plan = ExecutionPlan(
            plan_id=f"determinism-plan-{i}",
            goal="Determine if kernel has side-effects",
            origin="integration_test",
            steps=[step_1_copy, step_2_copy],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        req = PlannerRequest(request_id=f"req-det-{i}", plan=plan)
        res = planner.execute(req)
        results.append(res)
        
    # Baseline comparison using first result
    first_res = results[0]
    assert first_res.status == PlannerStatus.SUCCESS
    
    for i in range(1, 50):
        res = results[i]
        
        # 1. Assert status and results match
        assert res.status == first_res.status
        assert res.plan.status == first_res.plan.status
        
        # 2. Assert step outputs match exactly
        assert len(res.plan.steps) == len(first_res.plan.steps)
        for idx in range(len(res.plan.steps)):
            step_current = res.plan.steps[idx]
            step_first = first_res.plan.steps[idx]
            assert step_current.status == step_first.status
            assert step_current.outputs == step_first.outputs
            assert len(step_current.artifacts) == len(step_first.artifacts)
            
        # 3. Assert timeline event types and ordering match exactly
        assert len(res.plan.timeline) == len(first_res.plan.timeline)
        for idx in range(len(res.plan.timeline)):
            event_current = res.plan.timeline[idx]
            event_first = first_res.plan.timeline[idx]
            assert event_current.event_type == event_first.event_type
            assert event_current.step_id == event_first.step_id
            assert event_current.message == event_first.message


# ==========================================
# Diagnostic Health Report Verification
# ==========================================

def test_kernel_health_report(kernel_setup):
    health = KernelHealthReport(
        tool_registry=kernel_setup["tool_registry"],
        skill_registry=kernel_setup["skill_registry"],
        execution_registry=kernel_setup["execution_registry"]
    )
    
    summary = health.get_summary()
    assert summary["kernel_version"] == "0.1.0"
    assert "tool_runtime" in summary["runtimes"]
    
    # Check registered objects count
    assert len(summary["registered_tools"]) >= 2
    assert len(summary["registered_skills"]) >= 2
    assert len(summary["registered_executables"]) >= 3
    
    markdown = health.generate_report_markdown()
    assert "# DeepCore Kernel Health Report" in markdown
    assert "echo_skill" in markdown
    assert "registry_search_echo_skill" in markdown
    assert "flaky_executable" in markdown
