import json
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session

from deepcore.core.registry.service import RegistryService
from deepcore.core.providers.youtube import YouTubeProvider

from deepcore.core.objects.schemas import RegistryObjectUpdate

# Supported providers registry
PROVIDERS = [
    YouTubeProvider
]

class UnsupportedInputError(Exception):
    """Exception raised when input cannot be routed to any registered provider."""
    pass


class CaptureService:
    def __init__(self, db: Session):
        self.db = db
        self.registry_service = RegistryService(db)

    def capture(self, content: Any) -> Any:
        """Route the input content to the correct provider and return the stamped RegistryObject."""
        matched_provider_cls = None
        for provider_cls in PROVIDERS:
            if provider_cls.can_handle(content):
                matched_provider_cls = provider_cls
                break

        if not matched_provider_cls:
            raise UnsupportedInputError(f"Unsupported input content or source system: {content}")

        # Instantiate provider with the content in its input queue
        provider = matched_provider_cls(urls=[content])
        
        # Execute sync to process the queue
        synced_objects = provider.sync(self.registry_service)
        
        if synced_objects:
            db_obj = synced_objects[0]
        else:
            # Empty sync indicates a duplicate. We retrieve the existing object using normalized coordinates.
            normalized = provider.normalize(content)
            existing = self.registry_service.list_objects(filters={
                "source_system": normalized["source_system"],
                "external_id": normalized["external_id"]
            })
            if not existing:
                raise ValueError("Failed to retrieve or register object.")
            db_obj = existing[0]

        # Post-process and stamp metadata with capture audit details
        metadata = json.loads(db_obj.metadata_json) if db_obj.metadata_json else {}
        metadata["captured_via"] = "capture"
        metadata["captured_at"] = datetime.now(timezone.utc).isoformat()
        
        # Avoid direct DB write/commit, use RegistryService update_object
        update_data = RegistryObjectUpdate(metadata_json=json.dumps(metadata))
        return self.registry_service.update_object(db_obj.id, update_data)
