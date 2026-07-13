---
Category: Specification
Status: Approved
Dependencies: [specifications/DESCRIPTOR_DESIGN.md, specifications/CAPABILITY_REGISTRY_DESIGN.md]
Source-of-truth: True
---

# Capability Discovery Service Design Specification

This document outlines the architecture and serialization model mappings of the DeepCore Capability Discovery Service.

---

## Objective

Act as a stateless composition and translation layer between the Capability Registry and future client API gateways. The discovery service maps internal descriptor structures into frontend-ready, decoupled data schemas.

---

## Architecture Principles

1. **Stateless Operations**: The service holds no state, caches no indexes, and performs composition on-demand directly from the registry.
2. **Schema Isolation**: Internal registry/descriptor schemas must never leak to API responses. The service maps internal objects into client-safe models (`CapabilitySummary`, `CapabilityDetail`).
3. **Generic Catalog Grouping**: Groups summaries dynamically without hardcoding capability categories. This allows adding new categories to `DescriptorCategory` without rewriting catalog logic or client response schemas.

---

## Discovery Response Models

### 1. `CapabilitySummary`
Exposes the core metadata representation:
- `id` (`str`): Unique capability identifier.
- `name` (`str`): Display name.
- `description` (`str`): Details summary.
- `category` (`DescriptorCategory`): Typed category.
- `enabled` (`bool`): Active status flag.
- `configurable` (`bool`): Setup requirement flag.
- `experimental` (`bool`): Preview flag.
- `tags` (`List[str]`): Filtering tags.
- `metadata` (`Dict[str, Any]`): Arbitrary dictionary.

### 2. `CapabilityDetail`
Separates base summary fields from subclass-specific metadata (such as schemas, variables, and latencies):
- `summary` (`CapabilitySummary`): Core metadata.
- `details` (`Dict[str, Any]`): Dict of specific fields excluding base descriptor parameters.

### 3. `CapabilityCategoryGroup`
Binds categorized capabilities:
- `category` (`DescriptorCategory`): Category enum.
- `display_name` (`str`): Categorized capitalized string.
- `capabilities` (`List[CapabilitySummary]`): List of capability summaries, sorted by ID.

### 4. `CapabilityCatalog`
Root catalog model sent to frontends:
- `categories` (`List[CapabilityCategoryGroup]`): Group list, sorted dynamically by category value.

---

## Service API

```python
class CapabilityDiscoveryService:
    def __init__(self, registry: CapabilityRegistry):
        ...

    def get_all_capabilities(self) -> List[CapabilitySummary]:
        """Maps and returns all summaries sorted alphabetically by ID."""
        ...

    def get_capability(self, id: str) -> CapabilityDetail:
        """Retrieves and compiles CapabilityDetail. Raises error if missing."""
        ...

    def get_by_category(self, category: DescriptorCategory) -> List[CapabilitySummary]:
        """Retrieves summaries within a category, sorted by ID."""
        ...

    def get_enabled(self) -> List[CapabilitySummary]:
        """Returns enabled summaries, sorted by ID."""
        ...

    def get_experimental(self) -> List[CapabilitySummary]:
        """Returns experimental summaries, sorted by ID."""
        ...

    def get_configurable(self) -> List[CapabilitySummary]:
        """Returns configurable summaries, sorted by ID."""
        ...

    def get_catalog(self) -> CapabilityCatalog:
        """Dynamically compiles grouped categories sorted by category name."""
        ...
```
