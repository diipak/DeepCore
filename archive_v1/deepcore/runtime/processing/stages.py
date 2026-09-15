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


class RelationshipStage:
    """
    Stage 2: Relationship Engine.
    Processes deterministic relationships for newly synchronized or modified active notes.
    """
    @property
    def id(self) -> str:
        return "relationship_engine"

    @property
    def name(self) -> str:
        return "Relationship Engine"

    @property
    def description(self) -> str:
        return "Establishes explainable, deterministic relationships between canonical objects"

    @property
    def order(self) -> int:
        return 200

    @property
    def enabled(self) -> bool:
        return True

    def execute(self, db: Session, sync_result: SyncResult, pipeline_result: ProcessingResult) -> None:
        from deepcore.intelligence.relationship_engine import RelationshipEngine
        workspace_id = pipeline_result.context["workspace_id"]
        engine = RelationshipEngine(db, workspace_id)
        try:
            processed_count = engine.process_sync_result(sync_result, pipeline_result)
            pipeline_result.objects_processed += processed_count
        except Exception as e:
            raise RuntimeError(f"Relationship Engine execution failed: {str(e)}")


class SignalStage:
    """
    Stage 3: Temporal Signal Engine.
    Processes deterministic signals for newly synchronized or modified active notes.
    """
    @property
    def id(self) -> str:
        return "temporal_signal_engine"

    @property
    def name(self) -> str:
        return "Temporal Signal Engine"

    @property
    def description(self) -> str:
        return "Derives deterministic temporal signals from canonical objects, relationships, and sync history"

    @property
    def order(self) -> int:
        return 300

    @property
    def enabled(self) -> bool:
        return True

    def execute(self, db: Session, sync_result: SyncResult, pipeline_result: ProcessingResult) -> None:
        from deepcore.intelligence.signal_engine import SignalEngine
        workspace_id = pipeline_result.context["workspace_id"]
        engine = SignalEngine(db, workspace_id)
        try:
            processed_count = engine.process_sync_result(sync_result, pipeline_result)
            pipeline_result.objects_processed += processed_count
        except Exception as e:
            raise RuntimeError(f"Temporal Signal Engine execution failed: {str(e)}")

