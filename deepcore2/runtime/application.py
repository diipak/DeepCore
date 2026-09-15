from typing import Dict, Any, List, Callable, Optional
from deepcore2.config import Settings
from deepcore2.runtime.descriptors import CapabilityRegistry, CapabilityDiscoveryService
from deepcore2.runtime.tools.registry import ToolRegistry
from deepcore2.runtime.skills.registry import SkillRegistry
from deepcore2.runtime.execution.registry import ExecutionRegistry
from deepcore2.runtime.tools.runtime import ToolRuntime
from deepcore2.runtime.skills.runtime import SkillRuntime
from deepcore2.runtime.execution.runtime import ExecutionRuntime
from deepcore2.runtime.planner.runtime import PlannerRuntime
from deepcore2.runtime.ingestion.runtime import IngestionRuntime
from deepcore2.runtime.processing.runtime import ProcessingRuntime
from deepcore2.intelligence import ContextEngine
from deepcore2.core.assistant.service import ConversationService

class Application:
    """
    Central Application object representing the running DeepCore instance.
    Serves as the service boundary for the DeepCore platform, exposing
    high-level services rather than leaking internal execution layers.
    """
    def __init__(
        self,
        config: Settings,
        capability_registry: CapabilityRegistry,
        discovery_service: CapabilityDiscoveryService,
        tool_registry: ToolRegistry,
        skill_registry: SkillRegistry,
        execution_registry: ExecutionRegistry,
        tool_runtime: ToolRuntime,
        skill_runtime: SkillRuntime,
        execution_runtime: ExecutionRuntime,
        planner_runtime: PlannerRuntime,
        ingestion_runtime: IngestionRuntime,
        processing_runtime: ProcessingRuntime,
        preview_service: Optional[Any] = None,
        observability_service: Optional[Any] = None,
        acquisition_manager: Optional[Any] = None,
        acquisition_runtime: Optional[Any] = None
    ):
        self.config = config
        
        # Reference tracking exposures
        self._capability_registry = capability_registry
        self._tool_registry = tool_registry
        self._skill_registry = skill_registry
        self._execution_registry = execution_registry
        self._tool_runtime = tool_runtime
        self._skill_runtime = skill_runtime
        self._execution_runtime = execution_runtime
        self._planner_runtime = planner_runtime

        self.capability_registry = capability_registry
        self.tool_registry = tool_registry
        self.skill_registry = skill_registry
        self.execution_registry = execution_registry
        self.tool_runtime = tool_runtime
        self.skill_runtime = skill_runtime
        self.execution_runtime = execution_runtime
        self.planner_runtime = planner_runtime
        
        # Service boundary exposures
        self.capabilities_service = discovery_service
        self.ingestion_service = ingestion_runtime
        self.processing_service = processing_runtime
        self.preview_service = preview_service
        self.observability_service = observability_service
        self.acquisition_manager = acquisition_manager
        self.acquisition_runtime = acquisition_runtime
        
        self.status = "created"
        self._shutdown_hooks: List[Callable[[], None]] = []

    def get_context_service(self, db, workspace_id: Optional[int] = None) -> ContextEngine:
        """Exposes the ContextEngine service dynamically bound to a database session."""
        return ContextEngine(db, workspace_id=workspace_id)


    def get_conversation_service(self, db, workspace_id: int = 1) -> ConversationService:
        """Exposes the ConversationService dynamically bound to a database session."""
        return ConversationService(
            db,
            workspace_id=workspace_id,
            tool_registry=self.tool_registry,
            tool_runtime=self.tool_runtime,
        )


    def register_shutdown_hook(self, hook: Callable[[], None]) -> None:
        """Registers a graceful shutdown hook callback to execute during teardown."""
        self._shutdown_hooks.append(hook)

    def shutdown(self) -> None:
        """Executes all registered shutdown hooks in order, transitioning application state to stopped."""
        self.status = "stopped"
        for hook in self._shutdown_hooks:
            try:
                hook()
            except Exception as e:
                # Log or print hook failure but continue executing remaining hooks
                print(f"DeepCore Shutdown Hook Error: {e}")

    @property
    def health_info(self) -> Dict[str, Any]:
        """
        Exposes dynamic, hierarchical health and diagnostics status
        across multiple expandable system domains.
        """
        from deepcore2.runtime.health import KernelHealthReport
        report = KernelHealthReport(
            tool_registry=self._tool_registry,
            skill_registry=self._skill_registry,
            execution_registry=self._execution_registry
        )
        kernel_summary = report.get_summary()

        # Build Domain-based Hierarchical Health Model
        return {
            "status": "ready" if self.status == "ready" else self.status,
            "domains": {
                "kernel": {
                    "status": "healthy",
                    "kernel_version": kernel_summary.get("kernel_version"),
                    "runtimes": kernel_summary.get("runtimes", {}),
                    "registered_tools_count": len(kernel_summary.get("registered_tools", [])),
                    "registered_skills_count": len(kernel_summary.get("registered_skills", [])),
                    "registered_executables_count": len(kernel_summary.get("registered_executables", []))
                },
                "registry": {
                    "status": "healthy",
                    "registry_frozen": getattr(self._capability_registry, "_frozen", False),
                    "registered_capabilities_count": len(self._capability_registry.list())
                },
                "providers": {
                    "status": "healthy",
                    "registered_providers": [
                        p.id for p in self._capability_registry.list() 
                        if getattr(p, "category", None) == "provider"
                    ]
                },
                "models": {
                    "status": "healthy",
                    "supported_models": [
                        m.id for m in self._capability_registry.list()
                        if getattr(m, "category", None) == "model"
                    ]
                },
                "synchronization": {
                    "status": "idle",
                    "last_sync_timestamp": None
                }
            }
        }
