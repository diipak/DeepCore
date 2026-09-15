from typing import List, Any, Optional
from deepcore2.core.providers.base import BaseProvider
from deepcore2.core.registry.service import RegistryService
from deepcore2.core.objects.schemas import RegistryObjectCreate

class ManualProvider(BaseProvider):
    def __init__(self, raw_inputs: Optional[List[dict]] = None):
        """Initialize with an optional list of raw dictionary inputs."""
        self.raw_inputs = raw_inputs or []

    def add_input(self, raw_data: dict) -> None:
        """Add a raw object manually to the provider's queue."""
        self.raw_inputs.append(raw_data)

    def discover(self, *args, **kwargs) -> List[dict]:
        """Discover manually input raw objects by returning the queue and clearing it."""
        discovered = list(self.raw_inputs)
        self.raw_inputs.clear()
        return discovered

    def normalize(self, raw_data: dict) -> dict:
        """Normalize manually entered raw data to match Registry schema format."""
        # Ensure standard defaults and explicitly set source_system to 'manual'
        return {
            "object_type": raw_data.get("object_type"),
            "title": raw_data.get("title"),
            "source_system": "manual",
            "external_id": str(raw_data.get("external_id")) if raw_data.get("external_id") is not None else None,
            "location": raw_data.get("location"),
            "description": raw_data.get("description"),
            "status": raw_data.get("status", "active"),
            "metadata_json": raw_data.get("metadata_json"),
            "provider_version": raw_data.get("provider_version", "1.0.0")
        }

    def sync(self, registry_service: RegistryService, *args, **kwargs) -> List[Any]:
        """Sync manually added objects to the database using the RegistryService."""
        raw_objects = self.discover()
        registered_objects = []
        for raw in raw_objects:
            normalized = self.normalize(raw)
            obj_create = RegistryObjectCreate(**normalized)
            db_obj = registry_service.register_object(obj_create)
            registered_objects.append(db_obj)
        return registered_objects
