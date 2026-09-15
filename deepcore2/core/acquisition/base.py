from abc import ABC, abstractmethod
from enum import Enum
from typing import Generator, Dict, Any, Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class Provenance(BaseModel):
    """
    Explicit and immutable provenance metadata tracing the source origin
    of any ingested object in DeepCore.
    """
    connector_id: str = Field(..., description="Unique ID of the connector package")
    provider_id: str = Field(..., description="Type of provider, e.g., 'github'")
    source_system: str = Field(..., description="Source instance name, e.g., 'personal_github'")
    external_id: str = Field(..., description="Unique ID of the record in the external system")
    acquisition_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sync_run_id: str = Field(..., description="UUID of the coordinating SyncRun")

    model_config = ConfigDict(frozen=True)  # Enforce immutability


class HealthStatus(BaseModel):
    """
    Standardized payload for dynamic connector health reporting.
    """
    state: str = Field(..., description="State string: HEALTHY, DEGRADED, CRITICAL, UNAUTHORIZED")
    message: Optional[str] = None
    last_check_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Optional[Dict[str, Any]] = None


class SyncContext:
    """
    Runtime execution context containing configuration, credentials, cursor state,
    and platform logging/cancellation hooks passed to the connector for batch ingestion.
    """
    def __init__(
        self,
        workspace_id: int,
        source_id: int,
        config: Dict[str, Any],
        credentials: Dict[str, Any],
        cursor_state: Optional[Dict[str, Any]] = None,
        logger: Any = None
    ):
        self.workspace_id = workspace_id
        self.source_id = source_id
        self.config = config
        self.credentials = credentials
        self.cursor_state = cursor_state or {}
        self.logger = logger
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled


# ============================================================================
# Live Execution Models (Phase A - Connector SDK Evolution)
# ============================================================================

class ConnectorOperation(str, Enum):
    """
    Canonical operations supported across live connector interactions.
    Connectors map these operations internally to native provider APIs.
    """
    SEARCH = "search"
    READ = "read"
    LIST = "list"
    QUERY = "query"
    ACTION = "action"


class ExecutionContext(BaseModel):
    """
    Lightweight runtime context for live execution, decoupled from ingestion SyncContext.
    Carries configuration, credentials, and optional workspace context.
    """
    config: Dict[str, Any] = Field(default_factory=dict)
    credentials: Dict[str, Any] = Field(default_factory=dict)
    workspace_id: Optional[int] = None
    source_id: Optional[int] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ExecutionRequest(BaseModel):
    """
    Platform-level request model for live connector operations.
    Re-usable by planners, tools, skills, and connector interfaces.
    """
    operation: ConnectorOperation
    parameters: Dict[str, Any] = Field(default_factory=dict)
    context: ExecutionContext = Field(default_factory=ExecutionContext)
    pagination: Optional[Dict[str, Any]] = None
    limits: Optional[Dict[str, Any]] = None


class ExecutionResponse(BaseModel):
    """
    Platform-level response model returned by live connector operations.
    """
    results: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    continuation_token: Optional[str] = None
    diagnostics: Dict[str, Any] = Field(default_factory=dict)


class ConnectorCapabilities(BaseModel):
    """
    Structured descriptor defining operational and runtime capabilities of a connector.
    """
    supported_operations: List[ConnectorOperation] = Field(default_factory=list)
    requires_configuration: bool = True
    requires_permissions: bool = False
    supports_pagination: bool = False
    supports_streaming: bool = False
    supports_actions: bool = False
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Single Connector Abstract Base Class
# ============================================================================

class BaseConnector(ABC):
    """
    Technical Contract Interface for DeepCore Connectors.
    Supports both Batch Ingestion (discover, sync, watch) and Stateless Live Execution (capabilities, check_health, execute).
    """

    # --- Batch Ingestion Surface ---
    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> HealthStatus:
        """Validate authentication credentials and verify connectivity."""
        pass

    @abstractmethod
    def discover(self, ctx: SyncContext) -> Generator[Dict[str, Any], None, None]:
        """Scan and discover all raw objects from the external system (full sync)."""
        pass

    @abstractmethod
    def sync(self, ctx: SyncContext) -> Generator[Dict[str, Any], None, None]:
        """
        Perform an incremental sync run from the external source since the last cursor state.
        Modifies ctx.cursor_state in-place during iteration.
        """
        pass

    @abstractmethod
    def watch(self, ctx: SyncContext) -> Generator[Dict[str, Any], None, None]:
        """Subscribe to live source changes and yield raw updates."""
        pass

    @abstractmethod
    def health(self, ctx: SyncContext) -> HealthStatus:
        """Run batch ingestion diagnostic checks."""
        pass

    # --- Stateless Live Execution Surface (Phase A Evolution) ---
    def capabilities(self) -> ConnectorCapabilities:
        """
        Return structured capability metadata describing supported operations
        and runtime capabilities.
        """
        return ConnectorCapabilities(supported_operations=[])

    def check_health(self, context: Optional[ExecutionContext] = None) -> HealthStatus:
        """
        Perform a stateless live health check using execution context (decoupled from SyncContext).
        """
        return HealthStatus(state="HEALTHY", message="Connector operational.")

    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """
        Execute a stateless live operation against the external provider.
        """
        raise NotImplementedError(
            f"Live operation '{request.operation.value}' is not implemented by connector '{self.__class__.__name__}'."
        )


class BaseTranslator(ABC):
    """
    Pure Invariant Semantic Translator interface. Translators must be side-effect-free,
    performing only deterministic dictionary translation from external structures
    to standard RegistryObjectCreate models.
    """
    @abstractmethod
    def translate_object(self, raw_data: Dict[str, Any], provenance: Provenance) -> Dict[str, Any]:
        """
        Translate a raw object from the Semantic Contract to a RegistryObjectCreate dictionary schema.
        Must never perform DB, network, relationship queries, AI calls, or state updates.
        """
        pass
