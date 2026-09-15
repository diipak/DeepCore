from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    INVALID_INPUT = "invalid_input"
    TIMEOUT = "timeout"

class ExecutionArtifact(BaseModel):
    artifact_id: str
    name: str
    artifact_type: str
    uri: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExecutionDiagnostics(BaseModel):
    execution_time_ms: float
    steps_run: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class ExecutionRequest(BaseModel):
    request_id: str
    handler_name: str
    inputs: Dict[str, Any] = Field(default_factory=dict)

class ExecutionResult(BaseModel):
    request_id: str
    status: ExecutionStatus
    outputs: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[ExecutionArtifact] = Field(default_factory=list)
    diagnostics: ExecutionDiagnostics
    error_message: Optional[str] = None

class ExecutionDescriptor(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    capabilities: List[str] = Field(default_factory=list)
    examples: List[Dict[str, Any]] = Field(default_factory=list)
