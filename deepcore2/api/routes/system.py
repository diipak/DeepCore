from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from deepcore2.storage.sqlite.db import get_db
from deepcore2.core.objects import schemas
from deepcore2.core.registry.service import RegistryService
from deepcore2.storage.sqlite.models import RegistryObject as DBRegistryObject, RegistryRelationship as DBRegistryRelationship
from deepcore2.api.routes.concepts import ConceptListEntry
from deepcore2.api.dependencies import get_execution_context

router = APIRouter(tags=["system"])

class SidebarSourceEntry(BaseModel):
    id: str
    name: str
    count: int
    visible: bool

class SystemStatsResponse(BaseModel):
    total_objects: int
    by_type: dict[str, int]
    by_source: dict[str, int]
    concept_count: int
    relationship_count: int
    sources: List[SidebarSourceEntry]

class TimelineStage(BaseModel):
    id: str
    name: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: float
    warnings: List[str] = []
    errors: List[str] = []

class ObservabilityTimeline(BaseModel):
    workspace_uuid: str
    run_uuid: Optional[str] = None
    status: str
    stages: List[TimelineStage]

class DescriptorEntry(BaseModel):
    id: str
    name: str
    category: str
    version: str
    implementation_version: str
    configurable: bool
    tags: List[str] = []

class RuntimeEntry(BaseModel):
    name: str
    version: str
    initialized: bool
    enabled: bool
    health: str
    dependencies: List[str]
    capabilities: List[str]
    registration_status: str

class ActiveExecution(BaseModel):
    uuid: str
    provider: str
    source_location: str
    started_at: str

class SyncRunHistoryEntry(BaseModel):
    uuid: str
    provider: str
    source_location: str
    started_at: str
    completed_at: Optional[str] = None
    status: str
    objects_scanned: int
    objects_created: int
    objects_existing: int
    objects_updated: int
    objects_missing: int
    errors: List[str] = []

class SystemObservabilityResponse(BaseModel):
    registered_runtimes: List[RuntimeEntry]
    capability_registry: List[DescriptorEntry]
    descriptor_registry: List[DescriptorEntry]
    active_execution: Optional[ActiveExecution] = None
    execution_queue: List[ActiveExecution] = []
    execution_history: List[SyncRunHistoryEntry] = []
    timeline: Optional[ObservabilityTimeline] = None


class CognitiveFocus(BaseModel):
    title: str
    object_type: str
    object_uuid: str
    description: str
    last_accessed: str

class SemanticChange(BaseModel):
    title: str
    change_type: str
    description: str
    time_ago: str
    object_uuid: Optional[str] = None

class CognitiveObservation(BaseModel):
    id: str
    observation_type: str
    title: str
    description: str
    severity: str
    action_label: str
    action_route: str

class CognitiveNextStep(BaseModel):
    title: str
    prompt: str
    action_label: str

class DashboardSummary(BaseModel):
    memory_count: int
    concept_count: int
    relationship_count: int

class DashboardResponse(BaseModel):
    summary: DashboardSummary
    focus: List[CognitiveFocus]
    orientation: List[SemanticChange]
    understanding: List[CognitiveObservation]
    continuation: List[CognitiveNextStep]

@router.get("/stats", response_model=SystemStatsResponse)
def get_system_stats_api(
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """System statistics API endpoint scoped to the workspace."""
    from deepcore2.storage.sqlite.models import KnowledgeSource as DBKnowledgeSource
    registry_service = RegistryService(db, context.workspace_id)
    stats_data = registry_service.get_statistics()
    
    concept_count = db.query(DBRegistryObject).filter(
        DBRegistryObject.workspace_id == context.workspace_id,
        DBRegistryObject.object_type == "concept"
    ).count()
    relationship_count = db.query(DBRegistryRelationship).filter(
        DBRegistryRelationship.workspace_id == context.workspace_id
    ).count()
    
    # 1. Fetch registered sources of the workspace
    registered_sources = db.query(DBKnowledgeSource).filter(
        DBKnowledgeSource.workspace_id == context.workspace_id
    ).all()
    
    sources_entries = []
    registered_provider_ids = set()
    
    nice_names = {
        "markdown": "Obsidian Note",
        "youtube": "YouTube Capture",
        "github": "GitHub Repository",
        "web": "Web Capture"
    }
    
    for src in registered_sources:
        registered_provider_ids.add(src.provider_id)
        count = stats_data["by_source"].get(src.provider_id, 0)
        sources_entries.append(SidebarSourceEntry(
            id=src.provider_id,
            name=src.name,
            count=count,
            visible=True
        ))
        
    # Add ad-hoc systems
    adhoc_systems = ["youtube", "github", "web", "markdown"]
    for system in adhoc_systems:
        if system in registered_provider_ids:
            continue
        count = stats_data["by_source"].get(system, 0)
        sources_entries.append(SidebarSourceEntry(
            id=system,
            name=nice_names.get(system, system.capitalize()),
            count=count,
            visible=count > 0
        ))

    return SystemStatsResponse(
        total_objects=stats_data["total_objects"],
        by_type=stats_data["by_type"],
        by_source=stats_data["by_source"],
        concept_count=concept_count,
        relationship_count=relationship_count,
        sources=sources_entries
    )

@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard_api(
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """Dashboard overview API endpoint for the UI home screen scoped to the workspace."""
    from deepcore2.core.awareness.service import AwarenessService
    
    service = AwarenessService(db, context.workspace_id)
    state = service.get_awareness_state()
    return state


@router.get("/health")
def health_endpoint():
    """Exposes hierarchical domain-based health and diagnostics of the application."""
    from deepcore2.runtime.composition import get_application
    app = get_application()
    return app.health_info


class WorkspaceSourceInfo(BaseModel):
    uuid: str
    name: str
    kind: str
    provider_id: str
    location: str
    config_json: Optional[str] = None


class WorkspaceDiagnosticsResponse(BaseModel):
    workspace_id: int
    workspace_uuid: str
    workspace_name: str
    db_path: str
    object_count: int
    relationship_count: int
    signal_count: int
    last_sync_run: Optional[dict] = None
    registered_providers: List[str] = []
    registered_sources: List[WorkspaceSourceInfo] = []
    active_stages: List[dict] = []


@router.get("/system/workspace", response_model=WorkspaceDiagnosticsResponse)
def get_system_workspace_diagnostics(
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """Retrieve runtime diagnostics info scoped to the active workspace."""
    from deepcore2.runtime.composition import get_application
    from deepcore2.storage.sqlite.models import RegistrySignal as DBRegistrySignal, SyncRun as DBSyncRun, KnowledgeSource as DBKnowledgeSource
    app = get_application()

    # Counts scoped to workspace
    obj_count = db.query(DBRegistryObject).filter(DBRegistryObject.workspace_id == context.workspace_id).count()
    rel_count = db.query(DBRegistryRelationship).filter(DBRegistryRelationship.workspace_id == context.workspace_id).count()
    sig_count = db.query(DBRegistrySignal).filter(DBRegistrySignal.workspace_id == context.workspace_id).count()

    # Last sync run scoped to workspace
    last_run = db.query(DBSyncRun).filter(DBSyncRun.workspace_id == context.workspace_id).order_by(DBSyncRun.started_at.desc()).first()
    last_run_dict = None
    if last_run:
        last_run_dict = {
            "uuid": last_run.uuid,
            "provider": last_run.provider,
            "source_location": last_run.source_location,
            "started_at": last_run.started_at,
            "completed_at": last_run.finished_at,
            "status": last_run.status,
            "objects_created": last_run.objects_created,
            "objects_updated": last_run.objects_updated,
            "objects_missing": last_run.objects_missing,
        }

    # Registered sources in this workspace
    sources = db.query(DBKnowledgeSource).filter(DBKnowledgeSource.workspace_id == context.workspace_id).all()
    sources_list = [
        WorkspaceSourceInfo(
            uuid=s.uuid,
            name=s.name,
            kind=s.kind,
            provider_id=s.provider_id,
            location=s.location,
            config_json=s.config_json
        )
        for s in sources
    ]

    # Active stages
    stages = [
        {"id": stage.id, "name": stage.name, "order": stage.order, "enabled": stage.enabled}
        for stage in app.processing_service._stages
    ]

    db_path = "unknown"
    if db.bind:
        if hasattr(db.bind, "url"):
            db_path = str(db.bind.url.database)
        elif hasattr(db.bind, "engine") and hasattr(db.bind.engine, "url"):
            db_path = str(db.bind.engine.url.database)

    return WorkspaceDiagnosticsResponse(
        workspace_id=context.workspace_id,
        workspace_uuid=context.workspace_uuid,
        workspace_name=context.workspace_name,
        db_path=db_path,
        object_count=obj_count,
        relationship_count=rel_count,
        signal_count=sig_count,
        last_sync_run=last_run_dict,
        registered_providers=list(app.ingestion_service._providers.keys()),
        registered_sources=sources_list,
        active_stages=stages
    )


class SubsystemHealth(BaseModel):
    status: str
    message: Optional[str] = None
    metrics: dict = {}


class PlatformHealthResponse(BaseModel):
    status: str
    subsystems: dict[str, SubsystemHealth]


@router.get("/system/runs", response_model=List[schemas.SyncRun])
def get_system_runs(
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """Retrieve history of sync runs scoped to the active workspace."""
    registry_service = RegistryService(db, context.workspace_id)
    return registry_service.list_sync_runs()


@router.get("/system/health", response_model=PlatformHealthResponse)
def get_system_health(
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """Exposes high-level health status of all 10 major subsystems in DeepCore."""
    from sqlalchemy import text
    from deepcore2.runtime.composition import get_application
    from deepcore2.storage.sqlite.models import Workspace, KnowledgeSource, RegistryObject
    app = get_application()

    subsystems = {}

    # 1. Database
    try:
        db.execute(text("SELECT 1")).scalar()
        subsystems["database"] = SubsystemHealth(
            status="healthy",
            message="Database connection established",
            metrics={"url": str(db.bind.url) if db.bind else "sqlite"}
        )
    except Exception as e:
        subsystems["database"] = SubsystemHealth(
            status="unhealthy",
            message=str(e),
            metrics={}
        )

    # 2. Workspace Resolver
    try:
        ws_count = db.query(Workspace).count()
        subsystems["workspace_resolver"] = SubsystemHealth(
            status="healthy",
            message=f"Resolved active workspace ID {context.workspace_id} ({context.workspace_name})",
            metrics={"total_workspaces": ws_count, "active_workspace_id": context.workspace_id}
        )
    except Exception as e:
        subsystems["workspace_resolver"] = SubsystemHealth(
            status="unhealthy",
            message=str(e),
            metrics={}
        )

    # 3. Registry
    try:
        obj_count = db.query(DBRegistryObject).filter(DBRegistryObject.workspace_id == context.workspace_id).count()
        subsystems["registry"] = SubsystemHealth(
            status="healthy",
            message=f"Operational. Registry contains {obj_count} objects in active workspace",
            metrics={"objects_count": obj_count}
        )
    except Exception as e:
        subsystems["registry"] = SubsystemHealth(
            status="unhealthy",
            message=str(e),
            metrics={}
        )

    # 4. Provider Registry
    try:
        providers = list(app.ingestion_service._providers.keys())
        subsystems["provider_registry"] = SubsystemHealth(
            status="healthy",
            message=f"Registered providers: {', '.join(providers)}",
            metrics={"providers_list": providers}
        )
    except Exception as e:
        subsystems["provider_registry"] = SubsystemHealth(
            status="unhealthy",
            message=str(e),
            metrics={}
        )

    # 5. Knowledge Sources
    try:
        sources_count = db.query(KnowledgeSource).filter(KnowledgeSource.workspace_id == context.workspace_id).count()
        subsystems["knowledge_sources"] = SubsystemHealth(
            status="healthy",
            message=f"Operational. Found {sources_count} registered sources",
            metrics={"sources_count": sources_count}
        )
    except Exception as e:
        subsystems["knowledge_sources"] = SubsystemHealth(
            status="unhealthy",
            message=str(e),
            metrics={}
        )

    # 6. Processing Runtime
    try:
        stages_count = len(app.processing_service._stages)
        subsystems["processing_runtime"] = SubsystemHealth(
            status="healthy",
            message=f"Loaded with {stages_count} processing stages",
            metrics={"stages_count": stages_count}
        )
    except Exception as e:
        subsystems["processing_runtime"] = SubsystemHealth(
            status="unhealthy",
            message=str(e),
            metrics={}
        )

    # Helper function to check stage health
    def get_stage_health(stage_id: str):
        try:
            stage = next((s for s in app.processing_service._stages if s.id == stage_id), None)
            if stage:
                if stage.enabled:
                    return SubsystemHealth(status="healthy", message="Stage is registered and enabled", metrics={"order": stage.order})
                else:
                    return SubsystemHealth(status="degraded", message="Stage is disabled", metrics={"order": stage.order})
            else:
                return SubsystemHealth(status="unhealthy", message="Stage not found in processing runtime", metrics={})
        except Exception as e:
            return SubsystemHealth(status="unhealthy", message=str(e), metrics={})

    # 7. Content Index Stage
    subsystems["content_index_stage"] = get_stage_health("content_indexing")

    # 8. Relationship Engine
    subsystems["relationship_engine"] = get_stage_health("relationship_engine")

    # 9. Temporal Signal Engine
    subsystems["temporal_signal_engine"] = get_stage_health("temporal_signal_engine")

    # 10. API Runtime
    subsystems["api_runtime"] = SubsystemHealth(
        status="healthy",
        message="FastAPI backend runtime active",
        metrics={"version": "0.1.0"}
    )

    # 11. Workspace Integrity
    try:
        from deepcore2.core.integrity.service import WorkspaceIntegrityService
        integrity_service = WorkspaceIntegrityService(db, context.workspace_id)
        validation = integrity_service.validate_integrity()
        subsystems["workspace_integrity"] = SubsystemHealth(
            status=validation["status"],
            message="All workspace integrity checks passed" if validation["status"] == "healthy" else "Some integrity checks failed",
            metrics=validation["checks"]
        )
    except Exception as e:
        subsystems["workspace_integrity"] = SubsystemHealth(
            status="unhealthy",
            message=str(e),
            metrics={}
        )

    # Determine overall status
    overall_status = "healthy"
    for sub in subsystems.values():
        if sub.status == "unhealthy":
            overall_status = "unhealthy"
            break
        elif sub.status == "degraded":
            overall_status = "degraded"

    return PlatformHealthResponse(
        status=overall_status,
        subsystems=subsystems
    )


@router.get("/system/observability", response_model=SystemObservabilityResponse)
def get_system_observability_api(
    db: Session = Depends(get_db),
    context: schemas.ExecutionContext = Depends(get_execution_context)
):
    """Retrieve detailed developer observability data dynamically compiled from the ObservabilityService."""
    from deepcore2.runtime.composition import get_application
    app = get_application()
    if not app.observability_service:
        raise HTTPException(status_code=500, detail="Observability service is not wired in the application composition.")
    
    return app.observability_service.get_observability_data(context.workspace_id, db, app)



