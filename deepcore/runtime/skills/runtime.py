import time
from typing import Dict, Any, Optional, List
from deepcore.runtime.skills.base import (
    BaseSkill,
    SkillRequest,
    SkillResult,
    SkillStatus,
    SkillDiagnostics,
    SkillRuntimeInterface
)
from deepcore.runtime.skills.registry import SkillRegistry
from deepcore.runtime.skills.exceptions import (
    SkillNotFoundError,
    SkillValidationError,
    SkillExecutionError,
    SkillRecursionError
)
from deepcore.runtime.tools.runtime import ToolRuntime

class SkillRuntime(SkillRuntimeInterface):
    """
    SkillRuntime coordinates the execution of deterministic skills.
    Integrates ToolRuntime via dependency injection.
    """
    def __init__(self, skill_registry: SkillRegistry, tool_runtime: ToolRuntime):
        self.skill_registry = skill_registry
        self.tool_runtime = tool_runtime

    def execute(self, skill_name: str, request: SkillRequest) -> SkillResult:
        """
        Main execution entrypoint for a skill.
        Validates request inputs, verifies recursion safety, and executes skill.
        """
        start_time = time.perf_counter()
        
        # 1. Resolve Skill
        skill = self.skill_registry.get(skill_name)
        if not skill:
            raise SkillNotFoundError(f"Skill '{skill_name}' not found in registry.")

        # 2. Recursion and Depth Verification
        try:
            if skill_name in request.call_stack:
                raise SkillRecursionError(
                    f"Circular skill execution detected: '{skill_name}' already exists in stack {request.call_stack}"
                )
            if len(request.call_stack) >= 4:
                raise SkillRecursionError("Max skill execution depth exceeded (limit=4).")
        except SkillRecursionError as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            return SkillResult(
                request_id=request.request_id,
                status=SkillStatus.FAILURE,
                outputs={},
                artifacts=[],
                diagnostics=SkillDiagnostics(
                    execution_time_ms=execution_time_ms,
                    steps_run=[],
                    tool_calls=[],
                    warnings=[str(e)]
                ),
                error_message=str(e)
            )

        # 3. Request Input Validation
        try:
            skill.input_schema(**request.inputs)
        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            return SkillResult(
                request_id=request.request_id,
                status=SkillStatus.INVALID_INPUT,
                outputs={},
                artifacts=[],
                diagnostics=SkillDiagnostics(
                    execution_time_ms=execution_time_ms,
                    steps_run=[],
                    tool_calls=[],
                    warnings=[]
                ),
                error_message=f"Validation failed: {str(e)}"
            )

        # 4. Prepare Child Request (propagate call stack)
        child_call_stack = list(request.call_stack) + [skill_name]
        child_request = SkillRequest(
            request_id=request.request_id,
            inputs=request.inputs,
            context_package_uuid=request.context_package_uuid,
            call_stack=child_call_stack
        )

        # 5. Execute Skill logic
        try:
            result = skill.execute(child_request)
            
            # Record total duration at runtime level
            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            if result.diagnostics:
                result.diagnostics.execution_time_ms = execution_time_ms
            else:
                result.diagnostics = SkillDiagnostics(
                    execution_time_ms=execution_time_ms
                )
            return result
        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            return SkillResult(
                request_id=request.request_id,
                status=SkillStatus.FAILURE,
                outputs={},
                artifacts=[],
                diagnostics=SkillDiagnostics(
                    execution_time_ms=execution_time_ms,
                    steps_run=[],
                    tool_calls=[],
                    warnings=[]
                ),
                error_message=f"Skill execution failed: {str(e)}"
            )

    def execute_skill(self, skill_name: str, request: SkillRequest) -> SkillResult:
        """Implementation of SkillRuntimeInterface for executing child skills."""
        return self.execute(skill_name, request)
