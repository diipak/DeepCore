---
Category: Design
Status: Stable
Dependencies: [design/TOOLS_DESIGN.md]
Source-of-truth: True
---

# Skills Architecture Design — DeepCore Intelligence Layer

Version: v0.1  
Status: Architectural Design Proposal  
Role: Reusable execution capabilities  

---

## 1. Philosophy

### What is a Skill?
A **Skill** is a self-contained, validated execution block that implements a specific capability within DeepCore. It represents a single unit of action—such as searching a directory, syncing a git repository, indexing document contents, or querying transaction statistics. 

### What problem does it solve?
Directly exposing raw **Tools** (like file systems, sqlite engines, web search clients, or git commands) to planners or LLMs creates several issues:
1. **Lack of Type Safety**: Raw tools usually accept and return unstructured inputs/outputs.
2. **Security & Permission Risks**: A planner might execute unsafe operations if it has direct tool access.
3. **Bloated Logic**: Complex workflows (e.g., syncing a folder, filtering markdown files, and fingerprinting them) would have to be handled by the orchestrator.

Skills solve this by wrapping tools in a highly structured, type-safe, and validated boundary.

### Why Planner Orchestrates Skills Instead of Tools
The **Planner** is a coordination layer, not an implementation layer. It does not need to know the command-line flags of `git`, the connection details of SQLite, or the formatting details of a YouTube transcript. 

By orchestrating Skills:
- The Planner remains completely insulated from underlying tool changes.
- The execution layer remains modular; a Skill can change how it talks to a Tool without breaking the Planner's execution plan.
- The security boundary is enforced at the Skill interface level.

---

## 2. Architectural Boundaries

A Skill must remain pure, deterministic in logic routing, and isolated from downstream generation layers.

```
   Planner / Executor
          │
          ▼  (SkillRequest)
     ┌─────────┐
     │  SKILL  │ ◄─── (Validates Inputs & Capabilities)
     └────┬────┘
          ├───────────────┬───────────────┐
          ▼               ▼               ▼
     Tool (Disk)     Tool (Network)    Context Skill
          │               │               │
          └───────────────┼───────────────┘
                          ▼  (SkillResult)
                  Composer / Formatter
```

### Operational Constraints

#### A Skill MUST:
- **Validate Inputs**: Reject requests immediately if they violate Pydantic schemas.
- **Orchestrate Tools**: Coordinate one or more low-level tools (e.g. read file, query API).
- **Invoke Context Skills**: Pull additional evidence from the Context Engine if necessary by invoking designated Context Skills.
- **Compose Results**: Assemble raw tool responses into a structured dictionary and register produced files/documents as formal artifacts.

#### A Skill MUST NEVER:
- **Call LLMs Directly**: A Skill should never execute a model or invoke local/cloud inference.
- **Generate Natural Language or Prompts**: It prepares structural data only.
- **Modify Planner State**: It is unaware of the macro plan or adjacent step statuses.
- **Communicate with the UI**: It has no direct connection to the frontend or notification socket.
- **Access Persistence Directly**: Database transactions (aside from registry lookups) should be owned by Registry services, not SQL queries written directly in the Skill.
- **Maintain Conversation State**: It is stateless and does not track historical conversation context.

---

## 3. Skill Contracts

Every Skill implements a strict public interface defined by the following Pydantic models. Notice that the `SkillRequest` does not contain a `skill_name` since the Registry resolves the target Skill prior to invocation; the request is generic and transports only execution payload data.

```python
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class SkillStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    INVALID_INPUT = "invalid_input"

class SkillCapability(str, Enum):
    """
    Declared capabilities required by a Skill during execution.
    This enables static validation and permission matching before runtime.
    """
    FILESYSTEM = "filesystem"
    NETWORK = "network"
    REGISTRY = "registry"
    CONTEXT = "context"
    CALENDAR = "calendar"
    LOCAL_MODEL = "local_model"

class ExecutionCharacteristics(BaseModel):
    """
    Metadata describing estimated execution characteristics for scheduling and optimization.
    """
    estimated_latency_ms: float = 100.0
    resource_cost: str = "low"  # "low", "medium", "high"
    blocking: bool = True

class SkillArtifact(BaseModel):
    """
    Rich outputs generated during skill execution (e.g. ContextPackage, generated reports, files).
    """
    artifact_id: str
    name: str
    artifact_type: str  # "ContextPackage", "MarkdownDocument", "CSVReport", etc.
    uri: str           # Absolute path or internal schema URI
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SkillDiagnostics(BaseModel):
    """
    Audit metrics and details gathered during execution.
    """
    execution_time_ms: float
    steps_run: List[str] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)  # Diagnostic record of low-level calls
    warnings: List[str] = Field(default_factory=list)

class SkillRequest(BaseModel):
    request_id: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    context_package_uuid: Optional[str] = None
    call_stack: List[str] = Field(default_factory=list)  # Used for tracing and circular loop prevention

class SkillResult(BaseModel):
    request_id: str
    status: SkillStatus
    outputs: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[SkillArtifact] = Field(default_factory=list)
    diagnostics: SkillDiagnostics
    error_message: Optional[str] = None
```

---

## 4. Execution Lifecycle

A Skill's internal execution runs through a deterministic lifecycle:

```
[Request Received] ──► [Schema Validation] ──► [Tool Orchestration] ──► [Composition] ──► [Return Result]
```

### Lifecycle Phases
1. **Input Validation**: Check input parameters against the Skill’s defined `input_schema`. If validation fails, return `SkillStatus.INVALID_INPUT` immediately.
2. **Tool Orchestration**: Call the required low-level tools. If a tool raises an error, handle it locally (e.g., transient network retries).
3. **Result Composition**: Gather the output fields, register any generated files as `SkillArtifact` records, and compile the diagnostic trace.
4. **Result Return**: Return the structured `SkillResult` to the caller.

### Retry Ownership Boundaries
- **Transient Tool Retries (Skill Level)**: The Skill is responsible for resolving transient tool errors (e.g. standard HTTP backoff when calling a remote web search, retrying an sqlite lock).
- **Logical Flow Retries (Planner Level)**: The Planner owns step-level retries. If a Skill returns `SkillStatus.FAILURE` (e.g. because credentials expired, a path is completely missing, or a structural error occurred), the Planner decides whether to execute a macro retry, branch to a fallback plan, or fail the execution step.

---

## 5. Registration and Skill Descriptors

To keep the platform modular, the Planner resolves Skills through a central **Skill Registry** rather than importing individual Skill implementations directly.

### Skill Descriptor
The Registry exposes a `SkillDescriptor` schema for each registered skill. This serves to make the platform self-describing for future planners, documentation generators, and user interfaces.

```python
class SkillDescriptor(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]  # JSON schema representation
    output_schema: Dict[str, Any] # JSON schema representation
    capabilities: List[SkillCapability] = Field(default_factory=list)
    execution_characteristics: ExecutionCharacteristics = Field(default_factory=ExecutionCharacteristics)
    requires_context: bool = False  # Declares if ContextPackage is required prior to execution
    examples: List[Dict[str, Any]] = Field(default_factory=list)
```

### Base Skill Class
Every Skill inherits from the abstract base class `BaseSkill`, declaring its capabilities, execution profile, and context requirements:

```python
from abc import ABC, abstractmethod
from typing import Type
from pydantic import BaseModel

class BaseSkill(ABC):
    name: str
    description: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]
    capabilities: List[SkillCapability] = []
    execution_characteristics: ExecutionCharacteristics = ExecutionCharacteristics()
    requires_context: bool = False  # Enables Planner to avoid running Context Engine if False
    examples: List[Dict[str, Any]] = []

    def get_descriptor(self) -> SkillDescriptor:
        return SkillDescriptor(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema.model_json_schema(),
            output_schema=self.output_schema.model_json_schema(),
            capabilities=self.capabilities,
            execution_characteristics=self.execution_characteristics,
            requires_context=self.requires_context,
            examples=self.examples
        )

    @abstractmethod
    def execute(self, request: SkillRequest) -> SkillResult:
        """Execute the skill deterministically."""
        pass
```

### Skill Registry
The Skill Registry handles mapping and instantiation:

```python
class SkillRegistry:
    def __init__(self):
        self._registry: Dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        if skill.name in self._registry:
            raise ValueError(f"Skill '{skill.name}' is already registered.")
        self._registry[skill.name] = skill

    def get(self, name: str) -> Optional[BaseSkill]:
        return self._registry.get(name)

    def get_descriptor(self, name: str) -> Optional[SkillDescriptor]:
        skill = self.get(name)
        return skill.get_descriptor() if skill else None

    def list_skills(self) -> List[SkillDescriptor]:
        return [skill.get_descriptor() for skill in self._registry.values()]
```

---

## 6. Composition and Recursion Safety

Skills may invoke other Skills by looking up their handlers in the `SkillRegistry` (e.g., a `VaultIndexerSkill` calling a `FileReadSkill`). To prevent infinite loops and circular executions:

1. **Call Stack Tracking**: Every `SkillRequest` contains a `call_stack` representing the ancestors of the current execution (e.g. `['vault_indexer', 'file_reader']`).
2. **Circular Execution Prevention**:
   - Before executing a child skill, the parent must verify the child's target name is not in the current `call_stack`.
   - If it is already in the stack, the execution registry throws a `RecursionError` and prevents execution.
3. **Max Execution Depth**: A global limit (e.g. max depth of 4) is enforced on the `call_stack` size.

```python
def check_recursion(request: SkillRequest, target_skill_name: str) -> None:
    if target_skill_name in request.call_stack:
        raise RecursionError(
            f"Circular skill execution detected: '{target_skill_name}' already exists in stack {request.call_stack}"
        )
    if len(request.call_stack) >= 4:
        raise RecursionError("Max skill execution depth exceeded (limit=4).")
```

---

## 7. Verification Strategy

We will use mock implementations of Skills to test validation, composition, and recursion safety without introducing disk/network dependencies:

- **MockFileReadSkill**: Simulates reading file contents from a dictionary-based mock filesystem. Declares `capabilities = [SkillCapability.FILESYSTEM]`.
- **MockContextLookupSkill**: Simulates pulling related concepts from a mock Context Engine. Declares `requires_context = True` and `capabilities = [SkillCapability.CONTEXT]`.
- **MockCircularSkill**: Intentionally attempts to call itself recursively to verify that the `call_stack` logic throws recursion and circular errors correctly.
