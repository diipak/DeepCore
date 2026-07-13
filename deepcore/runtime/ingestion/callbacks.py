from typing import Protocol, List, Any, TypeVar
from sqlalchemy.orm import Session

T = TypeVar("T", contravariant=True)

class IngestionCallback(Protocol[T]):
    """
    Lightweight protocol defining the contract for all ingestion lifecycle callbacks.
    Implemented by downstream engines (e.g. Content Index, Relationship, Signal).
    """
    def __call__(self, db: Session, sync_result: T) -> None:
        """
        Execute post-persistence processing for a synchronization run.
        """
        ...


class ContentIndexCallback:
    """
    Ingestion callback that indexes the content of newly created or updated objects.
    """
    def __call__(self, db: Session, sync_result: Any) -> None:
        from deepcore.core.content.service import ContentService
        content_service = ContentService(db)
        
        # Index all active created or updated objects
        to_index = sync_result.created + sync_result.updated
        for obj in to_index:
            if obj.status == "active" and obj.location and obj.location.lower().endswith(".md"):
                content_service.index_object(obj.id)
