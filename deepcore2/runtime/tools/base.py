from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional, Type
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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

from deepcore2.runtime.descriptors import BaseDescriptor, DescriptorCategory

class ToolDescriptor(BaseDescriptor):
    capabilities: List[ToolCapability] = Field(default_factory=list)
    safety: SafetyDeclaration = Field(default_factory=SafetyDeclaration)
    estimated_latency_ms: float = 50.0
    resource_cost: str = "low"  # "low", "medium", "high"
    input_schema: Dict[str, Any]  # JSON schema representation
    output_schema: Dict[str, Any] # JSON schema representation
    examples: List[Dict[str, Any]] = Field(default_factory=list)

class BaseTool(ABC):
    id: Optional[str] = None
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
            id=self.id or self.name,
            name=self.name,
            description=self.description,
            category=DescriptorCategory.TOOL,
            capabilities=self.capabilities,
            safety=self.safety,
            estimated_latency_ms=self.estimated_latency_ms,
            resource_cost=self.resource_cost,
            input_schema=self.input_schema.model_json_schema(),
            output_schema=self.output_schema.model_json_schema(),
            examples=self.examples,
            metadata={"tool_category": self.category}
        )

    @abstractmethod
    def execute(self, request: ToolRequest) -> ToolResult:
        """Run the tool's deterministic execution primitive."""
        pass
