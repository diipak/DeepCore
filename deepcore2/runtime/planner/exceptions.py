class PlannerError(Exception):
    """Base exception for all planner runtime errors."""
    pass

class PlannerValidationError(PlannerError):
    """Raised when an ExecutionPlan fails configuration or validation checks."""
    pass

class PlannerDependencyError(PlannerError):
    """Raised when step dependencies are invalid or circular."""
    pass

class PlannerExecutionError(PlannerError):
    """Raised when step execution fails and retries are exhausted."""
    pass

class PlannerCancellationError(PlannerError):
    """Raised when plan execution is cancelled."""
    pass
