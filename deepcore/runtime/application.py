from typing import Dict, Any, List, Callable
from deepcore.config import Settings
from deepcore.runtime.descriptors import CapabilityRegistry, CapabilityDiscoveryService
from deepcore.runtime.tools.registry import ToolRegistry
from deepcore.runtime.skills.registry import SkillRegistry
from deepcore.runtime.execution.registry import ExecutionRegistry
from deepcore.runtime.tools.runtime import ToolRuntime
from deepcore.runtime.skills.runtime import SkillRuntime
from deepcore.runtime.execution.runtime import ExecutionRuntime
from deepcore.runtime.planner.runtime import PlannerRuntime
from deepcore.runtime.conversation.runtime import ConversationRuntime
from deepcore.intelligence import ContextEngine

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
        conversation_runtime: ConversationRuntime,
    ):
        self.config = config
        
        # Internal reference tracking
        self._capability_registry = capability_registry
        self._tool_registry = tool_registry
        self._skill_registry = skill_registry
        self._execution_registry = execution_registry
        self._tool_runtime = tool_runtime
        self._skill_runtime = skill_runtime
        self._execution_runtime = execution_runtime
        self._planner_runtime = planner_runtime
        
        # Service boundary exposures
        self.capabilities_service = discovery_service
        self.conversation_service = conversation_runtime
        
        self.status = "created"
        self._shutdown_hooks: List[Callable[[], None]] = []

    def get_context_service(self, db) -> ContextEngine:
        """Exposes the ContextEngine service dynamically bound to a database session."""
        return ContextEngine(db)

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
        from deepcore.runtime.health import KernelHealthReport
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
