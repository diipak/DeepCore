import pytest
from deepcore.runtime.descriptors import (
    DescriptorCategory,
    BaseDescriptor,
    ProviderDescriptor,
    PromptDescriptor,
    ModelDescriptor,
    CapabilityRegistry,
    CapabilityDiscoveryService,
    CapabilitySummary,
    CapabilityDetail,
    CapabilityCatalog,
    DescriptorNotFoundError
)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def populated_registry():
    registry = CapabilityRegistry()
    
    # 1. Enabled Tool
    registry.register(BaseDescriptor(
        id="tool_calc",
        name="Calculator",
        description="Run arithmetic",
        category=DescriptorCategory.TOOL,
        enabled=True,
        tags=["math"]
    ))
    
    # 2. Disabled/Experimental Skill
    registry.register(BaseDescriptor(
        id="skill_nlp",
        name="NLP Parser",
        description="Parse sentences",
        category=DescriptorCategory.SKILL,
        enabled=False,
        experimental=True,
        tags=["nlp"]
    ))
    
    # 3. Configurable Provider
    registry.register(ProviderDescriptor(
        id="provider_md",
        name="Markdown Sync",
        description="Sync markdown notes",
        category=DescriptorCategory.PROVIDER,
        enabled=True,
        configurable=True,
        provider_type="markdown",
        supported_formats=[".md"]
    ))
    
    # 4. Prompt
    registry.register(PromptDescriptor(
        id="prompt_sync",
        name="Sync Guidance",
        description="Instructions on sync",
        category=DescriptorCategory.PROMPT,
        enabled=True,
        template_identifier="guidance_v1",
        strategy_name="cot",
        input_variables=["vault_path"]
    ))
    
    # 5. Model
    registry.register(ModelDescriptor(
        id="model_llm",
        name="Local LLM",
        description="Local inference engine",
        category=DescriptorCategory.MODEL,
        enabled=True,
        model_type="local_llm",
        context_length=8192,
        publisher="meta-llama"
    ))
    
    return registry


@pytest.fixture
def discovery_service(populated_registry):
    return CapabilityDiscoveryService(populated_registry)


# ==========================================
# Test Cases
# ==========================================

def test_get_all_capabilities(discovery_service):
    summaries = discovery_service.get_all_capabilities()
    
    # Verify all registered capabilities returned
    assert len(summaries) == 5
    
    # Verify mapping to client-facing model CapabilitySummary
    for s in summaries:
        assert isinstance(s, CapabilitySummary)
        # Ensure it has no implementation-specific fields (e.g. context_length)
        assert not hasattr(s, "context_length")
        
    # Verify deterministic sorting (alphabetical by ID)
    ids = [s.id for s in summaries]
    assert ids == ["model_llm", "prompt_sync", "provider_md", "skill_nlp", "tool_calc"]


def test_get_capability_details(discovery_service):
    # Lookup LLM Model details
    detail = discovery_service.get_capability("model_llm")
    
    assert isinstance(detail, CapabilityDetail)
    assert isinstance(detail.summary, CapabilitySummary)
    assert detail.summary.id == "model_llm"
    assert detail.summary.category == DescriptorCategory.MODEL
    
    # Verify that subclass-specific fields are preserved in details dict
    assert detail.details["context_length"] == 8192
    assert detail.details["publisher"] == "meta-llama"
    assert detail.details["model_type"] == "local_llm"
    
    # Missing ID raises DescriptorNotFoundError
    with pytest.raises(DescriptorNotFoundError):
        discovery_service.get_capability("nonexistent")


def test_get_by_category(discovery_service):
    summaries = discovery_service.get_by_category(DescriptorCategory.TOOL)
    assert len(summaries) == 1
    assert summaries[0].id == "tool_calc"


def test_filtering_methods(discovery_service):
    # 1. Enabled
    enabled = discovery_service.get_enabled()
    assert len(enabled) == 4
    assert "skill_nlp" not in [e.id for e in enabled]  # skill_nlp is disabled
    
    # 2. Experimental
    experimental = discovery_service.get_experimental()
    assert len(experimental) == 1
    assert experimental[0].id == "skill_nlp"
    
    # 3. Configurable
    configurable = discovery_service.get_configurable()
    assert len(configurable) == 1
    assert configurable[0].id == "provider_md"


def test_generic_catalog_grouping(discovery_service):
    catalog = discovery_service.get_catalog()
    
    assert isinstance(catalog, CapabilityCatalog)
    assert len(catalog.categories) == 5  # model, prompt, provider, skill, tool
    
    # Verify group structures and display names
    for group in catalog.categories:
        assert isinstance(group.category, DescriptorCategory)
        assert group.display_name == group.category.value.capitalize()
        # Verify capabilities in group are CapabilitySummary
        for cap in group.capabilities:
            assert isinstance(cap, CapabilitySummary)
            assert cap.category == group.category
            
    # Verify deterministic sorting of groups by category value
    categories_order = [g.category for g in catalog.categories]
    assert categories_order == [
        DescriptorCategory.MODEL,
        DescriptorCategory.PROMPT,
        DescriptorCategory.PROVIDER,
        DescriptorCategory.SKILL,
        DescriptorCategory.TOOL
    ]
    
    # Add a new descriptor dynamically to verify generic grouping updates
    discovery_service.registry.register(BaseDescriptor(
        id="tool_custom",
        name="Custom Tool",
        description="A custom capability",
        category=DescriptorCategory.TOOL,
        tags=["custom"]
    ))
    
    new_catalog = discovery_service.get_catalog()
    # Should automatically incorporate it without changes
    total_caps = sum(len(g.capabilities) for g in new_catalog.categories)
    assert total_caps == 6


def test_stateless_repeated_calls(discovery_service):
    # Repeated calls must yield identical, fresh result lists without side effects
    res1 = discovery_service.get_all_capabilities()
    res2 = discovery_service.get_all_capabilities()
    
    assert [r.id for r in res1] == [r.id for r in res2]
    assert id(res1) != id(res2)  # different list instances
