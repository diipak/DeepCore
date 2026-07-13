---
Category: Design
Status: Stable
Dependencies: [architecture/ARCHITECTURE.md]
Source-of-truth: True
---

# Tools Architecture Design — DeepCore Intelligence Layer

Version: v0.1  
Status: Architectural Design Proposal  
Role: Deterministic execution primitives  

---

## 1. Philosophy

### What is a Tool?
A **Tool** is the smallest executable primitive in DeepCore. It represents a single, atomic, and deterministic utility that interfaces directly with host OS services, file systems, databases, networks, or hardware. 

### Why do Tools exist?
Tools exist to isolate low-level operations from high-level reasoning and coordination. They implement the concrete execution details (e.g. running a shell command, writing a byte array to disk, querying an sqlite database, or firing an API request). 

### Why the Planner never executes Tools directly
The **Planner** coordinates high-level, multi-step execution graphs (`ExecutionPlan`). If the Planner executed Tools directly:
1. It would need to understand the minutiae of every technical interaction (e.g. formatting a curl request or checking directory permissions).
2. It would lose the capability to bundle interactions into logical units of capabilities (which is the job of **Skills**).
3. Any minor technical change in a tool interface would require updating the Planner's goal parsing and execution state engine.

### Why Skills encapsulate Tools
A **Skill** provides a functional capability to the Planner. It holds validation logic, orchestrates the sequence of operations, binds context packages, and formats output results. It uses **Tools** as its mechanical muscles to interact with the environment. For example:
- A `VaultSyncSkill` handles the business logic of verifying note locations, matching local database records, and resolving renames.
- It encapsulates tools like the `FileReaderTool` (to read files), `GitCommitTool` (to commit notes), and `RegistryWriteTool` (to update DB tables).

### Core Relationship Chain
The data and execution flow operates through a strict hierarchical structure:

```
   Conversation (User input layer)
        ↓
    Planner (Orchestrates ExecutionPlan steps)
        ↓
     Skills (Coordinates business logic, inputs, & context)
        ↓
      Tools (Executes atomic, low-level primitives)
        ↓
    Providers (Normalizes raw external source schemas)
        ↓
    Registry (Exposes universal object references)
        ↓
     Sources (Represents raw documents, notes, & APIs)
```

---

## 2. Architectural Boundaries

A Tool must act as a stateless executor, isolated from the platform's macro-decision layers.

### Operational Boundaries

#### A Tool MAY:
- **Receive Structured Requests**: Parse and execute structured arguments.
- **Validate Inputs**: Ensure inputs conform to Pydantic schemas.
- **Access Platform Services**: Fetch configurations or check system capabilities.
- **Call Providers**: Invoke provider normalization logic.
- **Access Registry Services**: Query or update universal object tables.
- **Access Integrations**: Execute commands against external services or local APIs.
- **Return Structured Outputs**: Package execution outputs cleanly.

#### A Tool MUST NEVER:
- **Perform Planning**: A Tool is blind to the larger execution plan and overall goal.
- **Call the Planner**: It cannot initiate or modify execution graphs.
- **Invoke Skills**: Downward calls (Tools calling Skills) are strictly prohibited to prevent layer violations.
- **Call other Tools directly**: Tools must remain independent and isolated. (The only exception is the reserved *Composite Tools* architecture).
- **Generate Prompts**: A Tool prepares structural data, never prompt templates.
- **Communicate with LLMs**: It is model-agnostic and has no AI framework references.
- **Communicate with the UI**: It cannot post directly to sockets, logs, or UI views.
- **Maintain Conversation State**: It is stateless and does not track session logs.

---

## 3. Tool Classification

To ensure long-term architectural stability, Tools are classified by their *architectural responsibilities* rather than current implementation examples. This taxonomy naturally accommodates future capabilities (e.g. local OS services, robotics, or cloud providers) without requiring redesign:

| Category | Responsibility | Future Accommodation |
|---|---|---|
| **I/O Operations** (`ReadWrite`) | Performs raw reads and writes against physical storage. | Filesystem access, database reads, object storage writes, local document parsing. |
| **Search & Index** (`Query`) | Executes indexes, parses registry metadata, and queries database references. | SQLite table queries, full-text index lookups, similarity searches. |
| **Integrations** (`Connectors`) | Bridges DeepCore to external services, APIs, and client ecosystems. | Calendar, finance trackers, email, local system applications, smart home protocols. |
| **System Services** (`OS`) | Interacts with the host operating system, processes, and local hardware. | Local OS notification dispatch, process checks, system telemetry, memory stats. |
| **Perceptual & Vision** (`Perception`) | Interacts with camera, voice, audio, or physical sensors. | Vision parsing, speech-to-text, spatial mapping, local camera state. |

### Reasoning behind the taxonomy:
- **I/O vs Search**: Reading/writing raw files is structurally different from searching structured indices or database relations. This separation keeps storage tools clean.
- **Integrations vs OS**: OS tools deal with local host-system resources (which are highly restricted and local-first), while Integrations deal with external web services and APIs (which require credentials and handle network-specific errors).

---

## 4. Tool Contracts

Every Tool conforms to strict contracts modeled using Pydantic:

```python
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ToolStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    INVALID_INPUT = "invalid_input"
    TIMEOUT = "timeout"

class ToolArtifact(BaseModel):
    """
    Rich artifact output from Tool execution (e.g. temporary files, parsed output buffers).
    """
    artifact_id: str
    name: str
    artifact_type: str
    uri: str
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolDiagnostics(BaseModel):
    """
    Diagnostic traces for performance profiling, debugging, and tracing.
    """
    execution_time_ms: float
    system_resources_used: Dict[str, Any] = Field(default_factory=dict)  # e.g., memory, handles
    errors_encountered: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class ToolRequest(BaseModel):
    request_id: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: Optional[float] = 10.0

class ToolResult(BaseModel):
    request_id: str
    status: ToolStatus
    outputs: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[ToolArtifact] = Field(default_factory=list)
    diagnostics: ToolDiagnostics
    error_message: Optional[str] = None
```

---

## 5. Tool Descriptor and Safety Model

Every Tool exposes a static descriptor that makes the Tool layer self-describing for future planning models, automated documentation, and UI discovery.

### Safety Model Declarations
The safety model exposes metadata declarations describing execution characteristics. These are declaration properties rather than runtime enforcement mechanisms:

```python
class ToolCapability(str, Enum):
    FILESYSTEM = "filesystem"
    NETWORK = "network"
    REGISTRY = "registry"
    OS_SERVICE = "os_service"
    LOCAL_DEVICE = "local_device"

class SafetyDeclaration(BaseModel):
    safe: bool = True                    # Is it read-only and free from side effects?
    destructive: bool = False             # Does it modify, overwrite, or delete data?
    requires_confirmation: bool = False   # Should the UI prompt the user before execution?
    requires_network: bool = False        # Does it connect to external network interfaces?
    requires_local_resources: bool = False # Does it lock local devices, GPUs, or file paths?

class ToolDescriptor(BaseModel):
    name: str
    description: str
    category: str  # "ReadWrite", "Query", "Connectors", "OS", "Perception"
    capabilities: List[ToolCapability] = Field(default_factory=list)
    safety: SafetyDeclaration = Field(default_factory=SafetyDeclaration)
    estimated_latency_ms: float = 50.0
    resource_cost: str = "low"  # "low", "medium", "high"
    input_schema: Dict[str, Any]  # JSON schema representation
    output_schema: Dict[str, Any] # JSON schema representation
    examples: List[Dict[str, Any]] = Field(default_factory=dict)
```

---

## 6. Execution Lifecycle

A Tool owns deterministic execution only. It has no knowledge of retry routing, which is handled at the Skill or Planner levels:

```
[Request Received] ──► [Input Validation] ──► [Primitive Execution] ──► [Compile Trace] ──► [Return Result]
```

1. **Input Validation**: Check input parameters against the Tool's defined `input_schema`. If invalid, return `ToolStatus.INVALID_INPUT` immediately.
2. **Primitive Execution**: Run the raw operation (e.g. read, write, call). Respect `timeout_seconds`. If a timeout is reached, raise a timeout exception and return `ToolStatus.TIMEOUT`.
3. **Compile Trace**: Gather run metrics (latency, resource usage) and format output data structures and artifacts.
4. **Result Return**: Return the completed `ToolResult`.

---

## 7. Registration and Plugin Architecture

The platform resolves Tools via a **Tool Registry**. Skills look up Tool handlers through this registry rather than importing implementations, ensuring loose coupling and permitting third-party extensions.

### Base Tool Class
```python
from abc import ABC, abstractmethod
from typing import Type

class BaseTool(ABC):
    name: str
    description: str
    category: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]
    capabilities: List[ToolCapability] = []
    safety: SafetyDeclaration = SafetyDeclaration()
    estimated_latency_ms: float = 50.0
    resource_cost: str = "low"
    examples: List[Dict[str, Any]] = []

    def get_descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            name=self.name,
            description=self.description,
            category=self.category,
            capabilities=self.capabilities,
            safety=self.safety,
            estimated_latency_ms=self.estimated_latency_ms,
            resource_cost=self.resource_cost,
            input_schema=self.input_schema.model_json_schema(),
            output_schema=self.output_schema.model_json_schema(),
            examples=self.examples
        )

    @abstractmethod
    def execute(self, request: ToolRequest) -> ToolResult:
        """Run the tool's deterministic execution primitive."""
        pass
```

### Tool Registry
```python
class ToolRegistry:
    def __init__(self):
        self._registry: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._registry:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._registry[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._registry.get(name)

    def list_tools(self) -> List[ToolDescriptor]:
        return [tool.get_descriptor() for tool in self._registry.values()]
```

---

## 8. Composite Tools (Reserved)

The architecture reserves support for **Composite Tools**. A Composite Tool internally orchestrates multiple Tools (e.g. reading a template, fetching data, and writing a file) while presenting a single Tool interface to the Skills layer:

- Composite Tools are useful for standardizing multi-step low-level routines (e.g., backup and restore routines) that do not require logical branching or context evaluation from Skills.
- A Composite Tool has its own internal Registry reference and executes its children sequentially, stopping and failing if any child fails.

---

## 9. Verification Strategy

We will use mock tools to verify execution correctness, registry binding, and safety declaration propagation:

- **MockDiskReadTool**: Implements a simulated file reader with a 10ms estimated latency and `SafetyDeclaration(safe=True)`.
- **MockDiskWriteTool**: Implements a simulated file writer with `SafetyDeclaration(safe=False, destructive=True, requires_confirmation=True)`.
- **MockTimeoutTool**: Simulates a slow socket call that hangs beyond the request timeout, verifying that the lifecycle transitions to `ToolStatus.TIMEOUT` correctly.


## 10. Reserved Future Extensions

The following capabilities are intentionally reserved for future runtime evolution.
They are not part of the current implementation.

- ExecutionContext propagation
- Tool health reporting
- Event streaming
- Progressive outputs
- Plugin versioning
