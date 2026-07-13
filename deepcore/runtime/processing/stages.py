from sqlalchemy.orm import Session
from deepcore.core.providers.base import SyncResult
from deepcore.runtime.processing.runtime import ProcessingResult

class ContentIndexStage:
    """
    Stage 1: Ingestion Content Indexing.
    Processes newly synchronized or modified active notes to update their raw text index entries.
    """
    @property
    def id(self) -> str:
        return "content_indexing"

    @property
    def name(self) -> str:
        return "Content Indexing"

    @property
    def description(self) -> str:
        return "Extracts and indexes raw text from markdown documents for preview and search"

    @property
    def order(self) -> int:
        return 100

    @property
    def enabled(self) -> bool:
        return True

    def execute(self, db: Session, sync_result: SyncResult, pipeline_result: ProcessingResult) -> None:
        from deepcore.core.content.service import ContentService
        content_service = ContentService(db)

        # Index all active created or updated objects
        to_index = sync_result.created + sync_result.updated
        processed_count = 0
        
        for obj in to_index:
            if obj.status == "active" and obj.location and obj.location.lower().endswith(".md"):
                try:
                    content_service.index_object(obj.id)
                    processed_count += 1
                except Exception as e:
                    pipeline_result.failures.append({
                        "stage_id": self.id,
                        "object_id": obj.id,
                        "error": str(e)
                    })

        pipeline_result.objects_processed += processed_count
