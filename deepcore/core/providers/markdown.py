import json
import os
import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Any

from deepcore.core.providers.base import BaseProvider
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObjectCreate, RegistryObjectUpdate, SyncRunCreate

def calculate_sha256(filepath: str) -> str:
    """Calculate the SHA256 checksum of a file's contents."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""

class MarkdownProvider(BaseProvider):
    @classmethod
    def can_handle(cls, content: Any) -> bool:
        """Return True if content is a string representing a valid local directory path."""
        if isinstance(content, str):
            try:
                return os.path.isdir(content)
            except Exception:
                return False
        return False

    def __init__(self, root_path: str):
        """Initialize MarkdownProvider with the root path of the notes folder."""
        self.root_path = root_path
        self.scanned_count = 0
        self.new_count = 0
        self.existing_count = 0
        self.updated_count = 0
        self.missing_count = 0

    def discover(self, *args, **kwargs) -> List[dict]:
        """Recursively scan root_path for *.md files, ignoring hidden directories and files."""
        discovered = []
        if not os.path.isdir(self.root_path):
            return discovered

        for root, dirs, files in os.walk(self.root_path):
            # Prune hidden and excluded directories in-place to avoid searching them
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('.git', '.obsidian', '.trash')]
            
            for file in files:
                if file.startswith('.') or not file.lower().endswith('.md'):
                    continue

                abs_path = os.path.abspath(os.path.join(root, file))
                rel_path = os.path.relpath(abs_path, self.root_path)
                
                try:
                    stat = os.stat(abs_path)
                    try:
                        created_at = stat.st_birthtime
                    except AttributeError:
                        created_at = stat.st_ctime
                    modified_at = stat.st_mtime
                    file_size = stat.st_size
                except Exception:
                    # Graceful fallback if stat fails due to file changes or permissions
                    try:
                        created_at = os.path.getctime(abs_path)
                        modified_at = os.path.getmtime(abs_path)
                        file_size = os.path.getsize(abs_path)
                    except Exception:
                        created_at = datetime.now(timezone.utc).timestamp()
                        modified_at = datetime.now(timezone.utc).timestamp()
                        file_size = 0

                parent_folder = os.path.basename(os.path.dirname(abs_path))
                
                discovered.append({
                    "absolute_path": abs_path,
                    "relative_path": rel_path,
                    "filename": file,
                    "parent_folder": parent_folder,
                    "file_size": file_size,
                    "created_at_ts": created_at,
                    "modified_at_ts": modified_at
                })

        return discovered

    def normalize(self, raw_data: dict) -> dict:
        """Convert discovered markdown file dictionary to Registry Object dictionary."""
        filename = raw_data["filename"]
        title = os.path.splitext(filename)[0]
        
        # Convert timestamps to UTC ISO strings
        created_str = datetime.fromtimestamp(raw_data["created_at_ts"], timezone.utc).isoformat()
        modified_str = datetime.fromtimestamp(raw_data["modified_at_ts"], timezone.utc).isoformat()

        meta_payload = {
            "root_path": self.root_path,
            "relative_path": raw_data["relative_path"],
            "folder": raw_data["parent_folder"],
            "extension": ".md",
            "file_size": raw_data["file_size"],
            "created_at": created_str,
            "modified_at": modified_str,
            "viewer_hint": "obsidian_compatible",
            "provider": "markdown"
        }

        return {
            "object_type": "note",
            "title": title,
            "source_system": "markdown",
            "external_id": raw_data["relative_path"],
            "location": raw_data["absolute_path"],
            "description": None,
            "status": "active",
            "metadata_json": json.dumps(meta_payload),
            "provider_version": "markdown_v0.1",
            "content_hash": raw_data.get("content_hash")
        }

    def sync(self, registry_service: RegistryService, *args, **kwargs) -> List[Any]:
        """Perform duplicate checking, registry updates, and sync stats counting."""
        started_at = datetime.now(timezone.utc)
        status = "success"
        errors = []

        raw_files = self.discover()
        self.scanned_count = len(raw_files)
        self.new_count = 0
        self.existing_count = 0
        self.updated_count = 0
        self.missing_count = 0

        synced_objects = []
        active_external_ids = [raw["relative_path"] for raw in raw_files]

        # 1. Detect and mark missing objects first, so rename matching works against missing status
        try:
            self.missing_count = registry_service.mark_missing_objects("markdown", self.root_path, active_external_ids)
        except Exception as e:
            errors.append(f"Failed to mark missing objects: {e}")
            status = "failed"

        # Process scanned files
        for raw in raw_files:
            abs_path = raw["absolute_path"]
            rel_path = raw["relative_path"]
            
            # Calculate file hash
            file_hash = calculate_sha256(abs_path)
            raw["content_hash"] = file_hash

            # 2. Priority 1: Match by source_system + external_id
            existing_by_path = registry_service.list_objects(filters={
                "source_system": "markdown",
                "external_id": rel_path
            })
            
            if existing_by_path:
                db_obj = existing_by_path[0]
                self.existing_count += 1
                
                needs_update = False
                update_fields = {}
                if db_obj.status == "missing":
                    update_fields["status"] = "active"
                    self.missing_count = max(0, self.missing_count - 1)
                    needs_update = True
                if db_obj.content_hash != file_hash:
                    update_fields["content_hash"] = file_hash
                    needs_update = True
                
                if needs_update:
                    try:
                        db_obj = registry_service.update_object(db_obj.id, RegistryObjectUpdate(**update_fields))
                        self.updated_count += 1
                        # Process embedded resources
                        from deepcore.core.capture.service import CaptureService
                        capture_service = CaptureService(registry_service.db)
                        capture_service.process_embedded_resources(db_obj, set())
                    except Exception as e:
                        errors.append(f"Failed to update note {rel_path}: {e}")
                        status = "failed"
                continue

            # 3. Priority 2: Match by content_hash + existing status missing (Move/Rename)
            existing_by_hash = registry_service.find_by_hash(file_hash)
            if existing_by_hash and existing_by_hash.source_system == "markdown" and existing_by_hash.status == "missing":
                # moved or renamed detected
                new_title = os.path.splitext(raw["filename"])[0]
                update_fields = {
                    "external_id": rel_path,
                    "location": abs_path,
                    "title": new_title,
                    "status": "active"
                }
                
                try:
                    db_obj = registry_service.update_object(existing_by_hash.id, RegistryObjectUpdate(**update_fields))
                    self.existing_count += 1
                    self.updated_count += 1
                    self.missing_count = max(0, self.missing_count - 1)
                    # Process embedded resources
                    from deepcore.core.capture.service import CaptureService
                    capture_service = CaptureService(registry_service.db)
                    capture_service.process_embedded_resources(db_obj, set())
                except Exception as e:
                    errors.append(f"Failed to update moved note {rel_path}: {e}")
                    status = "failed"
                continue

            # 4. No match or hash-match on active (Separate Copy) -> register new
            try:
                normalized = self.normalize(raw)
                obj_create = RegistryObjectCreate(**normalized)
                db_obj = registry_service.register_object(obj_create)
                synced_objects.append(db_obj)
                self.new_count += 1
                # Process embedded resources
                from deepcore.core.capture.service import CaptureService
                capture_service = CaptureService(registry_service.db)
                capture_service.process_embedded_resources(db_obj, set())
            except Exception as e:
                errors.append(f"Failed to register note {rel_path}: {e}")
                status = "failed"

        finished_at = datetime.now(timezone.utc)

        # 6. Record sync run
        try:
            sync_run = SyncRunCreate(
                provider="markdown",
                source_location=self.root_path,
                started_at=started_at,
                finished_at=finished_at,
                status=status,
                objects_scanned=self.scanned_count,
                objects_created=self.new_count,
                objects_existing=self.existing_count,
                objects_updated=self.updated_count,
                objects_missing=self.missing_count,
                errors_json=json.dumps(errors) if errors else None
            )
            registry_service.record_sync_run(sync_run)
        except Exception as e:
            # Shield sync output from sync logging failures
            pass

        return synced_objects
