import os
from typing import Optional
from sqlalchemy.orm import Session
from deepcore2.config import Settings
from deepcore2.storage.sqlite.db import engine, SessionLocal
from deepcore2.storage.sqlite.models import run_migrations

from deepcore2.runtime.descriptors import (
    CapabilityRegistry,
    CapabilityDiscoveryService,
    DescriptorCategory,
    ProviderDescriptor,
    ModelDescriptor,
    PromptDescriptor
)
from deepcore2.runtime.descriptors.exceptions import (
    DuplicateDescriptorError,
    DescriptorValidationError
)
from deepcore2.runtime.tools.registry import ToolRegistry, ExecutionRegistry as ToolExecRegistry
from deepcore2.runtime.tools.runtime import ToolRuntime
from deepcore2.runtime.skills.registry import SkillRegistry
from deepcore2.runtime.skills.runtime import SkillRuntime
from deepcore2.runtime.execution.registry import ExecutionRegistry
from deepcore2.runtime.execution.runtime import ExecutionRuntime
from deepcore2.runtime.planner.runtime import PlannerRuntime
from deepcore2.runtime.ingestion.runtime import IngestionRuntime
from deepcore2.runtime.processing.runtime import ProcessingRuntime
from deepcore2.runtime.processing.stages import ContentIndexStage, RelationshipStage, SignalStage
from deepcore2.core.providers.markdown import MarkdownProvider
from deepcore2.core.registry.service import RegistryService

from deepcore2.runtime.application import Application

class CompositionRoot:
    """
    Orchestrates the deterministic startup lifecycle: constructing registries,
    registering capability descriptors and custom executables, freezing metadata
    registries, wiring runtimes, and executing integrity validation.
    """
    def __init__(self, config: Settings):
        self.config = config

    def assemble(self) -> Application:
        """
        Executes the deterministic startup sequence. Returns a fully wired,
        validated, and active Application object.
        """
        # 1. Load & Validate Configuration
        self._validate_config()

        # 2. Run Database Migrations
        self._run_migrations()

        # 3. Construct Registries
        capability_registry = CapabilityRegistry()
        tool_registry = ToolRegistry()
        skill_registry = SkillRegistry()
        execution_registry = ExecutionRegistry()

        from deepcore2.core.acquisition.manager import AcquisitionManager
        acquisition_manager = AcquisitionManager()
        self.acquisition_manager = acquisition_manager

        # 4. Register Descriptors & Executables
        self._register_descriptors_and_executables(
            capability_registry,
            tool_registry,
            skill_registry,
            execution_registry
        )

        # 5. Freeze Metadata Registries (Operational Registries are left mutable)
        capability_registry.freeze()

        # 6. Construct Services & Wire Dependencies
        tool_exec_reg = ToolExecRegistry(tool_registry)
        tool_runtime = ToolRuntime(tool_exec_reg)
        skill_runtime_inst = SkillRuntime(skill_registry, tool_runtime)
        execution_runtime = ExecutionRuntime(execution_registry, skill_runtime_inst)
        planner_runtime = PlannerRuntime(execution_runtime)
        discovery_service = CapabilityDiscoveryService(capability_registry)

        # Ingestion & Processing Runtime construction
        from deepcore2.core.observability.service import ObservabilityService
        observability_service = ObservabilityService()

        processing_runtime = ProcessingRuntime(observability_service=observability_service)
        processing_runtime.register_stage(ContentIndexStage())
        processing_runtime.register_stage(RelationshipStage())
        processing_runtime.register_stage(SignalStage())

        ingestion_runtime = IngestionRuntime(processing_runtime)
        ingestion_runtime.register_provider("markdown", MarkdownProvider)

        from deepcore2.core.acquisition.preview import PreviewService
        preview_service = PreviewService()

        from deepcore2.core.acquisition.runtime import AcquisitionRuntime
        acquisition_runtime = AcquisitionRuntime()

        # 7. Perform Startup Integrity Validation
        self._validate_integrity(capability_registry, execution_registry)

        # 8. Construct Application Wrapper
        app = Application(
            config=self.config,
            capability_registry=capability_registry,
            discovery_service=discovery_service,
            tool_registry=tool_registry,
            skill_registry=skill_registry,
            execution_registry=execution_registry,
            tool_runtime=tool_runtime,
            skill_runtime=skill_runtime_inst,
            execution_runtime=execution_runtime,
            planner_runtime=planner_runtime,
            ingestion_runtime=ingestion_runtime,
            processing_runtime=processing_runtime,
            preview_service=preview_service,
            observability_service=observability_service,
            acquisition_manager=acquisition_manager,
            acquisition_runtime=acquisition_runtime
        )
        app.status = "ready"
        return app

    def _validate_config(self) -> None:
        if not self.config.DB_PATH:
            raise ValueError("Startup validation failed: Database path is empty in configuration.")
        
        # Test connection validity
        try:
            conn = engine.connect()
            conn.close()
        except Exception as e:
            raise ValueError(f"Startup validation failed: Database connection failure. Detail: {e}")

    def _run_migrations(self) -> None:
        try:
            run_migrations(engine)
        except Exception as e:
            raise ValueError(f"Startup validation failed: Migration execution error. Detail: {e}")

    def _register_descriptors_and_executables(
        self,
        capability_registry: CapabilityRegistry,
        tool_registry: ToolRegistry,
        skill_registry: SkillRegistry,
        execution_registry: ExecutionRegistry
    ) -> None:
        # Discover and register configured external MCP tools (Invariant #8)
        from deepcore2.runtime.tools.mcp_client import discover_and_register_mcp_tools
        discover_and_register_mcp_tools(tool_registry=tool_registry, config=self.config)

        # Tools registration (clean in 2.0 - no mock stubs)
        for tool_desc in tool_registry.list_tools():
            capability_registry.register(tool_desc)

        # Skills & Executables registration (clean in 2.0 - no mock stubs)
        tool_exec_reg = ToolExecRegistry(tool_registry)
        tool_runtime = ToolRuntime(tool_exec_reg)
        for skill_desc in skill_registry.list_skills():
            capability_registry.register(skill_desc)

        # Runtimes setup
        skill_runtime_inst = SkillRuntime(skill_registry, tool_runtime)
        execution_runtime = ExecutionRuntime(execution_registry, skill_runtime_inst)
        planner_runtime = PlannerRuntime(execution_runtime)

        # Discover and register all connector ProviderDescriptors dynamically via ConnectorLoader
        from deepcore2.core.acquisition.loader import ConnectorLoader
        connector_loader = ConnectorLoader(capability_registry, self.acquisition_manager)
        connector_loader.discover_and_register()

        capability_registry.register(ModelDescriptor(
            id="ollama_llama3",
            name="Llama 3 (8B)",
            description="Local offline inference engine powered by Ollama",
            category=DescriptorCategory.MODEL,
            model_type="local_llm",
            context_length=8192,
            publisher="meta-llama"
        ))
        capability_registry.register(PromptDescriptor(
            id="prompt_assistant_default",
            name="Default Assistant Prompt",
            description="Core guidance system prompt for assistant queries",
            category=DescriptorCategory.PROMPT,
            template_identifier="assistant_v1",
            strategy_name="cot",
            input_variables=["context_package", "user_query"]
        ))

    def _validate_integrity(
        self,
        capability_registry: CapabilityRegistry,
        execution_registry: ExecutionRegistry
    ) -> None:
        # Required descriptor verification
        required_ids = [
            "filesystem",
            "ollama_llama3",
            "prompt_assistant_default"
        ]
        for req_id in required_ids:
            try:
                capability_registry.get(req_id)
            except Exception:
                raise ValueError(f"Startup validation failed: Required capability descriptor '{req_id}' is missing.")
        for req_id in required_ids:
            try:
                capability_registry.get(req_id)
            except Exception:
                raise ValueError(f"Startup validation failed: Required capability descriptor '{req_id}' is missing.")

        # Registry alignment verification
        for exe_desc in execution_registry.list_descriptors():
            try:
                capability_registry.get(exe_desc.name)
            except Exception:
                raise ValueError(f"Startup validation failed: Registered execution handler '{exe_desc.name}' does not have a corresponding descriptor in CapabilityRegistry.")


_global_app: Optional[Application] = None

def bootstrap_application(config: Settings) -> Application:
    """Bootstraps and sets the global singleton application instance."""
    global _global_app
    root = CompositionRoot(config)
    _global_app = root.assemble()
    return _global_app

def get_application() -> Application:
    """Dependency provider or locator returning the active Application singleton."""
    global _global_app
    if _global_app is None:
        from deepcore2.config import settings
        bootstrap_application(settings)
    return _global_app
