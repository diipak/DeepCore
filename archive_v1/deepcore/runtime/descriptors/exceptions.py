class DuplicateDescriptorError(ValueError):
    """Raised when a descriptor with a duplicate ID is registered."""
    pass


class DescriptorNotFoundError(KeyError):
    """Raised when a descriptor cannot be found by ID."""
    pass


class DescriptorValidationError(ValueError):
    """Raised when descriptor metadata integrity checks fail during registration."""
    pass


class RegistryFrozenError(RuntimeError):
    """Raised when an write operation is attempted on a frozen registry."""
    pass

