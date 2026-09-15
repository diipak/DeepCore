import os
from typing import List, Optional
from deepcore.core.objects.schemas import PreviewArtifact, PreviewArtifactType
from deepcore.core.acquisition.base import SyncContext

class PreviewService:
    def _get_connector_and_context(self, provider_id: str, location: str, config: Optional[dict] = None):
        from deepcore.runtime.composition import get_application
        app = get_application()
        
        # Map provider ID for backwards compatibility
        pid = provider_id.lower()
        if pid in ("markdown", "markdown_provider"):
            pid = "filesystem"
            
        connector_class = app.acquisition_manager.get_connector_class(pid)
        connector = connector_class()
        
        # Prepare context config
        full_config = dict(config or {})
        full_config["path"] = location
        full_config["location"] = location
        full_config["search_path"] = location
        full_config["mock_file_path"] = location
        
        ctx = SyncContext(
            workspace_id=1,
            source_id=0,
            config=full_config,
            credentials={}
        )
        return connector, ctx

    def validate_source(self, provider_id: str, location: str, config: Optional[dict] = None) -> None:
        """
        Validate source readability and basic constraints by calling health check.
        Raises HTTP-friendly errors (ValueError, PermissionError, FileNotFoundError) if invalid.
        """
        connector, ctx = self._get_connector_and_context(provider_id, location, config)
        
        health_status = connector.health(ctx)
        if health_status.state == "CRITICAL":
            msg = health_status.message or ""
            if "not exist" in msg.lower():
                raise FileNotFoundError(msg)
            elif "permission" in msg.lower():
                raise PermissionError(msg)
            else:
                raise ValueError(msg)

    def estimate_import(self, provider_id: str, location: str, config: Optional[dict] = None) -> int:
        """
        Estimate total count of artifacts by counting connector.discover() objects.
        """
        self.validate_source(provider_id, location, config)
        connector, ctx = self._get_connector_and_context(provider_id, location, config)
        count = 0
        try:
            for _ in connector.discover(ctx):
                count += 1
        except Exception:
            pass
        return count

    def enumerate_preview(self, provider_id: str, location: str, config: Optional[dict] = None, limit: int = 10) -> List[PreviewArtifact]:
        """
        Enumerate a subset of preview artifacts by calling connector.discover() and mapping to PreviewArtifact.
        """
        self.validate_source(provider_id, location, config)
        connector, ctx = self._get_connector_and_context(provider_id, location, config)
        artifacts = []
        try:
            for raw_obj in connector.discover(ctx):
                name = raw_obj.get("filename") or raw_obj.get("summary") or raw_obj.get("title") or "Unnamed"
                
                # Determine type
                if "start_time" in raw_obj or provider_id.lower() == "calendar":
                    art_type = PreviewArtifactType.EVENT
                else:
                    art_type = PreviewArtifactType.NOTE
                
                # Determine location descriptor
                if "relative_path" in raw_obj:
                    loc_desc = raw_obj["relative_path"]
                elif "absolute_path" in raw_obj:
                    loc_desc = os.path.relpath(raw_obj["absolute_path"], location) if location else raw_obj["absolute_path"]
                elif "location" in raw_obj:
                    loc_val = raw_obj["location"]
                    if isinstance(loc_val, dict):
                        loc_desc = loc_val.get("title") or "Unknown"
                    else:
                        loc_desc = str(loc_val)
                else:
                    loc_desc = raw_obj.get("external_id") or ""
                
                # Determine size
                size_bytes = raw_obj.get("file_size") or raw_obj.get("size") or raw_obj.get("size_bytes")
                if size_bytes is not None:
                    try:
                        size_bytes = int(size_bytes)
                    except ValueError:
                        size_bytes = None
                
                artifacts.append(PreviewArtifact(
                    name=name,
                    type=art_type,
                    location_descriptor=loc_desc,
                    size_bytes=size_bytes
                ))
                
                if len(artifacts) >= limit:
                    break
        except Exception:
            pass
        return artifacts
