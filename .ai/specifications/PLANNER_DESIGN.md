---
Category: Specification
Status: Approved
Dependencies: [specifications/SKILLS_DESIGN.md, specifications/TOOLS_DESIGN.md]
Source-of-truth: True
---

# Planner Architecture Design — DeepCore Intelligence Layer

Version: v0.1  
Status: Architectural Design Proposal  
Role: Reusable, deterministic coordination engine  

---

## 1. Philosophy and Boundaries

The **Planner** is the deterministic orchestrator of the DeepCore Intelligence Layer. It sits as an operational gateway between the **Conversation/API Layer** (which initiates goals) and the **Execution Layer** (which implements capabilities).

### Core Boundaries

```
   Conversation / UI
          ↓
       Planner (Deterministic Orchestration & State)
          │
          ▼
   Execution Handlers
   ┌──────┴──────┐
   ▼             ▼
Skills      Context Skill
                 │
                 ▼
           Context Engine
```

To maintain architectural integrity, the Planner must strictly adhere to the following rules:

1. **No LLM or Reasoning Internals**: The Planner does not execute LLMs, call reasoning models, or generate natural language responses. It parses a plan (which may be provided by a reasoning model or user input), compiles it into an executable graph, and drives execution.
2. **Infrastructure-Agnostic Boundaries**: The Planner has no direct dependency on the Context Engine. It does not import or directly call the Context Engine; instead, any context retrieval occurs by invoking a Context Skill or dedicated execution handler.
3. **No Direct Tool Execution**: The Planner never executes tools (e.g. databases, file writers, terminal commands) directly. It only invokes registered execution handlers with structured inputs.
4. **Deterministic State Machine**: Plan execution, step transitions, retry logic, and input-output mapping must be 100% deterministic and trace-verified.
5. **Resiliency and Checkpointing**: The Planner persists execution state at the boundaries of every step. If a process is interrupted (e.g., app shutdown or local service restart), it can safely resume.

---

## 2. Contracts and Data Models

The Planner treats plans as structured Directed Acyclic Graphs (DAGs) with explicit inputs, outputs, conditions, and retry policies.

To prevent tight coupling, steps refer to a generic `handler_name` (instead of being hardcoded to a specific Skill). This allows future execution of Skills, Workflows, Macros, or Nested Plans without changing contracts.

```json
{
  "plan_id": "plan_7f1a9b",
  "goal": "Sync Markdown vault and extract concepts",
  "status": "executing",
  "steps": [
    {
      "step_id": "sync_vault",
      "handler_name": "vault_sync_provider",
      "inputs": {
        "vault_path": "/Users/user/Notes"
      },
      "status": "completed",
      "outputs": {
        "files_synced": 42
      },
      "artifacts": []
    },
    {
      "step_id": "extract_concepts",
      "handler_name": "concept_extractor",
      "inputs": {
        "min_confidence": 0.8
      },
      "status": "pending",
      "conditions": [
        {
          "expression": "steps.sync_vault.outputs.files_synced > 0"
        }
      ],
      "artifacts": []
    }
  ],
  "timeline": [],
  "created_at": "2026-07-10T22:37:00Z",
  "updated_at": "2026-07-10T22:37:00Z"
}
```

### Schema Definitions (Pydantic Models)

These models define the internal contracts of the Planner:

```python
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class PlanStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

class RetryPolicy(BaseModel):
    max_attempts: int = 3
    backoff_seconds: float = 1.0
    exponential: bool = True

class StepCondition(BaseModel):
    """
    Defines a deterministic condition for execution.
    Example: expression="steps.step_1.outputs.result_code == 0"
    """
    expression: str

class ExecutionArtifact(BaseModel):
    """
    Structured artifacts generated during step execution.
    Artifacts are distinct from scalar outputs (e.g. ContextPackage, reports).
    """
    artifact_id: str
    name: str
    artifact_type: str  # "ContextPackage", "Report", "Image", "Graph", etc.
    location_uri: str   # Location in storage (e.g. file:///... or db://...)
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TimelineEvent(BaseModel):
    """
    Structured timeline event for auditing, replay, UI state, and tracking.
    """
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str  # "step_started", "step_retry", "step_finished", "plan_cancelled"
    step_id: Optional[str] = None
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)

class ExecutionStep(BaseModel):
    step_id: str
    handler_name: str  # Refers to generic skill, workflow, macro, or nested plan executor
    description: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Optional[Dict[str, Any]] = None
    artifacts: List[ExecutionArtifact] = Field(default_factory=list)  # Reserved for rich documents/files
    status: StepStatus = StepStatus.PENDING
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    conditions: List[StepCondition] = Field(default_factory=list)
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

class ExecutionPlan(BaseModel):
    plan_id: str
    goal: str
    origin: str  # "assistant", "planner", "research_skill", "user"
    status: PlanStatus = PlanStatus.PENDING
    steps: List[ExecutionStep]
    timeline: List[TimelineEvent] = Field(default_factory=list)  # Reserved for audit logs/history
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
```

---

## 3. Platform APIs

The Planner is exposed as a platform service via the following API endpoints:

### `POST /api/planner/plans`
Creates a new `ExecutionPlan` structure. It maps a high-level goal and request origin into a structured set of steps.
- **Request Body**:
  ```json
  {
    "goal": "string",
    "origin": "string",
    "trigger_object_uuid": "string (optional)",
    "steps": []
  }
  ```
- **Returns**: `ExecutionPlan`

### `POST /api/planner/plans/{plan_id}/execute`
Begins or resumes execution of an existing plan.
- **Returns**: `ExecutionPlan` (running state)

### `GET /api/planner/plans/{plan_id}`
Retrieves the current execution progress, logs, and outputs of a plan.
- **Returns**: `ExecutionPlan`

### `POST /api/planner/plans/{plan_id}/cancel`
Gracefully interrupts a running plan, marking the current step as failed/cancelled and preventing future steps from running.
- **Returns**: `ExecutionPlan`

---

## 4. Execution Lifecycle and State Engine

The execution lifecycle of a plan runs through a deterministic loop:

```
[Create Plan] ──► [Validate Bindings] ──► [Evaluate Step Conditions]
                                                     │
                                            ┌────────┴────────┐
                                            ▼ (Met)           ▼ (Not Met)
                                      [Run Handler]      [Skip Step]
                                            │                 │
                                    ┌───────┴───────┐         │
                                    ▼ (Success)     ▼ (Fail)  │
                             [Save Outputs]    [Retry/Fail]   │
                                    │               │         │
                                    └───────┬───────┘         │
                                            ▼                 ▼
                                    [Next Step or Finish Plan]
```

### Detailed Lifecycle Phases

1. **Resolution & Validation**:
   - The Planner matches every step's `handler_name` against the registered executors in the Execution Registry.
   - It checks variable interpolation paths (e.g. `{{steps.prev.outputs.x}}`) to ensure referenced data flows exist in upstream steps.
2. **Step Condition Evaluation**:
   - Before a step is marked `RUNNING`, its `conditions` are evaluated.
   - If conditions fail, the step changes directly to `SKIPPED`.
3. **Execution Execution**:
   - The status is set to `RUNNING`, and `started_at` is timestamped.
   - The Planner executes the designated handler (which can invoke a Skill, execute a sub-workflow, or recursively run a **Nested Plan** if the handler is designated as a nested executor).
4. **Retry Handling**:
   - If the handler raises an exception or returns a failure indicator, the Planner retries based on the `RetryPolicy`.
   - Once max attempts are exhausted, the step transitions to `FAILED`, halting subsequent dependent branches unless fallback paths are explicitly mapped.
5. **Output & Artifact Binding**:
   - Upon successful step completion, output variables are saved into `outputs`, and generated artifacts are registered in `artifacts`.
   - Variable interpolation dynamically feeds outputs into the inputs of downstream steps.

---

## 5. Verification Strategy

The Planner's deterministic behavior requires robust testing strategies to guarantee reliability under failure states.

### Simulated / Mock Handler Runner
Tests must verify state transitions without calling live local system tools. We will introduce a `MockHandlerRegistry` registering simulated behaviors:
- **InstantSuccessHandler**: Simulates an immediate return value.
- **RetryFlakyHandler**: Fails `N` times before succeeding.
- **AlwaysFailHandler**: Reaches max retries to test failure transitions.
- **BranchingHandler**: Outputs true/false variables to verify conditional evaluation of downstream steps.

### Planned Unit Tests
- `test_plan_compilation_and_validation`: Verifies syntax validation of variable bindings.
- `test_condition_evaluation`: Confirms expression evaluation skips steps correctly.
- `test_retry_and_backoff_timing`: Measures that retries respect wait/exponential periods.
- `test_checkpoint_and_resume`: Simulates engine crash midway and checks that finished steps are skipped during re-run.
