import json
import os
from datetime import datetime, timezone
from typing import List, Optional, Any

from deepcore.core.providers.base import BaseProvider
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObjectCreate

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
            "provider_version": "markdown_v0.1"
        }

    def sync(self, registry_service: RegistryService, *args, **kwargs) -> List[Any]:
        """Perform duplicate checking, registry updates, and sync stats counting."""
        raw_files = self.discover()
        self.scanned_count = len(raw_files)
        self.new_count = 0
        self.existing_count = 0

        synced_objects = []

        for raw in raw_files:
            rel_path = raw["relative_path"]
            
            # Check existing duplicates by relative path identity
            existing = registry_service.list_objects(filters={
                "source_system": "markdown",
                "external_id": rel_path
            })
            
            if existing:
                self.existing_count += 1
                continue

            try:
                normalized = self.normalize(raw)
                obj_create = RegistryObjectCreate(**normalized)
                db_obj = registry_service.register_object(obj_create)
                synced_objects.append(db_obj)
                self.new_count += 1
            except Exception:
                # Silently skip file if DB registration fails
                continue

        return synced_objects
