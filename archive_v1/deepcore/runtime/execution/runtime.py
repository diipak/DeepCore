import time
from typing import Dict, Any, Optional
from deepcore.runtime.execution.base import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionDiagnostics,
    ExecutionArtifact
)
from deepcore.runtime.execution.registry import ExecutionRegistry
from deepcore.runtime.execution.exceptions import (
    ExecutableNotFoundError,
    ExecutionValidationError,
    ExecutionTimeoutError
)
from deepcore.runtime.skills.base import BaseSkill, SkillRequest, SkillStatus
from deepcore.runtime.skills.runtime import SkillRuntime

class ExecutionRuntime:
    """
    Universal execution gateway for all executable handlers in DeepCore.
    Decouples Planner from concrete execution types (Skills, Workflows, Macros, etc.).
    """
    def __init__(self, execution_registry: ExecutionRegistry, skill_runtime: SkillRuntime):
        self.execution_registry = execution_registry
        self.skill_runtime = skill_runtime

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Resolves the target executable, validates, routes execution,
        gathers diagnostics, and returns an ExecutionResult.
        """
        start_time = time.perf_counter()
        
        # 1. Resolve Executable from Registry
        exe = self.execution_registry.get(request.handler_name)
        if not exe:
            raise ExecutableNotFoundError(f"Executable '{request.handler_name}' not found.")

        # 2. Route Execution based on contract type
        try:
            if isinstance(exe, BaseSkill):
                # Route to SkillRuntime
                skill_req = SkillRequest(
                    request_id=request.request_id,
                    inputs=request.inputs
                )
                skill_res = self.skill_runtime.execute(request.handler_name, skill_req)
                
                # Map SkillResult to ExecutionResult
                execution_time_ms = (time.perf_counter() - start_time) * 1000.0
                
                status_mapped = ExecutionStatus.FAILURE
                if skill_res.status == SkillStatus.SUCCESS:
                    status_mapped = ExecutionStatus.SUCCESS
                elif skill_res.status == SkillStatus.INVALID_INPUT:
                    status_mapped = ExecutionStatus.INVALID_INPUT

                artifacts_mapped = [
                    ExecutionArtifact(
                        artifact_id=a.artifact_id,
                        name=a.name,
                        artifact_type=a.artifact_type,
                        uri=a.uri,
                        created_at=a.created_at,
                        metadata=a.metadata
                    ) for a in skill_res.artifacts
                ]

                diagnostics_mapped = ExecutionDiagnostics(
                    execution_time_ms=execution_time_ms,
                    steps_run=skill_res.diagnostics.steps_run,
                    warnings=skill_res.diagnostics.warnings
                )

                return ExecutionResult(
                    request_id=request.request_id,
                    status=status_mapped,
                    outputs=skill_res.outputs,
                    artifacts=artifacts_mapped,
                    diagnostics=diagnostics_mapped,
                    error_message=skill_res.error_message
                )
            else:
                # Direct Executable handling (duck-typing: execute(request) -> ExecutionResult)
                # First, validate inputs if the executable has input_schema
                if hasattr(exe, "input_schema"):
                    try:
                        exe.input_schema(**request.inputs)
                    except Exception as val_err:
                        execution_time_ms = (time.perf_counter() - start_time) * 1000.0
                        return ExecutionResult(
                            request_id=request.request_id,
                            status=ExecutionStatus.INVALID_INPUT,
                            outputs={},
                            artifacts=[],
                            diagnostics=ExecutionDiagnostics(
                                execution_time_ms=execution_time_ms,
                                steps_run=[],
                                warnings=[]
                            ),
                            error_message=f"Validation failed: {str(val_err)}"
                        )

                # Run direct execute method
                res = exe.execute(request)
                
                # Make sure the result execution time is recorded
                execution_time_ms = (time.perf_counter() - start_time) * 1000.0
                if res.diagnostics:
                    res.diagnostics.execution_time_ms = execution_time_ms
                else:
                    res.diagnostics = ExecutionDiagnostics(
                        execution_time_ms=execution_time_ms
                    )
                return res

        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                request_id=request.request_id,
                status=ExecutionStatus.FAILURE,
                outputs={},
                artifacts=[],
                diagnostics=ExecutionDiagnostics(
                    execution_time_ms=execution_time_ms,
                    steps_run=[],
                    warnings=[]
                ),
                error_message=f"Execution failed: {str(e)}"
            )
