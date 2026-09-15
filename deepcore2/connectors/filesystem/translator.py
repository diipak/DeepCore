import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any
from deepcore2.core.acquisition.base import BaseTranslator, Provenance

class MarkdownTranslator(BaseTranslator):
    """
    Pure Invariant Markdown Translator. Normalizes generic file metadata from the
    Filesystem Connector, extracts the file body text, and maps properties to
    a DeepCore note registry schema.
    """
    def translate_object(self, raw_data: Dict[str, Any], provenance: Provenance) -> Dict[str, Any]:
        # Enforce purity invariants: no DB access, no network, no relationship computation
        abs_path = raw_data["absolute_path"]
        rel_path = raw_data["relative_path"]
        filename = raw_data["filename"]
        file_size = raw_data["file_size"]

        title = os.path.splitext(filename)[0]

        # Read file contents locally (file mapping only, no network/DB)
        raw_text = ""
        content_hash = ""
        try:
            if os.path.exists(abs_path):
                with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                    raw_text = f.read()
                # Compute SHA256 of contents
                content_hash = hashlib.sha256(raw_text.encode("utf-8", errors="ignore")).hexdigest()
        except Exception:
            pass

        # If file couldn't be read or hashed, generate hash from metadata
        if not content_hash:
            hash_payload = f"{rel_path}|{file_size}|{raw_data['modified_at_ts']}"
            content_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

        # Format timestamps
        created_str = datetime.fromtimestamp(raw_data["created_at_ts"], timezone.utc).isoformat()
        modified_str = datetime.fromtimestamp(raw_data["modified_at_ts"], timezone.utc).isoformat()

        # Build metadata block
        metadata_payload = {
            "root_path": raw_data.get("root_path", ""),
            "relative_path": rel_path,
            "folder": raw_data["parent_folder"],
            "extension": os.path.splitext(filename)[1],
            "file_size": file_size,
            "created_at": created_str,
            "modified_at": modified_str,
            "viewer_hint": "obsidian_compatible",
            "provider": "filesystem"
        }

        # Return dict mapping directly to RegistryObjectCreate parameters
        return {
            "object_type": "note",
            "title": title,
            "source_system": provenance.source_system,
            "external_id": rel_path,
            "location": abs_path,
            "description": f"Imported markdown note: {title}",
            "status": "active",
            "metadata_json": json.dumps(metadata_payload),
            "provider_version": "filesystem_v1.0",
            "content_hash": content_hash,
            "raw_text": raw_text  # Will be extracted and written by IngestionService
        }
