from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Reuse ExecutionArtifact from execution runtime to avoid duplication
from deepcore2.runtime.execution.base import ExecutionArtifact

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

class TimelineEvent(BaseModel):
    """
    Structured timeline event for auditing, replay, UI state, and tracking.
    """
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Planner-specific Runtime Models
class PlannerStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"
    CANCELLED = "cancelled"
    INVALID_INPUT = "invalid_input"

class PlannerRequest(BaseModel):
    request_id: str
    plan: ExecutionPlan

class PlannerDiagnostics(BaseModel):
    execution_time_ms: float
    steps_executed: int = 0
    steps_skipped: int = 0
    steps_failed: int = 0

class PlannerResult(BaseModel):
    request_id: str
    status: PlannerStatus
    plan: ExecutionPlan
    diagnostics: PlannerDiagnostics
    error_message: Optional[str] = None

class VariableReference(BaseModel):
    """Normalized variable reference representing step.STEP_ID.outputs.FIELD or status."""
    step_id: str
    attribute: str  # "outputs" or "status"
    field_name: Optional[str] = None
