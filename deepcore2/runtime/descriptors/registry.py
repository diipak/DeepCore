from typing import List, Dict, Any, Optional
from deepcore2.runtime.descriptors.base import BaseDescriptor, DescriptorCategory, DescriptorProvider
from deepcore2.runtime.descriptors.exceptions import (
    DuplicateDescriptorError,
    DescriptorNotFoundError,
    DescriptorValidationError,
    RegistryFrozenError
)

class CapabilityRegistry:
    """
    Unified metadata registry responsible for indexing, validating,
    and exposing DeepCore capability descriptors.
    
    This registry is purely metadata-focused and does not run, execute,
    or manage runtime instances.
    """
    def __init__(self):
        self._descriptors: Dict[str, BaseDescriptor] = {}
        self._frozen: bool = False

    def freeze(self) -> None:
        """Freezes the registry to prevent subsequent mutations."""
        self._frozen = True

    def register(self, descriptor: BaseDescriptor) -> None:
        """
        Validates and registers a BaseDescriptor.
        
        Raises RegistryFrozenError if the registry is frozen.
        Raises DescriptorValidationError if integrity checks fail.
        Raises DuplicateDescriptorError if the descriptor ID is already registered.
        """
        if self._frozen:
            raise RegistryFrozenError("Cannot register capability: CapabilityRegistry is frozen.")

        # 1. Validate descriptor integrity
        if not descriptor.id or not isinstance(descriptor.id, str) or not descriptor.id.strip():
            raise DescriptorValidationError("Descriptor must contain a valid non-empty string ID.")

        if descriptor.id in self._descriptors:
            raise DuplicateDescriptorError(f"Descriptor with ID '{descriptor.id}' is already registered.")

        if not isinstance(descriptor.category, DescriptorCategory):
            raise DescriptorValidationError(f"Invalid capability category: {descriptor.category}")

        if not descriptor.descriptor_version or not isinstance(descriptor.descriptor_version, str) or not descriptor.descriptor_version.strip():
            raise DescriptorValidationError("Descriptor must specify a non-empty descriptor_version.")

        if not descriptor.implementation_version or not isinstance(descriptor.implementation_version, str) or not descriptor.implementation_version.strip():
            raise DescriptorValidationError("Descriptor must specify a non-empty implementation_version.")

        # 2. Store descriptor (immutable registry view guarantee)
        # Note: Since the Pydantic models are frozen, storing them directly ensures immutability.
        self._descriptors[descriptor.id] = descriptor

    def register_provider(self, provider: DescriptorProvider) -> None:
        """
        Convenience helper to extract and register a descriptor from a DescriptorProvider.
        """
        self.register(provider.get_descriptor())

    def unregister(self, id: str) -> None:
        """
        Unregisters a descriptor by ID.
        
        Raises RegistryFrozenError if the registry is frozen.
        Raises DescriptorNotFoundError if the ID is not currently registered.
        """
        if self._frozen:
            raise RegistryFrozenError("Cannot unregister capability: CapabilityRegistry is frozen.")

        if id not in self._descriptors:
            raise DescriptorNotFoundError(f"No registered descriptor found with ID '{id}'.")
        del self._descriptors[id]

    def get(self, id: str) -> BaseDescriptor:
        """
        Retrieves a registered descriptor by ID.
        
        Raises DescriptorNotFoundError if the ID is not found.
        """
        if id not in self._descriptors:
            raise DescriptorNotFoundError(f"No registered descriptor found with ID '{id}'.")
        return self._descriptors[id]

    def list(self) -> List[BaseDescriptor]:
        """
        Returns all registered descriptors.
        
        Invariant: List is sorted deterministically by descriptor ID.
        """
        return sorted(self._descriptors.values(), key=lambda d: d.id)

    def list_by_category(self, category: DescriptorCategory) -> List[BaseDescriptor]:
        """
        Returns all descriptors within a specific category.
        
        Invariant: List is sorted deterministically by descriptor ID.
        """
        filtered = [d for d in self._descriptors.values() if d.category == category]
        return sorted(filtered, key=lambda d: d.id)

    def search(self, tags: List[str]) -> List[BaseDescriptor]:
        """
        Returns descriptors containing all matching search tags.
        
        Invariant: List is sorted deterministically by descriptor ID.
        """
        if not tags:
            return self.list()
        
        matched = []
        for d in self._descriptors.values():
            if all(t in d.tags for t in tags):
                matched.append(d)
                
        return sorted(matched, key=lambda d: d.id)
