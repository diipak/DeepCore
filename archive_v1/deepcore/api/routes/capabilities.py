from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from deepcore.storage.sqlite.db import get_db
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
    DuplicateDescriptorError,
    DescriptorNotFoundError
)

from deepcore.runtime.tools.registry import ToolRegistry, ExecutionRegistry as ToolExecRegistry
from deepcore.runtime.tools.runtime import ToolRuntime
from deepcore.runtime.skills.registry import SkillRegistry
from deepcore.runtime.skills.runtime import SkillRuntime


from deepcore.runtime.stubs import (
    EchoTool,
    RegistrySearchMockTool,
    EchoSkill,
    RegistrySearchEchoSkill,
)
from deepcore.core.registry.service import RegistryService

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


def get_discovery_service() -> CapabilityDiscoveryService:
    """
    Helper dependency to retrieve the CapabilityDiscoveryService from the Application singleton.
    """
    from deepcore.runtime.composition import get_application
    app = get_application()
    return app.capabilities_service


@router.get("", response_model=CapabilityCatalog)
def get_catalog(
    service: CapabilityDiscoveryService = Depends(get_discovery_service)
):
    """Exposes the dynamically compiled capability catalog."""
    return service.get_catalog()


@router.get("/filter", response_model=List[CapabilitySummary])
def filter_capabilities(
    enabled: Optional[bool] = None,
    configurable: Optional[bool] = None,
    experimental: Optional[bool] = None,
    service: CapabilityDiscoveryService = Depends(get_discovery_service)
):
    """Returns filtered lists of capability summaries."""
    results = service.get_all_capabilities()
    
    if enabled is not None:
        results = [r for r in results if r.enabled == enabled]
    if configurable is not None:
        results = [r for r in results if r.configurable == configurable]
    if experimental is not None:
        results = [r for r in results if r.experimental == experimental]
        
    return results


@router.get("/category/{category}", response_model=List[CapabilitySummary])
def get_by_category(
    category: str,
    service: CapabilityDiscoveryService = Depends(get_discovery_service)
):
    """Returns all capability summaries matching a category."""
    try:
        enum_cat = DescriptorCategory(category.lower())
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid category: '{category}'. Supported values: {[c.value for c in DescriptorCategory]}"
        )
    return service.get_by_category(enum_cat)


@router.get("/{id}", response_model=CapabilityDetail)
def get_detail(
    id: str,
    service: CapabilityDiscoveryService = Depends(get_discovery_service)
):
    """Retrieves detailed metadata for a capability by ID."""
    try:
        return service.get_capability(id)
    except DescriptorNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Capability with ID '{id}' not found."
        )
