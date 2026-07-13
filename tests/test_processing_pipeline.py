import pytest
from deepcore.runtime.processing.runtime import ProcessingRuntime, ProcessingResult, ProcessingStage
from deepcore.runtime.processing.stages import ContentIndexStage
from deepcore.core.providers.base import SyncResult
from deepcore.storage.sqlite.models import ContentIndex, RegistryObject

class MockStage:
    def __init__(self, stage_id: str, order: int, fail: bool = False, enabled: bool = True):
        self._id = stage_id
        self._order = order
        self.fail = fail
        self._enabled = enabled
        self.executed = False
        self.execution_order = None

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return f"Mock Stage {self._id}"

    @property
    def description(self) -> str:
        return "A mock stage for pipeline verification"

    @property
    def order(self) -> int:
        return self._order

    @property
    def enabled(self) -> bool:
        return self._enabled

    def execute(self, db, sync_result, pipeline_result) -> None:
        self.executed = True
        # Track execution order dynamically
        execution_sequence = getattr(pipeline_result, "_sequence", [])
        execution_sequence.append(self._id)
        pipeline_result._sequence = execution_sequence
        
        if self.fail:
            raise RuntimeError(f"Stage {self._id} failed intentionally.")


def test_processing_stage_contract_metadata():
    """Verify that ContentIndexStage satisfies the ProcessingStage contract metadata."""
    stage = ContentIndexStage()
    assert stage.id == "content_indexing"
    assert stage.name == "Content Indexing"
    assert len(stage.description) > 0
    assert isinstance(stage.order, int)
    assert stage.enabled is True


def test_processing_runtime_explicit_ordering():
    """Verify that stages execute in explicit numeric order rather than registration order."""
    runtime = ProcessingRuntime()
    
    # Register in non-sequential order
    stage_c = MockStage("C", order=30)
    stage_a = MockStage("A", order=10)
    stage_b = MockStage("B", order=20)
    
    runtime.register_stage(stage_c)
    runtime.register_stage(stage_a)
    runtime.register_stage(stage_b)

    sync_res = SyncResult()
    result = runtime.execute(None, sync_res)

    # Order must be sorted explicitly: A (10), B (20), C (30)
    assert result.stages_executed == ["A", "B", "C"]
    assert getattr(result, "_sequence") == ["A", "B", "C"]


def test_processing_runtime_failure_isolation():
    """Verify that a failing stage does not block the execution of subsequent stages."""
    runtime = ProcessingRuntime()
    
    stage_1 = MockStage("1", order=10, fail=True)
    stage_2 = MockStage("2", order=20)
    
    runtime.register_stage(stage_1)
    runtime.register_stage(stage_2)

    sync_res = SyncResult()
    result = runtime.execute(None, sync_res)

    assert result.stages_executed == ["1", "2"]
    assert stage_1.executed is True
    assert stage_2.executed is True
    
    # Stats checking
    assert result.stage_status["1"] == "failed"
    assert result.stage_status["2"] == "success"
    assert len(result.failures) == 1
    assert result.failures[0]["stage_id"] == "1"
    assert "failed intentionally" in result.failures[0]["error"]


def test_processing_runtime_enabled_toggle():
    """Verify that disabled stages are skipped entirely during pipeline execution."""
    runtime = ProcessingRuntime()
    
    stage_1 = MockStage("1", order=10)
    stage_2 = MockStage("2", order=20, enabled=False)
    
    runtime.register_stage(stage_1)
    runtime.register_stage(stage_2)

    sync_res = SyncResult()
    result = runtime.execute(None, sync_res)

    assert result.stages_executed == ["1"]
    assert stage_1.executed is True
    assert stage_2.executed is False


def test_content_indexing_stage_execution(staged_notes_dir, db_session):
    """Verify that ContentIndexStage successfully indexes newly created active notes."""
    # Register objects manually first
    from deepcore.core.providers.markdown import MarkdownProvider
    from deepcore.core.registry.service import RegistryService

    provider = MarkdownProvider(root_path=staged_notes_dir)
    registry_service = RegistryService(db_session)
    
    # Sync returns SyncResult
    sync_result = provider.sync(registry_service)
    assert len(sync_result.created) == 3

    # Clear ContentIndex table to ensure the stage does the work
    db_session.query(ContentIndex).delete()
    db_session.commit()
    assert db_session.query(ContentIndex).count() == 0

    # Instantiate and execute Stage 1
    stage = ContentIndexStage()
    pipeline_res = ProcessingResult()
    
    stage.execute(db_session, sync_result, pipeline_res)

    # Check database
    assert db_session.query(ContentIndex).count() == 3
    assert pipeline_res.objects_processed == 3
    assert len(pipeline_res.failures) == 0
