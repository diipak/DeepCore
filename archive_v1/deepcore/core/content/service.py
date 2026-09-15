import os
import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Union
from sqlalchemy import or_
from sqlalchemy.orm import Session
from deepcore.storage.sqlite.models import (
    RegistryObject as DBRegistryObject,
    ContentIndex as DBContentIndex,
    get_utc_now
)
from deepcore.core.registry.service import RegistryService
from deepcore.core.utils.text import extract_search_keywords

class ContentService:
    def __init__(self, db: Session):
        self.db = db

    def index_object(self, object_id: int) -> Optional[DBContentIndex]:
        """Index a single registry object by loading its file contents if supported."""
        obj = self.db.query(DBRegistryObject).filter(DBRegistryObject.id == object_id).first()
        if not obj or obj.status != "active":
            return None

        # Only process .md files (Markdown Content Handling)
        if not obj.location or not obj.location.lower().endswith(".md"):
            return None

        # Read file gracefully
        try:
            with open(obj.location, "r", encoding="utf-8", errors="replace") as f:
                raw_text = f.read()
        except FileNotFoundError:
            # Handle missing files gracefully
            return None
        except Exception:
            # Handle encoding/permissions/other errors gracefully
            return None

        word_count = len(raw_text.split())
        content_hash = hashlib.sha256(raw_text.encode("utf-8", errors="ignore")).hexdigest()

        # Avoid duplicate indexing: skip if same content_hash exists for this object_id
        existing = self.db.query(DBContentIndex).filter(
            DBContentIndex.object_id == obj.id,
            DBContentIndex.content_hash == content_hash
        ).first()
        if existing:
            return existing

        # Ensure one registry object has one content index entry initially (update or create)
        idx_entry = self.db.query(DBContentIndex).filter(DBContentIndex.object_id == obj.id).first()
        if idx_entry:
            idx_entry.raw_text = raw_text
            idx_entry.content_hash = content_hash
            idx_entry.word_count = word_count
            idx_entry.indexed_at = get_utc_now()
        else:
            idx_entry = DBContentIndex(
                object_id=obj.id,
                content_type="markdown",
                raw_text=raw_text,
                content_hash=content_hash,
                word_count=word_count,
                index_version="content_v0.1"
            )
            self.db.add(idx_entry)

        self.db.commit()
        self.db.refresh(idx_entry)
        return idx_entry

    def index_all_active_objects(self) -> dict:
        """Scan all active registry objects, index them if supported, and return stats."""
        active_objects = self.db.query(DBRegistryObject).filter(DBRegistryObject.status == "active").all()
        
        scanned = len(active_objects)
        indexed = 0
        skipped = 0

        for obj in active_objects:
            if not obj.location or not obj.location.lower().endswith(".md"):
                skipped += 1
                continue

            if not os.path.exists(obj.location):
                skipped += 1
                continue

            try:
                with open(obj.location, "r", encoding="utf-8", errors="replace") as f:
                    raw_text = f.read()
            except Exception:
                skipped += 1
                continue

            content_hash = hashlib.sha256(raw_text.encode("utf-8", errors="ignore")).hexdigest()

            # Avoid duplicate indexing using content_hash
            existing = self.db.query(DBContentIndex).filter(
                DBContentIndex.object_id == obj.id,
                DBContentIndex.content_hash == content_hash
            ).first()
            if existing:
                skipped += 1
                continue

            # Run indexing
            res = self.index_object(obj.id)
            if res:
                indexed += 1
            else:
                skipped += 1

        return {
            "scanned": scanned,
            "indexed": indexed,
            "skipped": skipped
        }

    def get_content(self, object_id_or_uuid: Union[int, str]) -> Optional[DBContentIndex]:
        """Retrieve indexed content for a specific registry object by ID or UUID."""
        registry_service = RegistryService(self.db)
        obj = registry_service.get_object(object_id_or_uuid)
        if not obj:
            return None
        return self.db.query(DBContentIndex).filter(DBContentIndex.object_id == obj.id).first()

    def search_content(self, query: str) -> List[Tuple[DBRegistryObject, DBContentIndex]]:
        """Search raw_text using case-insensitive LIKE (ilike) matching on extracted keywords. Returns structured DB objects."""
        keywords = extract_search_keywords(query)
        if not keywords:
            return []

        kw_conditions = [DBContentIndex.raw_text.ilike(f"%{kw}%") for kw in keywords]
        return self.db.query(DBRegistryObject, DBContentIndex).join(
            DBContentIndex, DBRegistryObject.id == DBContentIndex.object_id
        ).filter(
            DBRegistryObject.status == "active",
            or_(*kw_conditions)
        ).all()
