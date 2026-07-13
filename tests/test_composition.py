import pytest
from deepcore.config import Settings
from deepcore.runtime.composition import CompositionRoot, bootstrap_application, get_application
from deepcore.runtime.application import Application
from deepcore.runtime.descriptors import (
    BaseDescriptor,
    DescriptorCategory,
    CapabilityRegistry,
    RegistryFrozenError
)
from deepcore.runtime.tools.registry import ToolRegistry
from deepcore.runtime.skills.registry import SkillRegistry
from deepcore.runtime.execution.registry import ExecutionRegistry
from deepcore.storage.sqlite.db import db_session_ctx

def test_deterministic_application_startup(db_session):
    # Setup test configuration
    settings = Settings()
    root = CompositionRoot(settings)
    app = root.assemble()

    assert isinstance(app, Application)
    assert app.status == "ready"
    
    # Check that services/gateways are wired
    assert app.capabilities_service is not None
    assert app.conversation_service is not None
    assert app.get_context_service(db_session) is not None

def test_registry_lifecycle_enforcement():
    settings = Settings()
    root = CompositionRoot(settings)
    app = root.assemble()

    # 1. CapabilityRegistry (Metadata Registry) must be frozen
    assert getattr(app._capability_registry, "_frozen", False) is True
    
    with pytest.raises(RegistryFrozenError):
        app._capability_registry.register(BaseDescriptor(
            id="temp_id",
            name="Temp",
            description="Temp description",
            category=DescriptorCategory.TOOL
        ))
        
    with pytest.raises(RegistryFrozenError):
        app._capability_registry.unregister("ollama_llama3")

    # 2. Operational Registries must remain mutable (not frozen)
    assert getattr(app._tool_registry, "_frozen", False) is False
    assert getattr(app._skill_registry, "_frozen", False) is False
    assert getattr(app._execution_registry, "_frozen", False) is False

def test_singleton_ownership():
    settings = Settings()
    root = CompositionRoot(settings)
    app1 = root.assemble()
    app2 = root.assemble()

    # Different assemblies produce different instances
    assert app1 is not app2

    # Runtimes within the same app are singletons wired together
    assert app1._tool_runtime is app1._skill_runtime.tool_runtime

def test_startup_validation_missing_required_descriptor():
    settings = Settings()
    root = CompositionRoot(settings)
    
    # We patch _register_descriptors_and_executables to omit a required descriptor
    orig_register = root._register_descriptors_and_executables
    
    def patched_register(cap_reg, tool_reg, skill_reg, exec_reg):
        orig_register(cap_reg, tool_reg, skill_reg, exec_reg)
        # Remove a required descriptor
        cap_reg.unregister("conversation_runtime")
        
    root._register_descriptors_and_executables = patched_register

    with pytest.raises(ValueError, match="Required capability descriptor 'conversation_runtime' is missing"):
        root.assemble()

def test_graceful_shutdown():
    settings = Settings()
    root = CompositionRoot(settings)
    app = root.assemble()

    shutdown_calls = []
    
    def hook1():
        shutdown_calls.append("hook1")

    def hook2():
        shutdown_calls.append("hook2")

    app.register_shutdown_hook(hook1)
    app.register_shutdown_hook(hook2)

    app.shutdown()

    assert app.status == "stopped"
    assert shutdown_calls == ["hook1", "hook2"]

def test_health_domain_structure(db_session):
    settings = Settings()
    root = CompositionRoot(settings)
    app = root.assemble()

    health = app.health_info
    
    assert health["status"] == "ready"
    assert "domains" in health
    
    domains = health["domains"]
    assert "kernel" in domains
    assert "registry" in domains
    assert "providers" in domains
    assert "models" in domains
    assert "synchronization" in domains
    
    assert domains["kernel"]["status"] == "healthy"
    assert domains["registry"]["registry_frozen"] is True
    assert "ollama_llama3" in domains["models"]["supported_models"]
    assert "markdown_provider" in domains["providers"]["registered_providers"]

def test_health_endpoint_http(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "ready"
    assert "domains" in data
    assert data["domains"]["kernel"]["status"] == "healthy"
