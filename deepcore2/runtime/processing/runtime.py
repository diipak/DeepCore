import time
from typing import Protocol, List, Any, Dict, Optional
from sqlalchemy.orm import Session
from deepcore2.core.providers.base import SyncResult

class ProcessingResult:
    """
    Structured outcome of the processing pipeline execution.
    """
    def __init__(self):
        self.stages_executed: List[str] = []
        self.stage_durations: Dict[str, float] = {}  # stage ID -> duration in seconds
        self.stage_status: Dict[str, str] = {}      # stage ID -> "success" or "failed"
        self.objects_processed: int = 0
        self.failures: List[Dict[str, Any]] = []    # {"stage_id": str, "error": str}
        self.warnings: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}


class ProcessingStage(Protocol):
    """
    Lightweight protocol defining the contract for all deterministic Processing Stages.
    """
    @property
    def id(self) -> str:
        """Unique identifier of the processing stage."""
        ...

    @property
    def name(self) -> str:
        """Human-readable name of the stage."""
        ...

    @property
    def description(self) -> str:
        """Brief description of what this stage processes."""
        ...

    @property
    def order(self) -> int:
        """Numeric order of execution (lower numbers execute first)."""
        ...

    @property
    def enabled(self) -> bool:
        """Flag indicating if this stage is enabled."""
        ...

    def execute(self, db: Session, sync_result: SyncResult, pipeline_result: ProcessingResult) -> None:
        """
        Execute the transformation/processing logic for this stage.
        """
        ...


class ProcessingRuntime:
    """
    Orchestration layer responsible for executing ordered processing stages in the pipeline.
    """
    def __init__(self, observability_service: Optional[Any] = None):
        self._stages: List[ProcessingStage] = []
        self.observability_service = observability_service

    def register_stage(self, stage: ProcessingStage) -> None:
        """Register a processing stage in the pipeline."""
        if any(s.id == stage.id for s in self._stages):
            raise ValueError(f"Processing Stage with ID '{stage.id}' is already registered.")
        self._stages.append(stage)

    def get_registered_stages(self) -> List[ProcessingStage]:
        """Return registered processing stages sorted deterministically by order and ID."""
        return sorted(self._stages, key=lambda s: (s.order, s.id))

    def execute(self, db: Session, sync_result: SyncResult, workspace_id: Optional[int] = None) -> ProcessingResult:
        """
        Execute all registered, enabled stages sorted deterministically by their order.
        Provides failure isolation so a failing stage does not block the overall run.
        """
        if workspace_id is None:
            if db is not None:
                try:
                    from deepcore2.storage.sqlite.models import Workspace
                    personal = db.query(Workspace).filter(Workspace.name == "Personal Workspace").first()
                    if not personal:
                        personal = Workspace(name="Personal Workspace")
                        db.add(personal)
                        db.commit()
                        db.refresh(personal)
                    workspace_id = personal.id
                except Exception:
                    workspace_id = 1
            else:
                workspace_id = 1
            
        result = ProcessingResult()
        result.context["workspace_id"] = workspace_id
        
        # Sort stages explicitly by order, then by ID to ensure deterministic secondary sorting
        sorted_stages = self.get_registered_stages()
        
        for stage in sorted_stages:
            if not stage.enabled:
                continue

            stage_id = stage.id
            result.stages_executed.append(stage_id)
            
            start_time = time.perf_counter()
            try:
                stage.execute(db, sync_result, result)
                result.stage_status[stage_id] = "success"
            except Exception as e:
                result.stage_status[stage_id] = "failed"
                result.failures.append({
                    "stage_id": stage_id,
                    "error": str(e)
                })
            finally:
                duration = time.perf_counter() - start_time
                result.stage_durations[stage_id] = duration

        # Publish execution result to injected observability service if available
        if self.observability_service:
            try:
                self.observability_service.publish_processing_result(workspace_id, result)
            except Exception:
                pass

        return result
