from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from deepcore.runtime.descriptors.base import BaseDescriptor, DescriptorCategory
from deepcore.runtime.descriptors.registry import CapabilityRegistry
from deepcore.runtime.descriptors.exceptions import DescriptorNotFoundError

class CapabilitySummary(BaseModel):
    """Client-facing minimal summary of a capability."""
    id: str
    name: str
    description: str
    category: DescriptorCategory
    enabled: bool
    configurable: bool
    experimental: bool
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CapabilityDetail(BaseModel):
    """Client-facing rich description containing base summary and implementation-specific schema/examples."""
    summary: CapabilitySummary
    details: Dict[str, Any]


class CapabilityCategoryGroup(BaseModel):
    """Group of capability summaries categorized under a single DescriptorCategory."""
    category: DescriptorCategory
    display_name: str
    capabilities: List[CapabilitySummary] = Field(default_factory=list)


class CapabilityCatalog(BaseModel):
    """Generic catalog view containing grouped capabilities."""
    categories: List[CapabilityCategoryGroup] = Field(default_factory=list)


class CapabilityDiscoveryService:
    """
    Stateless composition layer responsible for translating CapabilityRegistry metadata
    into client-friendly CapabilitySummary, CapabilityDetail, and CapabilityCatalog schemas.
    """
    def __init__(self, registry: CapabilityRegistry):
        self.registry = registry

    def _map_to_summary(self, desc: BaseDescriptor) -> CapabilitySummary:
        """Helper to translate internal BaseDescriptor to CapabilitySummary."""
        return CapabilitySummary(
            id=desc.id,
            name=desc.name,
            description=desc.description,
            category=desc.category,
            enabled=desc.enabled,
            configurable=desc.configurable,
            experimental=desc.experimental,
            tags=desc.tags,
            metadata=desc.metadata
        )

    def _filter_summaries(self, predicate) -> List[CapabilitySummary]:
        """Shared private filter and sort helper."""
        descriptors = self.registry.list()  # returns pre-sorted list by ID
        return [self._map_to_summary(d) for d in descriptors if predicate(d)]

    def get_all_capabilities(self) -> List[CapabilitySummary]:
        """Returns summaries of all registered capabilities, sorted by ID."""
        return self._filter_summaries(lambda _: True)

    def get_capability(self, id: str) -> CapabilityDetail:
        """
        Retrieves detailed view for a single capability.
        
        Raises DescriptorNotFoundError if the ID is not registered.
        """
        desc = self.registry.get(id)  # raises DescriptorNotFoundError if missing
        summary = self._map_to_summary(desc)
        
        # Extract details: model fields excluding base fields
        base_keys = set(BaseDescriptor.model_fields.keys())
        all_fields = desc.model_dump()
        details = {k: v for k, v in all_fields.items() if k not in base_keys}
        
        return CapabilityDetail(summary=summary, details=details)

    def get_by_category(self, category: DescriptorCategory) -> List[CapabilitySummary]:
        """Returns summaries matching the requested category, sorted by ID."""
        return self._filter_summaries(lambda d: d.category == category)

    def get_enabled(self) -> List[CapabilitySummary]:
        """Returns summaries of all enabled capabilities, sorted by ID."""
        return self._filter_summaries(lambda d: d.enabled is True)

    def get_experimental(self) -> List[CapabilitySummary]:
        """Returns summaries of all experimental capabilities, sorted by ID."""
        return self._filter_summaries(lambda d: d.experimental is True)

    def get_configurable(self) -> List[CapabilitySummary]:
        """Returns summaries of all configurable capabilities, sorted by ID."""
        return self._filter_summaries(lambda d: d.configurable is True)

    def get_catalog(self) -> CapabilityCatalog:
        """
        Groups all registered summaries dynamically into a generic CapabilityCatalog.
        Builds groups based on the registered descriptor categories.
        """
        groups: Dict[DescriptorCategory, List[CapabilitySummary]] = {}
        
        # 1. Group summaries by category
        for summary in self.get_all_capabilities():
            if summary.category not in groups:
                groups[summary.category] = []
            groups[summary.category].append(summary)

        # 2. Build sorted category list
        categories_list = sorted(list(groups.keys()), key=lambda c: c.value)
        category_groups = []
        for cat in categories_list:
            category_groups.append(
                CapabilityCategoryGroup(
                    category=cat,
                    display_name=cat.value.capitalize(),
                    capabilities=groups[cat]
                )
            )

        return CapabilityCatalog(categories=category_groups)
