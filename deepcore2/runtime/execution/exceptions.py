class ExecutionError(Exception):
    """Base exception for all execution runtime errors."""
    pass

class ExecutableNotFoundError(ExecutionError):
    """Raised when an executable is not found in the registry."""
    pass

class ExecutionValidationError(ExecutionError):
    """Raised when request inputs fail validation against the executable's schema."""
    pass

class ExecutionTimeoutError(ExecutionError):
    """Raised when request execution times out."""
    pass
