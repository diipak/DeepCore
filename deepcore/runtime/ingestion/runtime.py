from typing import Dict, List, Any, Type
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

    def sync_provider(self, provider_name: str, db: Session, path: str) -> Any:
        """
        Orchestrate provider synchronization and delegate post-persistence logic to the Processing Runtime.
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

        # 2. Delegate downstream processing (Content Index, etc.) to the Processing Runtime
        self.processing_runtime.execute(db, sync_result)

        # 3. Retrieve and return the sync run audit record
        runs = registry_service.list_sync_runs()
        latest_run = next((r for r in runs if r.provider == prov_name_lower and r.source_location == path), None)
        if not latest_run:
            raise RuntimeError(f"Sync completed, but no run history record was persisted for provider '{provider_name}'.")

        return latest_run
