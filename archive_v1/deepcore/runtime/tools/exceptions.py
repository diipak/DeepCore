class ToolError(Exception):
    """Base exception for all tool runtime errors."""
    pass

class ToolNotFoundError(ToolError):
    """Raised when a tool is not found in the registry."""
    pass

class ToolValidationError(ToolError):
    """Raised when request inputs fail validation against the tool's schema."""
    pass

class ToolExecutionError(ToolError):
    """Raised when tool execution fails deterministically."""
    pass

class ToolTimeoutError(ToolError):
    """Raised when tool execution exceeds the allowed timeout."""
    pass
