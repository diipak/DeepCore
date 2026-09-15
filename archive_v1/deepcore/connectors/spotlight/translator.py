import os
import hashlib
import mimetypes
from datetime import datetime, timezone
from typing import Dict, Any

from deepcore.core.acquisition.base import BaseTranslator, Provenance
from deepcore.connectors.spotlight.schema import DiscoveredArtifact

class SpotlightTranslator(BaseTranslator):
    """
    Spotlight Discovery Translator. Converts raw file indexing records
    into canonical DiscoveredArtifact domain models.
    """
    def translate_object(self, raw_data: Dict[str, Any], provenance: Provenance) -> DiscoveredArtifact:
        path = raw_data["absolute_path"]
        
        # 1. Deterministic UID from location
        uid = hashlib.sha256(path.encode("utf-8")).hexdigest()

        # 2. Extract standard properties
        filename = raw_data["filename"]
        title = os.path.splitext(filename)[0]

        # 3. Guess MIME Type
        mime, _ = mimetypes.guess_type(path)
        if not mime:
            ext = os.path.splitext(filename)[1].lower()
            if ext in [".md", ".markdown"]:
                mime = "text/markdown"
            elif ext == ".pdf":
                mime = "application/pdf"
            else:
                mime = "application/octet-stream"

        # 4. Standardize Timestamps
        mod_ts = raw_data["modified_at_ts"]
        mod_str = datetime.fromtimestamp(mod_ts, timezone.utc).isoformat()

        # Return canonical domain object
        return DiscoveredArtifact(
            uid=uid,
            title=title,
            location=path,
            mime_type=mime,
            modified_time=mod_str,
            tags=raw_data.get("tags") or [],
            size_bytes=raw_data.get("file_size", 0)
        )
