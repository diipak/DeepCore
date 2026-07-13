---
Category: Design
Status: Stable
Dependencies: [architecture/ARCHITECTURE.md]
Source-of-truth: True
---

# Descriptor Architecture Specification

This document details the standardized metadata descriptor hierarchy for all executable components and services within DeepCore.

---

## Objective

Standardize how capabilities describe themselves to the host system and frontends. Descriptors are strictly metadata objects: they describe behavior, but never execute or modify runtime behavior.

---

## Invariants

1. **Strict Immutability**: All descriptor instances are Pydantic-frozen (`frozen=True`) to prevent accidental runtime state alterations.
2. **Metadata-Only separation**: No execution handles, databases, or runtime state pointers should exist in any descriptor object.
3. **Descriptor Identity Law**: A Descriptor is the immutable public identity of a capability. Execution engines never depend on descriptor metadata to make runtime decisions.

---

## Descriptor Hierarchy

Every descriptor inherits from a common `BaseDescriptor`.

### BaseDescriptor Fields

* **`id`** (`str`): Globally unique and stable identifier for the capability.
* **`name`** (`str`): Human-readable name.
* **`description`** (`str`): Detailed description.
* **`category`** (`DescriptorCategory`): Strongly typed category enum (`tool`, `skill`, `provider`, `conversation`, `prompt`, `model`).
* **`descriptor_version`** (`str`): Schema version contract (default `"1.0.0"`).
* **`implementation_version`** (`str`): Underlying implementation version (default `"1.0.0"`).
* **`enabled`** (`bool`): Active state flag.
* **`configurable`** (`bool`): Flag declaring if runtime config is required.
* **`experimental`** (`bool`): Preview-only flag.
* **`tags`** (`List[str]`): Advisory keywords for filtering.
* **`metadata`** (`Dict[str, Any]`): Arbitrary advisory key-values.

---

## Domain Descriptors

### 1. ToolDescriptor
Exposes low-level parameters and safety restrictions:
- `capabilities`: Required platform capabilities (e.g. `filesystem`, `network`).
- `safety`: `SafetyDeclaration` object (read-only, destructive, confirmations, locks).
- `estimated_latency_ms`: Estimated run latency.
- `resource_cost`: Run resource cost tier (`low`, `medium`, `high`).
- `input_schema` / `output_schema`: JSON schemas.
- `examples`: Usage payload examples.

### 2. SkillDescriptor
Describes composite/orchestrated flows:
- `input_schema` / `output_schema`: JSON schemas.
- `capabilities`: Required platform capabilities list.
- `execution_characteristics`: latency, resource cost, and blocking flags.
- `requires_context`: Boolean flag indicating if Context Engine context package is required.
- `examples`: Composed payload examples.

### 3. ConversationDescriptor
Describes client communication gateway capabilities:
- `supported_modes`: Supported modes (e.g. `direct`, `planning`).
- `supports_context`: Flag indicating context injection support.
- `supports_planning`: Flag indicating goal planner compilation support.
- `supports_streaming`: Streaming responses support flag.
- `supports_models`: List of supported LLM backend models.

### 4. ProviderDescriptor
Describes data sync and ingestion modules:
- `provider_type`: Ingestion type identifier (e.g. `markdown`, `youtube`).
- `supported_formats`: Supported file extensions or content schemas.

### 5. PromptDescriptor
Exposes metadata of orchestrating prompts without exposing the raw template body:
- `template_identifier`: Stable lookup template key.
- `strategy_name`: Prompt orchestration strategy (e.g. `few_shot`, `cot`).
- `input_variables`: List of variables expected by the template string.

### 6. ModelDescriptor
Describes offline or online AI models:
- `model_type`: Model target type (e.g. `local_llm`, `embedding`, `rerank`).
- `context_length`: Token window context length.
- `publisher`: Model publishing entity.

---

## DescriptorProvider Protocol

Any component exposing self-describing descriptors satisfies the `DescriptorProvider` structural Protocol:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class DescriptorProvider(Protocol):
    def get_descriptor(self) -> BaseDescriptor:
        """Returns the stable, self-describing metadata descriptor for the component."""
        ...
```
This enables decoupled runtime registering to registries.
