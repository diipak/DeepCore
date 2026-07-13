import pytest
from pydantic import ValidationError

from deepcore.runtime.descriptors import (
    DescriptorCategory,
    BaseDescriptor,
    DescriptorProvider,
    ProviderDescriptor,
    PromptDescriptor,
    ModelDescriptor,
    CapabilityRegistry,
    DuplicateDescriptorError,
    DescriptorNotFoundError,
    DescriptorValidationError
)


# ==========================================
# Mock Provider
# ==========================================

class DummyProvider(DescriptorProvider):
    def __init__(self, desc_id: str, category: DescriptorCategory):
        self.desc_id = desc_id
        self.category = category

    def get_descriptor(self) -> BaseDescriptor:
        return BaseDescriptor(
            id=self.desc_id,
            name=f"Name-{self.desc_id}",
            description=f"Desc-{self.desc_id}",
            category=self.category,
            tags=["dummy", self.category.value]
        )


# ==========================================
# Test Cases
# ==========================================

def test_successful_registration():
    registry = CapabilityRegistry()
    
    # 1. Register a raw BaseDescriptor directly
    desc = BaseDescriptor(
        id="tool_calc",
        name="Calculator",
        description="Math operations",
        category=DescriptorCategory.TOOL,
        tags=["math", "fast"]
    )
    registry.register(desc)
    
    # Verify retrieval
    retrieved = registry.get("tool_calc")
    assert retrieved.name == "Calculator"
    assert retrieved.category == DescriptorCategory.TOOL

    # 2. Register via DescriptorProvider helper
    provider = DummyProvider("skill_nlp", DescriptorCategory.SKILL)
    registry.register_provider(provider)
    
    retrieved_provider = registry.get("skill_nlp")
    assert retrieved_provider.name == "Name-skill_nlp"
    assert retrieved_provider.category == DescriptorCategory.SKILL


def test_duplicate_registration_rejection():
    registry = CapabilityRegistry()
    
    desc1 = BaseDescriptor(
        id="shared_id",
        name="First",
        description="First desc",
        category=DescriptorCategory.MODEL
    )
    
    desc2 = BaseDescriptor(
        id="shared_id",
        name="Second",
        description="Second desc",
        category=DescriptorCategory.MODEL
    )
    
    registry.register(desc1)
    
    # Must reject duplicates
    with pytest.raises(DuplicateDescriptorError):
        registry.register(desc2)


def test_integrity_validation_rules():
    registry = CapabilityRegistry()
    
    # Invalid ID
    with pytest.raises(DescriptorValidationError):
        registry.register(BaseDescriptor(
            id="",
            name="No ID",
            description="Missing ID",
            category=DescriptorCategory.PROMPT
        ))
        
    # Invalid category (Pydantic validates this on construction, but we also check it in registry validation)
    # Let's pass an invalid version string
    with pytest.raises(DescriptorValidationError):
        registry.register(BaseDescriptor(
            id="invalid_version",
            name="Name",
            description="Desc",
            category=DescriptorCategory.TOOL,
            descriptor_version=" "  # Empty version
        ))

    with pytest.raises(DescriptorValidationError):
        registry.register(BaseDescriptor(
            id="invalid_impl_version",
            name="Name",
            description="Desc",
            category=DescriptorCategory.TOOL,
            implementation_version=""  # Empty version
        ))


def test_deterministic_ordering_invariant():
    registry = CapabilityRegistry()
    
    # Register in non-alphabetical order
    ids = ["zebra", "apple", "monkey", "banana"]
    for desc_id in ids:
        registry.register(BaseDescriptor(
            id=desc_id,
            name=f"Name-{desc_id}",
            description="Desc",
            category=DescriptorCategory.MODEL,
            tags=["deterministic"]
        ))
        
    # Invariant: list() must return sorted by ID
    all_descriptors = registry.list()
    sorted_ids = [d.id for d in all_descriptors]
    assert sorted_ids == ["apple", "banana", "monkey", "zebra"]

    # Invariant: list_by_category() must return sorted by ID
    cat_descriptors = registry.list_by_category(DescriptorCategory.MODEL)
    cat_ids = [d.id for d in cat_descriptors]
    assert cat_ids == ["apple", "banana", "monkey", "zebra"]

    # Invariant: search() must return sorted by ID
    search_descriptors = registry.search(["deterministic"])
    search_ids = [d.id for d in search_descriptors]
    assert search_ids == ["apple", "banana", "monkey", "zebra"]


def test_unregister_behavior():
    registry = CapabilityRegistry()
    
    desc = BaseDescriptor(
        id="temporary",
        name="Temp",
        description="Will be removed",
        category=DescriptorCategory.PROVIDER
    )
    
    registry.register(desc)
    assert registry.get("temporary") == desc
    
    registry.unregister("temporary")
    
    # Getting deleted ID raises DescriptorNotFoundError
    with pytest.raises(DescriptorNotFoundError):
        registry.get("temporary")
        
    # Unregistering missing ID raises DescriptorNotFoundError
    with pytest.raises(DescriptorNotFoundError):
        registry.unregister("temporary")


def test_descriptor_retrieval_immutability():
    registry = CapabilityRegistry()
    
    desc = BaseDescriptor(
        id="immutable_test",
        name="Immutable",
        description="Verify returned views cannot be mutated",
        category=DescriptorCategory.CONVERSATION
    )
    
    registry.register(desc)
    retrieved = registry.get("immutable_test")
    
    # Retrieval view must be frozen (raises ValidationError on mutation attempt)
    with pytest.raises(ValidationError):
        retrieved.name = "Mutated Name"


def test_tag_filtering():
    registry = CapabilityRegistry()
    
    desc1 = BaseDescriptor(
        id="t1",
        name="T1",
        description="D1",
        category=DescriptorCategory.TOOL,
        tags=["fast", "math"]
    )
    desc2 = BaseDescriptor(
        id="t2",
        name="T2",
        description="D2",
        category=DescriptorCategory.TOOL,
        tags=["math", "slow"]
    )
    desc3 = BaseDescriptor(
        id="t3",
        name="T3",
        description="D3",
        category=DescriptorCategory.TOOL,
        tags=["fast"]
    )
    
    registry.register(desc1)
    registry.register(desc2)
    registry.register(desc3)
    
    # Match both fast and math -> only t1
    assert [d.id for d in registry.search(["fast", "math"])] == ["t1"]
    
    # Match math -> t1 and t2
    assert [d.id for d in registry.search(["math"])] == ["t1", "t2"]
    
    # Empty search tags -> all sorted
    assert [d.id for d in registry.search([])] == ["t1", "t2", "t3"]
