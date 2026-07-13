class SkillError(Exception):
    """Base exception for all skill runtime errors."""
    pass

class SkillNotFoundError(SkillError):
    """Raised when a skill is not found in the registry."""
    pass

class SkillValidationError(SkillError):
    """Raised when request inputs fail validation against the skill's schema."""
    pass

class SkillExecutionError(SkillError):
    """Raised when skill execution fails."""
    pass

class SkillRecursionError(SkillError):
    """Raised when circular execution or max depth is exceeded."""
    pass
