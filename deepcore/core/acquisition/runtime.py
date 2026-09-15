import json
import time
import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Generator
from sqlalchemy.orm import Session
from deepcore.storage.sqlite.models import (
    KnowledgeSource as DBKnowledgeSource,
    SyncRun as DBSyncRun
)
from deepcore.core.acquisition.base import (
    BaseConnector,
    BaseTranslator,
    SyncContext,
    Provenance
)
from deepcore.core.acquisition.ingestion import IngestionService

logger = logging.getLogger("deepcore.acquisition.runtime")

class AcquisitionRuntime:
    """
    Acquisition Runtime. Handles the execution flow of sync cycles:
    - Sets up execution context and sync telemetry records.
    - Manages retry logic and backoffs for connector operations.
    - Feeds connector raw objects to the Translator.
    - Routes translated outputs to the Ingestion Service.
    - Persists cursors and telemetry back to the database.
    """
    def __init__(self, db: Optional[Session] = None, ingestion_service: Optional[IngestionService] = None):
        self.db = db
        self.ingestion_service = ingestion_service

    def run_sync(
        self,
        source_id: int,
        connector: BaseConnector,
        translator: BaseTranslator,
        full_sync: bool = False,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        db: Optional[Session] = None,
        run_uuid: Optional[str] = None
    ) -> DBSyncRun:
        """
        Execute a sync run for a specific knowledge source instance.
        """
        # Resolve active database session and ingestion service
        active_db = db or self.db
        if not active_db:
            raise ValueError("Acquisition failed: Database session is required.")
            
        ingester = self.ingestion_service or IngestionService(active_db)

        # 1. Fetch KnowledgeSource
        source = active_db.query(DBKnowledgeSource).filter(DBKnowledgeSource.id == source_id).first()
        if not source:
            raise ValueError(f"Acquisition failed: KnowledgeSource with ID {source_id} not found.")

        workspace_id = source.workspace_id

        # 2. Parse config and cursor states
        config = json.loads(source.config_json or "{}")
        if not config.get("path"):
            config["path"] = source.location
        if not config.get("location"):
            config["location"] = source.location
        if not config.get("search_path"):
            config["search_path"] = source.location

        cursor_state = json.loads(source.cursor_state or "{}")

        # In a real sync we'd extract credentials from a secure keyring or vault.
        # For the framework, we extract credential overrides if stored in config or vault mock.
        credentials = config.get("credentials", {})

        # 3. Create or resolve SyncRun record
        sync_run = None
        if run_uuid:
            sync_run = active_db.query(DBSyncRun).filter(DBSyncRun.uuid == run_uuid).first()

        if sync_run:
            sync_run.status = "Syncing"
            sync_run.started_at = datetime.now(timezone.utc)
            sync_run.objects_scanned = 0
            sync_run.objects_created = 0
            sync_run.objects_existing = 0
            sync_run.objects_updated = 0
            sync_run.objects_missing = 0
            sync_run.progress = 0.0
            sync_run.telemetry_json = "{}"
        else:
            import uuid
            sync_run = DBSyncRun(
                uuid=run_uuid or str(uuid.uuid4()),
                workspace_id=workspace_id,
                source_id=source.id,
                provider=source.provider_id,
                source_location=source.location,
                started_at=datetime.now(timezone.utc),
                status="Syncing",
                objects_scanned=0,
                objects_created=0,
                objects_existing=0,
                objects_updated=0,
                objects_missing=0,
                progress=0.0,
                telemetry_json="{}"
            )
            active_db.add(sync_run)
            
        active_db.commit()
        active_db.refresh(sync_run)

        # Update source state to Syncing
        source.status = "Syncing"
        active_db.commit()

        # 4. Instantiate SyncContext
        ctx = SyncContext(
            workspace_id=workspace_id,
            source_id=source.id,
            config=config,
            credentials=credentials,
            cursor_state=cursor_state,
            logger=logger
        )

        scanned = 0
        created = 0
        updated = 0
        existing = 0
        telemetry_logs = []

        try:
            # 5. Execute technical discovery with retries
            retry_count = 0
            connector_generator = None
            
            while retry_count <= max_retries:
                try:
                    if full_sync:
                        connector_generator = connector.discover(ctx)
                    else:
                        connector_generator = connector.sync(ctx)
                    break
                except Exception as e:
                    retry_count += 1
                    telemetry_logs.append(f"Retry {retry_count}/{max_retries} due to error: {str(e)}")
                    if retry_count > max_retries:
                        raise e
                    sleep_time = backoff_factor ** retry_count
                    time.sleep(sleep_time)

            # 6. Stream and Normalise Payloads
            if connector_generator:
                for raw_obj in connector_generator:
                    if ctx.is_cancelled:
                        telemetry_logs.append("Sync run was cancelled by context.")
                        break

                    scanned += 1
                    
                    # Generate explicit, unique provenance ID
                    ext_id = raw_obj.get("external_id")
                    if not ext_id:
                        # Fallback to deterministic name if external ID is missing
                        ext_id = raw_obj.get("id") or raw_obj.get("path") or f"gen_{scanned}"

                    provenance = Provenance(
                        connector_id=source.provider_id,
                        provider_id=source.provider_id,
                        source_system=source.name,
                        external_id=str(ext_id),
                        sync_run_id=sync_run.uuid
                    )

                    # Pure Translation
                    translated = translator.translate_object(raw_obj, provenance)

                    # Ingestion Mapping Layer (Amendment 1)
                    if not isinstance(translated, dict):
                        if hasattr(translated, "uid") and hasattr(translated, "interval"):
                            event_dump = translated.model_dump()
                            event_dump["root_path"] = source.location # Map root_path for delete detection
                            # Flatten/serialize temporal attributes to registry fields
                            translated = {
                                "object_type": "event",
                                "title": translated.summary,
                                "source_system": provenance.source_system,
                                "external_id": translated.uid,
                                "location": translated.location.title if translated.location else "Unknown Location",
                                "description": translated.description or f"Calendar event: {translated.summary}",
                                "status": "active",
                                "metadata_json": json.dumps(event_dump),
                                "provider_version": "calendar_v1.0",
                                "content_hash": None, # Will be computed by IngestionService
                                "raw_text": f"{translated.summary}\n{translated.description or ''}"
                            }
                        elif hasattr(translated, "uid") and hasattr(translated, "mime_type"):
                            # Map DiscoveredArtifact (Discovery Classification Invariant)
                            translated = self._map_discovery_artifact_to_registry(
                                translated, provenance, source.location
                            )
                        else:
                            # Fallback if unknown domain model type is received
                            translated = translated.model_dump()

                    # Ingest via Ingestion Boundary Service
                    db_obj = ingester.ingest_object(
                        raw_translation=translated,
                        provenance=provenance,
                        workspace_id=workspace_id,
                        source_id=source.id
                    )

                    # Compare state to increment telemetry counts
                    # Check if DB object was created vs updated
                    # SQLite models don't tell us directly unless we track new vs modified
                    # Let's inspect objects in session or compare updated_at / created_at.
                    is_new = getattr(db_obj, "_is_new", False)
                    is_updated = getattr(db_obj, "_is_updated", False)
                    if is_new:
                        created += 1
                    elif is_updated:
                        updated += 1
                    else:
                        existing += 1

                    # Update SyncRun Progress
                    sync_run.objects_scanned = scanned
                    sync_run.objects_created = created
                    sync_run.objects_updated = updated
                    sync_run.objects_existing = existing
                    sync_run.progress = 0.5 + (0.5 * (scanned / max(scanned, 100))) # Mock progress curve
                    active_db.commit()

            # 7. Post-Sync Completion Tasks
            source.cursor_state = json.dumps(ctx.cursor_state)
            source.status = "Healthy"
            
            sync_run.status = "success"
            sync_run.finished_at = datetime.now(timezone.utc)
            sync_run.progress = 1.0
            sync_run.telemetry_json = json.dumps({
                "retries": retry_count,
                "logs": telemetry_logs,
                "completed_at": datetime.now(timezone.utc).isoformat()
            })
            active_db.commit()

        except Exception as err:
            tb = traceback.format_exc()
            logger.error(f"Sync run failed: {err}\n{tb}")
            
            # Update States
            source.status = "Error"
            sync_run.status = "failed"
            sync_run.finished_at = datetime.now(timezone.utc)
            sync_run.error_message = str(err)
            sync_run.errors_json = json.dumps({
                "error": str(err),
                "traceback": tb,
                "logs": telemetry_logs
            })
            active_db.commit()

        active_db.refresh(sync_run)
        return sync_run

    def _classify_discovery_artifact(self, mime_type: str, location: str) -> str:
        """
        Final Amendment: Simple default classifier mapping DiscoveredArtifact to Registry types.
        Can be extracted later into a standalone component.
        """
        import os
        ext = os.path.splitext(location)[1].lower()
        if mime_type == "text/markdown" or ext in [".md", ".markdown"]:
            return "note"
        return "file"

    def _map_discovery_artifact_to_registry(
        self, artifact: Any, provenance: Provenance, source_location: str
    ) -> Dict[str, Any]:
        """
        Maps a DiscoveredArtifact into a database-compliant RegistryObjectCreate payload.
        """
        import os
        # 1. Decide classification (note vs file)
        object_type = self._classify_discovery_artifact(artifact.mime_type, artifact.location)
        
        # 2. Extract raw text if it is a markdown note (for indexing)
        raw_text = ""
        if object_type == "note" and os.path.exists(artifact.location):
            try:
                with open(artifact.location, "r", encoding="utf-8", errors="replace") as f:
                    raw_text = f.read()
            except Exception:
                pass

        # 3. Build metadata payload
        meta_dict = artifact.model_dump()
        meta_dict["root_path"] = source_location  # Map root_path for delete detection

        return {
            "object_type": object_type,
            "title": artifact.title,
            "source_system": provenance.source_system,
            "external_id": artifact.uid,
            "location": artifact.location,
            "description": f"Ambiently discovered {object_type}: {artifact.title}",
            "status": "active",
            "metadata_json": json.dumps(meta_dict),
            "provider_version": "spotlight_v1.0",
            "content_hash": None,  # Will be computed by IngestionService
            "raw_text": raw_text
        }
