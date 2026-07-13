import time
import concurrent.futures
import contextvars
from typing import Dict, Any, Optional
from deepcore.runtime.tools.base import BaseTool, ToolRequest, ToolResult, ToolStatus, ToolDiagnostics
from deepcore.runtime.tools.registry import ExecutionRegistry
from deepcore.runtime.tools.exceptions import (
    ToolNotFoundError,
    ToolValidationError,
    ToolExecutionError,
    ToolTimeoutError
)

class ToolRuntime:
    def __init__(self, execution_registry: ExecutionRegistry):
        self.execution_registry = execution_registry

    def before_execute(self, tool: BaseTool, request: ToolRequest) -> None:
        """Reserved lifecycle hook run before tool execution."""
        pass

    def after_execute(self, tool: BaseTool, request: ToolRequest, result: ToolResult) -> None:
        """Reserved lifecycle hook run after tool execution."""
        pass

    def execute(self, tool_name: str, request: ToolRequest) -> ToolResult:
        """
        Resolves the tool, validates the request, executes the tool (with timeout),
        runs lifecycle hooks, gathers diagnostics, and returns the ToolResult.
        """
        start_time = time.perf_counter()
        errors = []
        warnings = []
        
        # 1. Resolve Tool via ExecutionRegistry
        try:
            tool = self.execution_registry.resolve(tool_name)
        except ToolNotFoundError as e:
            # Re-raise ToolNotFoundError as it indicates resolution layer failure
            raise e

        # 2. Lifecycle Hook: before_execute
        self.before_execute(tool, request)

        # 3. Input Validation against tool input_schema
        try:
            # Validate inputs by parsing against Pydantic schema
            tool.input_schema(**request.inputs)
        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            result = ToolResult(
                request_id=request.request_id,
                status=ToolStatus.INVALID_INPUT,
                outputs={},
                artifacts=[],
                diagnostics=ToolDiagnostics(
                    execution_time_ms=execution_time_ms,
                    errors_encountered=[str(e)],
                    warnings=warnings
                ),
                error_message=f"Validation failed: {str(e)}"
            )
            self.after_execute(tool, request, result)
            return result

        # 4. Primitive Execution (with timeout)
        timeout = request.timeout_seconds
        
        try:
            if timeout is not None and timeout > 0:
                ctx = contextvars.copy_context()
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(ctx.run, tool.execute, request)
                    try:
                        result = future.result(timeout=timeout)
                    except concurrent.futures.TimeoutError:
                        raise ToolTimeoutError(f"Tool '{tool_name}' execution timed out after {timeout} seconds.")
            else:
                result = tool.execute(request)
            
            # Record/overwrite overall execution time at runtime level
            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            if result.diagnostics:
                result.diagnostics.execution_time_ms = execution_time_ms
            else:
                result.diagnostics = ToolDiagnostics(
                    execution_time_ms=execution_time_ms,
                    errors_encountered=errors,
                    warnings=warnings
                )
            
            # Run lifecycle hook: after_execute
            self.after_execute(tool, request, result)
            return result

        except ToolTimeoutError as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            result = ToolResult(
                request_id=request.request_id,
                status=ToolStatus.TIMEOUT,
                outputs={},
                artifacts=[],
                diagnostics=ToolDiagnostics(
                    execution_time_ms=execution_time_ms,
                    errors_encountered=[str(e)],
                    warnings=warnings
                ),
                error_message=str(e)
            )
            self.after_execute(tool, request, result)
            return result
            
        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            result = ToolResult(
                request_id=request.request_id,
                status=ToolStatus.FAILURE,
                outputs={},
                artifacts=[],
                diagnostics=ToolDiagnostics(
                    execution_time_ms=execution_time_ms,
                    errors_encountered=[str(e)],
                    warnings=warnings
                ),
                error_message=f"Tool execution failed: {str(e)}"
            )
            self.after_execute(tool, request, result)
            return result
