from typing import Dict, List, Any, Type
from sqlalchemy.orm import Session

from deepcore.runtime.ingestion.callbacks import IngestionCallback

class IngestionRuntime:
    """
    Orchestration layer responsible for executing the Knowledge Ingestion workflow.
    Resolves providers, triggers sync execution, records stats, and runs lifecycle callbacks.
    """
    def __init__(self):
        self._providers: Dict[str, Type[Any]] = {}
        self._callbacks: List[IngestionCallback] = []

    def register_provider(self, name: str, provider_class: Type[Any]) -> None:
        """Register an ingestion provider class under a specific source name."""
        self._providers[name.lower()] = provider_class

    def register_callback(self, callback: IngestionCallback) -> None:
        """Register a synchronous post-persistence lifecycle callback."""
        self._callbacks.append(callback)

    def sync_provider(self, provider_name: str, db: Session, path: str) -> Any:
        """
        Orchestrate provider synchronization and invoke registered lifecycle callbacks.
        """
        prov_name_lower = provider_name.lower()
        if prov_name_lower not in self._providers:
            raise ValueError(f"Ingestion Provider '{provider_name}' is not supported or not registered.")

        provider_class = self._providers[prov_name_lower]
        # Instantiate provider with path config
        provider = provider_class(root_path=path)

        from deepcore.core.registry.service import RegistryService
        registry_service = RegistryService(db)

        # 1. Execute sync (persistence)
        sync_result = provider.sync(registry_service)

        # 2. Invoke lifecycle callbacks (e.g. content index update)
        for callback in self._callbacks:
            try:
                callback(db, sync_result)
            except Exception as e:
                # Log or handle callback errors gracefully
                print(f"Error executing ingestion callback: {e}")

        # 3. Retrieve and return the sync run audit record
        runs = registry_service.list_sync_runs()
        latest_run = next((r for r in runs if r.provider == prov_name_lower and r.source_location == path), None)
        if not latest_run:
            raise RuntimeError(f"Sync completed, but no run history record was persisted for provider '{provider_name}'.")

        return latest_run
