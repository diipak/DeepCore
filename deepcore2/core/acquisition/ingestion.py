import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from deepcore2.storage.sqlite.models import (
    RegistryObject as DBRegistryObject,
    ContentIndex as DBContentIndex
)
from deepcore2.core.acquisition.base import Provenance

class IngestionService:
    """
    Ingestion Service Boundary. Responsible for validating schemas, enforcing
    immutable provenance requirements, checking duplicate content hashes, managing
    database transactions, and indexing content.
    """
    def __init__(self, db: Session):
        self.db = db

    def ingest_object(
        self,
        raw_translation: Dict[str, Any],
        provenance: Provenance,
        workspace_id: int = 1,
        source_id: Optional[int] = None
    ) -> DBRegistryObject:
        """
        Ingest a normalized object translation into the DeepCore Registry.
        Enforces transaction boundaries and the purity of incoming data.
        """
        # 1. Enforce Mandatory Provenance Validation
        if not provenance:
            raise ValueError("Ingestion failed: Explicit provenance is mandatory.")

        # 2. Schema Validation
        object_type = raw_translation.get("object_type")
        title = raw_translation.get("title")
        if not object_type:
            raise ValueError("Ingestion failed: 'object_type' is a required field.")
        if not title or not title.strip():
            raise ValueError("Ingestion failed: 'title' is a required, non-empty field.")

        # Extract values
        location = raw_translation.get("location")
        description = raw_translation.get("description")
        provider_version = raw_translation.get("provider_version", "1.0.0")
        raw_text = raw_translation.get("raw_text", "")

        # Incorporate provenance directly inside metadata_json (which is a serializable dictionary)
        metadata_dict = raw_translation.get("metadata_json") or {}
        if isinstance(metadata_dict, str):
            try:
                metadata_dict = json.loads(metadata_dict)
            except Exception:
                metadata_dict = {}

        # Enforce that provenance metadata is stored in a dedicated block
        metadata_dict["provenance"] = provenance.model_dump()
        # Convert timestamp to ISO string format in JSON
        if "acquisition_timestamp" in metadata_dict["provenance"] and isinstance(metadata_dict["provenance"]["acquisition_timestamp"], datetime):
            metadata_dict["provenance"]["acquisition_timestamp"] = metadata_dict["provenance"]["acquisition_timestamp"].isoformat()

        metadata_json_str = json.dumps(metadata_dict)

        # 3. Calculate / Set Content Hash
        content_hash = raw_translation.get("content_hash")
        if not content_hash:
            # Generate deterministic hash based on stable source attributes and text contents
            hash_payload = f"{object_type}|{title}|{location or ''}|{description or ''}|{raw_text}"
            content_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

        # 4. Deduplication Look-up
        existing_obj = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.workspace_id == workspace_id,
            DBRegistryObject.source_system == provenance.source_system,
            DBRegistryObject.external_id == provenance.external_id
        ).first()

        utc_now = datetime.now(timezone.utc)

        if existing_obj:
            # If Content Hash is identical, skip actual write, just update timestamp
            if existing_obj.content_hash == content_hash:
                existing_obj.updated_at = utc_now
                self.db.commit()
                existing_obj._is_new = False
                existing_obj._is_updated = False
                return existing_obj

            # If Hash is different, update the record fields (provenance fields are immutable)
            existing_obj.title = title
            existing_obj.location = location
            existing_obj.description = description
            existing_obj.content_hash = content_hash
            existing_obj.metadata_json = metadata_json_str
            existing_obj.status = "active"
            existing_obj.updated_at = utc_now
            existing_obj._is_new = False
            existing_obj._is_updated = True
            db_obj = existing_obj
        else:
            # Create a brand new Registry Object
            db_obj = DBRegistryObject(
                workspace_id=workspace_id,
                source_id=source_id,
                object_type=object_type,
                title=title,
                source_system=provenance.source_system,
                external_id=provenance.external_id,
                location=location,
                description=description,
                status="active",
                metadata_json=metadata_json_str,
                provider_version=provider_version,
                content_hash=content_hash,
                provider_id=provenance.provider_id,
                created_at=utc_now,
                updated_at=utc_now
            )
            self.db.add(db_obj)
            self.db.flush()  # Populate db_obj.id
            db_obj._is_new = True
            db_obj._is_updated = False

        # 5. Index Content if text is provided
        if raw_text:
            word_count = len(raw_text.split())
            text_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
            
            existing_idx = self.db.query(DBContentIndex).filter(
                DBContentIndex.object_id == db_obj.id
            ).first()

            if existing_idx:
                existing_idx.raw_text = raw_text
                existing_idx.content_hash = text_hash
                existing_idx.word_count = word_count
                existing_idx.indexed_at = utc_now
            else:
                new_idx = DBContentIndex(
                    object_id=db_obj.id,
                    content_type="text",
                    raw_text=raw_text,
                    content_hash=text_hash,
                    word_count=word_count,
                    indexed_at=utc_now,
                    index_version="content_v0.1"
                )
                self.db.add(new_idx)

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
