from typing import Dict, List, Any, Type, Optional
from sqlalchemy.orm import Session

from deepcore.runtime.processing.runtime import ProcessingRuntime

class IngestionRuntime:
    """
    Orchestration layer responsible for executing the Knowledge Ingestion workflow.
    Resolves providers, triggers sync execution, records stats, and delegates downstream processing.
    """
    def __init__(self, processing_runtime: ProcessingRuntime):
        self._providers: Dict[str, Type[Any]] = {}
        self.processing_runtime = processing_runtime

    def register_provider(self, name: str, provider_class: Type[Any]) -> None:
        """Register an ingestion provider class under a specific source name."""
        self._providers[name.lower()] = provider_class

    def sync_provider(self, provider_name: str, db: Session, path: str, workspace_id: Optional[int] = None, source_id: Optional[int] = None) -> Any:
        """
        Orchestrate provider synchronization and delegate post-persistence logic to the Processing Runtime.
        """
        if workspace_id is None:
            from deepcore.storage.sqlite.models import Workspace
            personal = db.query(Workspace).filter(Workspace.name == "Personal Workspace").first()
            if not personal:
                personal = Workspace(name="Personal Workspace")
                db.add(personal)
                db.commit()
                db.refresh(personal)
            workspace_id = personal.id
        
        prov_name_lower = provider_name.lower()
        
        # Check if the provider is registered as a connector SDK in AcquisitionManager
        from deepcore.runtime.composition import get_application
        app = get_application()
        
        # Map provider ID for backwards compatibility
        lookup_name = prov_name_lower
        if lookup_name in ("markdown", "markdown_provider"):
            lookup_name = "filesystem"
            
        if source_id is not None and app.acquisition_manager is not None and lookup_name in app.acquisition_manager._registry:
            connector_class = app.acquisition_manager.get_connector_class(lookup_name)
            translator_class = app.acquisition_manager.get_translator_class(lookup_name)
            connector = connector_class()
            translator = translator_class()
            
            import uuid
            run_uuid = str(uuid.uuid4())
            
            sync_run = app.acquisition_runtime.run_sync(
                source_id=source_id,
                connector=connector,
                translator=translator,
                full_sync=False,
                db=db,
                run_uuid=run_uuid
            )
            return sync_run

        # Legacy provider sync path
        if prov_name_lower not in self._providers:
            raise ValueError(f"Ingestion Provider '{provider_name}' is not supported or not registered.")

        provider_class = self._providers[prov_name_lower]
        # Instantiate provider with path config
        provider = provider_class(root_path=path)

        from deepcore.core.registry.service import RegistryService
        registry_service = RegistryService(db, workspace_id)
        registry_service.source_id = source_id
        registry_service.provider_id = prov_name_lower

        sync_result = provider.sync(registry_service)

        # 2. Delegate downstream processing (Content Index, etc.) to the Processing Runtime
        self.processing_runtime.execute(db, sync_result, workspace_id)

        # 3. Retrieve and return the sync run audit record
        runs = registry_service.list_sync_runs()
        latest_run = next((r for r in runs if r.provider == prov_name_lower and r.source_location == path), None)
        if not latest_run:
            raise RuntimeError(f"Sync completed, but no run history record was persisted for provider '{provider_name}'.")

        return latest_run

    def sync_provider_v2(self, provider_name: str, db: Session, path: str, workspace_id: Optional[int] = None, source_id: Optional[int] = None, run_uuid: Optional[str] = None) -> Any:
        """
        Orchestrate provider synchronization with real-time status persistence and cancellation check support.
        """
        if workspace_id is None:
            from deepcore.storage.sqlite.models import Workspace
            personal = db.query(Workspace).filter(Workspace.name == "Personal Workspace").first()
            if not personal:
                personal = Workspace(name="Personal Workspace")
                db.add(personal)
                db.commit()
                db.refresh(personal)
            workspace_id = personal.id
        
        prov_name_lower = provider_name.lower()
        
        # Check if the provider is registered as a connector SDK in AcquisitionManager
        from deepcore.runtime.composition import get_application
        app = get_application()
        
        # Map provider ID for backwards compatibility
        lookup_name = prov_name_lower
        if lookup_name in ("markdown", "markdown_provider"):
            lookup_name = "filesystem"
            
        if source_id is not None and app.acquisition_manager is not None and lookup_name in app.acquisition_manager._registry:
            connector_class = app.acquisition_manager.get_connector_class(lookup_name)
            translator_class = app.acquisition_manager.get_translator_class(lookup_name)
            connector = connector_class()
            translator = translator_class()
            
            sync_run = app.acquisition_runtime.run_sync(
                source_id=source_id,
                connector=connector,
                translator=translator,
                full_sync=False,
                db=db,
                run_uuid=run_uuid
            )
            return sync_run

        # Legacy provider sync path
        if prov_name_lower not in self._providers:
            raise ValueError(f"Ingestion Provider '{provider_name}' is not supported or not registered.")

        provider_class = self._providers[prov_name_lower]
        provider = provider_class(root_path=path)

        from deepcore.core.registry.service import RegistryService
        registry_service = RegistryService(db, workspace_id)
        registry_service.source_id = source_id
        registry_service.provider_id = prov_name_lower
        registry_service.run_uuid = run_uuid

        # 1. Execute sync (persistence)
        sync_result = provider.sync(registry_service)

        # 2. Delegate downstream processing (Content Index, etc.) to the Processing Runtime
        # Only run downstream processing if not cancelled!
        if registry_service.is_cancelled:
            return None

        self.processing_runtime.execute(db, sync_result, workspace_id)

        # 3. Retrieve and return the sync run audit record
        from deepcore.storage.sqlite.models import SyncRun as DBSyncRun
        latest_run = db.query(DBSyncRun).filter(DBSyncRun.uuid == run_uuid).first()
        return latest_run

