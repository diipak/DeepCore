from abc import ABC, abstractmethod
from typing import List, Any

class SyncResult:
    """
    Structured outcome of a synchronization run, describing exactly
    what changed in the repository storage layer.
    """
    def __init__(self, scanned: int = 0, created: List[Any] = None, updated: List[Any] = None, existing: List[Any] = None, missing: List[Any] = None):
        self.scanned = scanned
        self.created = created or []
        self.updated = updated or []
        self.existing = existing or []
        self.missing = missing or []

    def __len__(self) -> int:
        return len(self.created)

    def __getitem__(self, index: int) -> Any:
        return self.created[index]

    def __iter__(self):
        return iter(self.created)

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
    def sync(self, registry_service: Any, *args, **kwargs) -> List[Any]:
        """Discover, normalize, and register objects in the registry database."""
        pass
