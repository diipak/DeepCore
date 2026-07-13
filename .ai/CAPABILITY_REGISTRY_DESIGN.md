# Capability Registry Design Specification

This document details the architecture and validation invariants of the DeepCore Capability Registry subsystem.

---

## Objective

Provide a unified, metadata-only storage engine to register, unregister, index, and query capability descriptors. The registry contains zero execution responsibility and never communicates with runtime engines.

---

## Design Invariants

1. **Deterministic Ordering**: All lookup, query, search, and list actions must return descriptors sorted alphabetically by `id`. This is a system-wide platform invariant.
2. **Immutable Storage**: The registry owns registered descriptors and never permits mutating them. Immutability is enforced via frozen Pydantic models.
3. **Descriptor Validation Laws**: Validation must execute and pass before a descriptor is stored. Failure raises appropriate custom exceptions.

---

## Pre-Registration Validation Invariants

Every registered descriptor is validated against these rules:
- **Unique ID**: The `descriptor.id` must be a non-empty string and must not already exist in the registry.
- **Valid Category**: `descriptor.category` must be a valid member of the `DescriptorCategory` enum.
- **Valid Versioning**: Both `descriptor_version` and `implementation_version` must be non-empty strings.

---

## Public API

```python
class CapabilityRegistry:
    def register(self, descriptor: BaseDescriptor) -> None:
        """Validates and registers a descriptor. Raises exceptions on failure."""
        ...

    def register_provider(self, provider: DescriptorProvider) -> None:
        """Convenience method extracting and registering a descriptor from a provider."""
        ...

    def unregister(self, id: str) -> None:
        """Removes descriptor from registry. Raises error if missing."""
        ...

    def get(self, id: str) -> BaseDescriptor:
        """Fetches descriptor by ID. Raises error if missing."""
        ...

    def list(self) -> List[BaseDescriptor]:
        """Lists all registered descriptors, sorted alphabetically by ID."""
        ...

    def list_by_category(self, category: DescriptorCategory) -> List[BaseDescriptor]:
        """Lists descriptors in a category, sorted alphabetically by ID."""
        ...

    def search(self, tags: List[str]) -> List[BaseDescriptor]:
        """Queries descriptors matching all tags, sorted alphabetically by ID."""
        ...
```

---

## Error Handling Contracts

- **`DuplicateDescriptorError`**: Raised if a descriptor with an already registered ID is added.
- **`DescriptorNotFoundError`**: Raised if lookup or unregistration targets a missing ID.
- **`DescriptorValidationError`**: Raised if empty ID, empty versions, or invalid category checks fail.

---

## Registry Lifecycle (Future Refinement)

The Capability Registry should evolve from request-scoped bootstrap behavior into an application-scoped singleton:

1. **Bootstrap Phase**: Currently, the registry is reconstructed and repopulated inside the API router dependency helper `get_discovery_service` per request.
2. **Target Architecture**: In future milestones focusing on application composition and startup dependency management, the registry will be instantiated on startup, populated with descriptors, frozen to prevent runtime changes, and injected globally as a stateless singleton.

