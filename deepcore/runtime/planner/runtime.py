import time
import copy
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set

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
    VariableReference
)
from deepcore.runtime.planner.scheduler import PlannerScheduler
from deepcore.runtime.planner.exceptions import (
    PlannerValidationError,
    PlannerDependencyError,
    PlannerExecutionError,
    PlannerCancellationError
)
from deepcore.runtime.execution.base import ExecutionRequest, ExecutionStatus
from deepcore.runtime.execution.runtime import ExecutionRuntime


# ==========================================
# Helpers for Reference Normalization
# ==========================================

# Matches steps.STEP_ID.attr.field or step.STEP_ID.attr.field
REF_PATTERN = r"\{\{\s*((?:steps|step)\.[a-zA-Z0-9_-]+\.(outputs\.[a-zA-Z0-9_-]+|status))\s*\}\}"

def extract_and_normalize_references(inputs: Dict[str, Any]) -> Dict[tuple, VariableReference]:
    """
    Recursively scans input dictionary for template strings and maps
    their key-paths to normalized VariableReference objects.
    """
    references = {}

    def traverse(current_val: Any, path: tuple):
        if isinstance(current_val, str):
            match = re.search(REF_PATTERN, current_val)
            if match:
                expr = match.group(1)
                parts = expr.split(".")
                step_id = parts[1]
                attr = parts[2]
                field_name = parts[3] if len(parts) > 3 else None
                
                references[path] = VariableReference(
                    step_id=step_id,
                    attribute=attr,
                    field_name=field_name
                )
        elif isinstance(current_val, dict):
            for k, v in current_val.items():
                traverse(v, path + (k,))
        elif isinstance(current_val, list):
            for idx, item in enumerate(current_val):
                traverse(item, path + (idx,))

    traverse(inputs, ())
    return references


def resolve_and_bind_references(
    inputs: Dict[str, Any],
    refs: Dict[tuple, VariableReference],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Creates a deep copy of step inputs and binds the resolved values
    of all normalized VariableReferences using the context.
    """
    resolved_inputs = copy.deepcopy(inputs)

    for path, var_ref in refs.items():
        step_id = var_ref.step_id
        if step_id not in context:
            raise ValueError(f"Referenced step '{step_id}' not found in execution context.")

        step_data = context[step_id]
        resolved_val = None
        
        if var_ref.attribute == "status":
            resolved_val = step_data.get("status")
        elif var_ref.attribute == "outputs":
            outputs = step_data.get("outputs", {}) or {}
            resolved_val = outputs.get(var_ref.field_name)

        # Get original value
        target_orig = inputs
        for key in path[:-1]:
            target_orig = target_orig[key]
        orig_val = target_orig[path[-1]]

        if isinstance(orig_val, str):
            exact_match = re.match(
                r"^\{\{\s*(?:steps|step)\.[a-zA-Z0-9_-]+\.(?:outputs\.[a-zA-Z0-9_-]+|status)\s*\}\}$",
                orig_val.strip()
            )
            if exact_match:
                final_val = resolved_val
            else:
                # Build pattern to match the template reference
                pattern = r"\{\{\s*(?:steps|step)\." + re.escape(var_ref.step_id) + r"\." + re.escape(var_ref.attribute)
                if var_ref.field_name:
                    pattern += r"\." + re.escape(var_ref.field_name)
                pattern += r"\s*\}\}"
                
                # Get current partially resolved string
                current_target = resolved_inputs
                for key in path[:-1]:
                    current_target = current_target[key]
                current_str = current_target[path[-1]]
                
                final_val = re.sub(pattern, str(resolved_val), current_str)
        else:
            final_val = resolved_val

        # Bind final value to target path
        target = resolved_inputs
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = final_val

    return resolved_inputs


# ==========================================
# Deterministic Condition Evaluator
# ==========================================

def resolve_path_value(path: str, context: Dict[str, Any]) -> Any:
    """Helper to resolve a dot-path like step.search.outputs.count against context."""
    parts = path.split(".")
    if not parts or parts[0] not in ("steps", "step"):
        return None
    if len(parts) < 2:
        return None

    step_id = parts[1]
    if step_id not in context:
        return None

    step_data = context[step_id]
    if len(parts) == 2:
        return step_data

    attr = parts[2]
    if attr == "status":
        return step_data.get("status")
    elif attr == "outputs" and len(parts) > 3:
        field = parts[3]
        outputs = step_data.get("outputs", {}) or {}
        return outputs.get(field)

    return None


def evaluate_condition_deterministically(expression: str, context: Dict[str, Any]) -> bool:
    """
    Deterministic Planner Expression Evaluator supporting:
    - step.STEP_ID.completed
    - step.STEP_ID.failed
    - steps.STEP_ID.outputs.VAR > VALUE (operators: ==, !=, >, <, >=, <=)
    - exists(steps.STEP_ID.outputs.VAR)
    """
    expression = expression.strip()

    # 1. exists(path)
    exists_match = re.match(r"^exists\((.+?)\)$", expression)
    if exists_match:
        path = exists_match.group(1).strip()
        val = resolve_path_value(path, context)
        return val is not None

    # 2. Comparisons: path OP value
    comp_match = re.match(r"^(.+?)\s*(==|!=|>=|<=|>|<)\s*(.+)$", expression)
    if comp_match:
        path = comp_match.group(1).strip()
        op = comp_match.group(2)
        raw_val = comp_match.group(3).strip()

        # Parse comparison value
        if raw_val.startswith("'") and raw_val.endswith("'"):
            val = raw_val[1:-1]
        elif raw_val.startswith('"') and raw_val.endswith('"'):
            val = raw_val[1:-1]
        elif raw_val == "True":
            val = True
        elif raw_val == "False":
            val = False
        elif raw_val == "None":
            val = None
        else:
            try:
                val = float(raw_val) if "." in raw_val else int(raw_val)
            except ValueError:
                val = raw_val

        actual_val = resolve_path_value(path, context)

        if op == "==":
            return actual_val == val
        elif op == "!=":
            return actual_val != val
        elif op == ">":
            return actual_val > val if actual_val is not None and val is not None else False
        elif op == "<":
            return actual_val < val if actual_val is not None and val is not None else False
        elif op == ">=":
            return actual_val >= val if actual_val is not None and val is not None else False
        elif op == "<=":
            return actual_val <= val if actual_val is not None and val is not None else False

    # 3. Simple path/status check
    if expression.endswith(".completed"):
        step_id = expression[:-10].split(".")[-1]
        step_data = context.get(step_id, {})
        return step_data.get("status") == "completed"
    elif expression.endswith(".failed"):
        step_id = expression[:-7].split(".")[-1]
        step_data = context.get(step_id, {})
        return step_data.get("status") == "failed"

    # Standard truthy evaluation
    actual_val = resolve_path_value(expression, context)
    return bool(actual_val)


# ==========================================
# Planner Runtime Engine
# ==========================================

class PlannerRuntime:
    """
    Deterministic Planner executing, scheduling, and monitoring ExecutionPlans.
    """
    def __init__(self, execution_runtime: ExecutionRuntime):
        self.execution_runtime = execution_runtime
        self._cancelled_plans: Set[str] = set()

    def cancel_plan(self, plan_id: str) -> None:
        """Signal cancellation for a running plan."""
        self._cancelled_plans.add(plan_id)

    def execute(self, request: PlannerRequest) -> PlannerResult:
        """
        Executes an ExecutionPlan step-by-step using ExecutionRuntime,
        respecting conditions, dependencies, and retry rules.
        """
        start_time = time.perf_counter()
        plan = request.plan
        
        # 1. Topological Sort and Graph Validation
        try:
            execution_order = PlannerScheduler.get_execution_order(plan)
        except PlannerDependencyError as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            plan.status = PlanStatus.FAILED
            plan.timeline.append(TimelineEvent(
                event_type="plan_failed",
                message=f"Plan dependency error: {str(e)}"
            ))
            return PlannerResult(
                request_id=request.request_id,
                status=PlannerStatus.FAILURE,
                plan=plan,
                diagnostics=PlannerDiagnostics(execution_time_ms=execution_time_ms),
                error_message=str(e)
            )

        # 2. Parse and normalize variable references for all steps
        step_references = {}
        for step in plan.steps:
            step_references[step.step_id] = extract_and_normalize_references(step.inputs)

        # 3. Build execution context from currently completed/running steps
        # This supports checkpointing (resuming plans where some steps are already completed)
        context = {}
        for step in plan.steps:
            context[step.step_id] = {
                "status": step.status.value,
                "outputs": step.outputs or {}
            }

        plan.status = PlanStatus.EXECUTING
        plan.timeline.append(TimelineEvent(
            event_type="plan_started",
            message=f"Started plan: {plan.goal}"
        ))

        steps_executed = 0
        steps_skipped = 0
        steps_failed = 0

        # 4. Drive step execution sequentially
        for step in execution_order:
            # Check for cancellation signal
            if plan.plan_id in self._cancelled_plans:
                plan.status = PlanStatus.CANCELLED
                # Any unfinished step gets marked as failed/cancelled
                for s in execution_order:
                    if s.status in (StepStatus.PENDING, StepStatus.RUNNING):
                        s.status = StepStatus.FAILED
                        s.error_message = "Execution cancelled."
                plan.timeline.append(TimelineEvent(
                    event_type="plan_cancelled",
                    message="Plan execution cancelled by user."
                ))
                execution_time_ms = (time.perf_counter() - start_time) * 1000.0
                return PlannerResult(
                    request_id=request.request_id,
                    status=PlannerStatus.CANCELLED,
                    plan=plan,
                    diagnostics=PlannerDiagnostics(
                        execution_time_ms=execution_time_ms,
                        steps_executed=steps_executed,
                        steps_skipped=steps_skipped,
                        steps_failed=steps_failed
                    ),
                    error_message="Plan execution cancelled."
                )

            # Skip steps already completed (checkpoint support)
            if step.status == StepStatus.COMPLETED:
                continue

            # Evaluate step conditions
            conditions_met = True
            for cond in step.conditions:
                try:
                    if not evaluate_condition_deterministically(cond.expression, context):
                        conditions_met = False
                        break
                except Exception as cond_err:
                    conditions_met = False
                    step.error_message = f"Condition evaluation error: {str(cond_err)}"
                    break

            if not conditions_met:
                step.status = StepStatus.SKIPPED
                context[step.step_id]["status"] = StepStatus.SKIPPED.value
                plan.timeline.append(TimelineEvent(
                    event_type="step_skipped",
                    step_id=step.step_id,
                    message=f"Skipped step '{step.step_id}' due to condition failure."
                ))
                steps_skipped += 1
                continue

            # Resolve variable references and bind resolved inputs
            try:
                resolved_inputs = resolve_and_bind_references(
                    step.inputs,
                    step_references[step.step_id],
                    context
                )
            except Exception as ref_err:
                step.status = StepStatus.FAILED
                step.error_message = f"Variable resolution failed: {str(ref_err)}"
                context[step.step_id]["status"] = StepStatus.FAILED.value
                plan.timeline.append(TimelineEvent(
                    event_type="step_failed",
                    step_id=step.step_id,
                    message=step.error_message
                ))
                steps_failed += 1
                plan.status = PlanStatus.FAILED
                execution_time_ms = (time.perf_counter() - start_time) * 1000.0
                return PlannerResult(
                    request_id=request.request_id,
                    status=PlannerStatus.FAILURE,
                    plan=plan,
                    diagnostics=PlannerDiagnostics(
                        execution_time_ms=execution_time_ms,
                        steps_executed=steps_executed,
                        steps_skipped=steps_skipped,
                        steps_failed=steps_failed
                    ),
                    error_message=step.error_message
                )

            # Execute step with RetryPolicy
            step.status = StepStatus.RUNNING
            step.started_at = datetime.now(timezone.utc)
            plan.timeline.append(TimelineEvent(
                event_type="step_started",
                step_id=step.step_id,
                message=f"Running step '{step.step_id}'"
            ))

            policy = step.retry_policy
            backoff = policy.backoff_seconds
            success = False
            last_error = None
            
            for attempt in range(1, policy.max_attempts + 1):
                try:
                    exec_req = ExecutionRequest(
                        request_id=f"{request.request_id}-{step.step_id}-{attempt}",
                        handler_name=step.handler_name,
                        inputs=resolved_inputs
                    )
                    
                    exec_res = self.execution_runtime.execute(exec_req)
                    
                    if exec_res.status == ExecutionStatus.SUCCESS:
                        success = True
                        step.outputs = exec_res.outputs
                        step.artifacts = [
                            a for a in exec_res.artifacts
                        ]
                        break
                    else:
                        last_error = exec_res.error_message or "Execution failed."
                except Exception as attempt_err:
                    last_error = str(attempt_err)

                # Wait/Exponential Backoff before retrying
                if attempt < policy.max_attempts:
                    plan.timeline.append(TimelineEvent(
                        event_type="step_retry",
                        step_id=step.step_id,
                        message=f"Attempt {attempt} failed for step '{step.step_id}'. Retrying...",
                        details={"attempt": attempt, "error": last_error}
                    ))
                    time.sleep(backoff)
                    if policy.exponential:
                        backoff *= 2

            step.finished_at = datetime.now(timezone.utc)
            
            if success:
                step.status = StepStatus.COMPLETED
                context[step.step_id]["status"] = StepStatus.COMPLETED.value
                context[step.step_id]["outputs"] = step.outputs
                plan.timeline.append(TimelineEvent(
                    event_type="step_finished",
                    step_id=step.step_id,
                    message=f"Completed step '{step.step_id}'"
                ))
                steps_executed += 1
            else:
                step.status = StepStatus.FAILED
                step.error_message = last_error
                context[step.step_id]["status"] = StepStatus.FAILED.value
                plan.timeline.append(TimelineEvent(
                    event_type="step_failed",
                    step_id=step.step_id,
                    message=f"Step '{step.step_id}' failed: {last_error}"
                ))
                steps_failed += 1
                plan.status = PlanStatus.FAILED
                execution_time_ms = (time.perf_counter() - start_time) * 1000.0
                return PlannerResult(
                    request_id=request.request_id,
                    status=PlannerStatus.FAILURE,
                    plan=plan,
                    diagnostics=PlannerDiagnostics(
                        execution_time_ms=execution_time_ms,
                        steps_executed=steps_executed,
                        steps_skipped=steps_skipped,
                        steps_failed=steps_failed
                    ),
                    error_message=f"Plan failed at step '{step.step_id}': {last_error}"
                )

        plan.status = PlanStatus.SUCCEEDED
        plan.timeline.append(TimelineEvent(
            event_type="plan_finished",
            message=f"Succeeded plan: {plan.goal}"
        ))

        execution_time_ms = (time.perf_counter() - start_time) * 1000.0
        return PlannerResult(
            request_id=request.request_id,
            status=PlannerStatus.SUCCESS,
            plan=plan,
            diagnostics=PlannerDiagnostics(
                execution_time_ms=execution_time_ms,
                steps_executed=steps_executed,
                steps_skipped=steps_skipped,
                steps_failed=steps_failed
            )
        )

    def build_plan_for_goal(self, goal: str, plan_id: Optional[str] = None) -> ExecutionPlan:
        """
        Dynamically constructs an ExecutionPlan based on the goal and registered executables.
        Ensures the Conversation Runtime remains unaware of specific skill implementations.
        """
        import uuid
        plan_id = plan_id or f"plan-{uuid.uuid4().hex[:8]}"
        
        # Get registered executable names
        exec_names = list(self.execution_runtime.execution_registry._executables.keys())
        
        steps = []
        search_handler = next((name for name in exec_names if "search" in name), None)
        echo_handler = next((name for name in exec_names if "echo" in name), None)
        
        if "search" in goal.lower() and search_handler:
            query = goal
            if "search for" in goal.lower():
                query = goal.lower().split("search for")[-1].strip()
            elif "search" in goal.lower():
                query = goal.lower().split("search")[-1].strip()
                
            steps.append(ExecutionStep(
                step_id="step_search",
                handler_name=search_handler,
                description=f"Search query matching: {query}",
                inputs={"query": query}
            ))
            
            if echo_handler:
                steps.append(ExecutionStep(
                    step_id="step_echo",
                    handler_name=echo_handler,
                    description="Echo search results",
                    inputs={"message": "Matches: {{steps.step_search.outputs.processed_results}}"}
                ))
        else:
            handler = echo_handler or (exec_names[0] if exec_names else "echo_skill")
            steps.append(ExecutionStep(
                step_id="step_echo",
                handler_name=handler,
                description="Echo goal response",
                inputs={"message": f"Echo: {goal}"}
            ))
            
        return ExecutionPlan(
            plan_id=plan_id,
            goal=goal,
            origin="conversation",
            steps=steps,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

