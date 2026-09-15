from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional, Type
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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

from deepcore2.runtime.descriptors import BaseDescriptor, DescriptorCategory

class SkillDescriptor(BaseDescriptor):
    input_schema: Dict[str, Any]  # JSON schema representation
    output_schema: Dict[str, Any] # JSON schema representation
    capabilities: List[SkillCapability] = Field(default_factory=list)
    execution_characteristics: ExecutionCharacteristics = Field(default_factory=ExecutionCharacteristics)
    requires_context: bool = False  # Declares if ContextPackage is required prior to execution
    examples: List[Dict[str, Any]] = Field(default_factory=list)


class SkillRuntimeInterface(ABC):
    """
    Minimal interface capable of resolving and executing child handlers.
    Decouples BaseSkill from the concrete SkillRuntime implementation.
    """
    @abstractmethod
    def execute_skill(self, skill_name: str, request: SkillRequest) -> SkillResult:
        """Resolve and execute a child skill handler by name."""
        pass


class BaseSkill(ABC):
    id: Optional[str] = None
    name: str
    description: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]
    capabilities: List[SkillCapability] = []
    execution_characteristics: ExecutionCharacteristics = ExecutionCharacteristics()
    requires_context: bool = False
    examples: List[Dict[str, Any]] = []

    def get_descriptor(self) -> SkillDescriptor:
        return SkillDescriptor(
            id=self.id or self.name,
            name=self.name,
            description=self.description,
            category=DescriptorCategory.SKILL,
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
