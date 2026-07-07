from abc import ABC, abstractmethod
from typing import List, Any
from deepcore.core.registry.service import RegistryService

class BaseProvider(ABC):
    @classmethod
    def can_handle(cls, content: Any) -> bool:
        """Return True if this provider can handle/route the given input content."""
        return False
    @abstractmethod
    def discover(self, *args, **kwargs) -> List[Any]:
        """Find or gather raw objects to ingest from the source system."""
        pass

    @abstractmethod
    def normalize(self, raw_data: Any) -> dict:
        """Translate source-specific data to the standard registry object format."""
        pass

    @abstractmethod
    def sync(self, registry_service: RegistryService, *args, **kwargs) -> List[Any]:
        """Discover, normalize, and register objects in the registry database."""
        pass
