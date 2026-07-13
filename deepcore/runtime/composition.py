import os
from typing import Optional
from sqlalchemy.orm import Session
from deepcore.config import Settings
from deepcore.storage.sqlite.db import engine, SessionLocal
from deepcore.storage.sqlite.models import run_migrations

from deepcore.runtime.descriptors import (
    CapabilityRegistry,
    CapabilityDiscoveryService,
    DescriptorCategory,
    ProviderDescriptor,
    ModelDescriptor,
    PromptDescriptor
)
from deepcore.runtime.descriptors.exceptions import (
    DuplicateDescriptorError,
    DescriptorValidationError
)
from deepcore.runtime.tools.registry import ToolRegistry, ExecutionRegistry as ToolExecRegistry
from deepcore.runtime.tools.runtime import ToolRuntime
from deepcore.runtime.skills.registry import SkillRegistry
from deepcore.runtime.skills.runtime import SkillRuntime
from deepcore.runtime.execution.registry import ExecutionRegistry
from deepcore.runtime.execution.runtime import ExecutionRuntime
from deepcore.runtime.planner.runtime import PlannerRuntime
from deepcore.runtime.conversation.runtime import ConversationRuntime
from deepcore.runtime.ingestion.runtime import IngestionRuntime
from deepcore.runtime.ingestion.callbacks import ContentIndexCallback
from deepcore.core.providers.markdown import MarkdownProvider
from deepcore.core.registry.service import RegistryService

from deepcore.runtime.stubs import (
    EchoTool,
    RegistrySearchMockTool,
    EchoSkill,
    RegistrySearchEchoSkill,
)
from deepcore.runtime.application import Application

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
        conversation_runtime = ConversationRuntime(planner_runtime)
        discovery_service = CapabilityDiscoveryService(capability_registry)

        # Ingestion Runtime construction
        ingestion_runtime = IngestionRuntime()
        ingestion_runtime.register_provider("markdown", MarkdownProvider)
        ingestion_runtime.register_callback(ContentIndexCallback())

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
            conversation_runtime=conversation_runtime,
            ingestion_runtime=ingestion_runtime
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
        # Register Tools
        echo_tool = EchoTool()
        search_tool = RegistrySearchMockTool()  # Uses db_session_ctx dynamically
        
        tool_registry.register(echo_tool)
        tool_registry.register(search_tool)
        
        for tool_desc in tool_registry.list_tools():
            capability_registry.register(tool_desc)

        # Register Skills
        tool_exec_reg = ToolExecRegistry(tool_registry)
        tool_runtime = ToolRuntime(tool_exec_reg)
        
        echo_skill = EchoSkill(tool_runtime)
        search_skill = RegistrySearchEchoSkill(tool_runtime)
        
        skill_registry.register(echo_skill)
        skill_registry.register(search_skill)
        
        for skill_desc in skill_registry.list_skills():
            capability_registry.register(skill_desc)

        # Register Executables
        execution_registry.register("echo_skill", echo_skill)
        execution_registry.register("registry_search_echo_skill", search_skill)

        # Runtimes and conversation setup
        skill_runtime_inst = SkillRuntime(skill_registry, tool_runtime)
        execution_runtime = ExecutionRuntime(execution_registry, skill_runtime_inst)
        planner_runtime = PlannerRuntime(execution_runtime)
        conversation_runtime = ConversationRuntime(planner_runtime)

        capability_registry.register(conversation_runtime.get_descriptor())

        # Static Providers, Models, Prompts
        capability_registry.register(ProviderDescriptor(
            id="markdown_provider",
            name="Markdown Sync",
            description="Sync local markdown vault directories",
            category=DescriptorCategory.PROVIDER,
            configurable=True,
            provider_type="markdown",
            supported_formats=[".md", ".markdown"]
        ))
        capability_registry.register(ProviderDescriptor(
            id="youtube_provider",
            name="YouTube Sync",
            description="Sync video metadata and transcript details",
            category=DescriptorCategory.PROVIDER,
            provider_type="youtube",
            supported_formats=["youtube.com", "youtu.be"]
        ))
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
            "markdown_provider",
            "youtube_provider",
            "ollama_llama3",
            "prompt_assistant_default",
            "conversation_runtime"
        ]
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
        from deepcore.config import settings
        bootstrap_application(settings)
    return _global_app
