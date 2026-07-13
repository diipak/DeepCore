from typing import List, Optional, Union
from sqlalchemy import func
from sqlalchemy.orm import Session
from deepcore.storage.sqlite.models import RegistryObject as DBRegistryObject, SyncRun as DBSyncRun
from deepcore.core.objects.schemas import RegistryObjectCreate, RegistryObjectUpdate, SyncRunCreate

class RegistryService:
    def __init__(self, db: Session):
        self.db = db

    def _get_query(self, object_id_or_uuid: Union[int, str]):
        """Helper to query a registry object by integer ID or string UUID."""
        if isinstance(object_id_or_uuid, int):
            return self.db.query(DBRegistryObject).filter(DBRegistryObject.id == object_id_or_uuid)
        elif isinstance(object_id_or_uuid, str):
            if object_id_or_uuid.isdigit():
                return self.db.query(DBRegistryObject).filter(DBRegistryObject.id == int(object_id_or_uuid))
            return self.db.query(DBRegistryObject).filter(DBRegistryObject.uuid == object_id_or_uuid)
        else:
            raise ValueError("Invalid identifier type")

    def register_object(self, obj_data: RegistryObjectCreate) -> DBRegistryObject:
        """Register a new object in the database."""
        db_obj = DBRegistryObject(**obj_data.model_dump())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def get_object(self, object_id_or_uuid: Union[int, str]) -> Optional[DBRegistryObject]:
        """Retrieve a specific object by ID or UUID."""
        return self._get_query(object_id_or_uuid).first()

    def list_objects(self, filters: Optional[dict] = None) -> List[DBRegistryObject]:
        """List objects, optionally filtering by specific fields."""
        query = self.db.query(DBRegistryObject)
        if filters:
            for key, value in filters.items():
                if hasattr(DBRegistryObject, key) and value is not None:
                    query = query.filter(getattr(DBRegistryObject, key) == value)
        return query.all()

    def update_object(self, object_id_or_uuid: Union[int, str], update_data: RegistryObjectUpdate) -> DBRegistryObject:
        """Update fields of an existing registry object."""
        db_obj = self._get_query(object_id_or_uuid).first()
        if not db_obj:
            raise ValueError(f"RegistryObject with identifier '{object_id_or_uuid}' not found")
        
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(db_obj, key, value)
            
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def archive_object(self, object_id_or_uuid: Union[int, str]) -> DBRegistryObject:
        """Archive a registry object by setting its status to 'archived'."""
        db_obj = self._get_query(object_id_or_uuid).first()
        if not db_obj:
            raise ValueError(f"RegistryObject with identifier '{object_id_or_uuid}' not found")
            
        db_obj.status = "archived"
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def get_statistics(self) -> dict:
        """Calculate and return registry statistics."""
        total = self.db.query(DBRegistryObject).count()
        
        by_type_query = self.db.query(
            DBRegistryObject.object_type, 
            func.count(DBRegistryObject.id)
        ).group_by(DBRegistryObject.object_type).all()
        by_type = {r[0]: r[1] for r in by_type_query}
        
        by_source_query = self.db.query(
            DBRegistryObject.source_system, 
            func.count(DBRegistryObject.id)
        ).group_by(DBRegistryObject.source_system).all()
        by_source = {r[0]: r[1] for r in by_source_query}
        
        return {
            "total_objects": total,
            "by_type": by_type,
            "by_source": by_source
        }

    def find_by_hash(self, content_hash: str) -> Optional[DBRegistryObject]:
        """Find a registry object by its content hash."""
        if not content_hash:
            return None
        return self.db.query(DBRegistryObject).filter(DBRegistryObject.content_hash == content_hash).first()

    def record_sync_run(self, sync_run_data: SyncRunCreate) -> DBSyncRun:
        """Record a sync run record in the database."""
        db_run = DBSyncRun(**sync_run_data.model_dump())
        self.db.add(db_run)
        self.db.commit()
        self.db.refresh(db_run)
        return db_run

    def list_sync_runs(self) -> List[DBSyncRun]:
        """List all sync runs, ordered by started_at descending."""
        return self.db.query(DBSyncRun).order_by(DBSyncRun.started_at.desc()).all()

    def mark_missing_objects(self, source_system: str, root_path: str, active_external_ids: List[str]) -> int:
        """Mark active objects of source_system in root_path not in active_external_ids as missing."""
        # Find active objects in this source system and root path that are not in active_external_ids
        query = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.source_system == source_system,
            DBRegistryObject.status == "active",
            func.json_extract(DBRegistryObject.metadata_json, '$.root_path') == root_path,
            ~DBRegistryObject.external_id.in_(active_external_ids)
        )
        missing_objects = query.all()
        for obj in missing_objects:
            obj.status = "missing"
        if missing_objects:
            self.db.commit()
        return len(missing_objects)

    def search_objects(
        self,
        query: str,
        object_type: Optional[str] = None,
        source_system: Optional[str] = None,
        limit: int = 20
    ) -> List[DBRegistryObject]:
        """Search active registry objects using case-insensitive LIKE matching on title, description, or location."""
        query_str = f"%{query}%"
        db_query = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.status == "active",
            (
                DBRegistryObject.title.ilike(query_str) |
                DBRegistryObject.description.ilike(query_str) |
                DBRegistryObject.location.ilike(query_str)
            )
        )
        if object_type:
            db_query = db_query.filter(DBRegistryObject.object_type == object_type)
        if source_system:
            db_query = db_query.filter(DBRegistryObject.source_system == source_system)
            
        return db_query.limit(limit).all()

    def get_object_details(self, id_or_uuid: Union[int, str]) -> Optional[dict]:
        """Retrieve full details of a registry object by ID or UUID."""
        obj = self.get_object(id_or_uuid)
        if not obj:
            return None

        # Fetch connected concepts
        from deepcore.storage.sqlite.models import RegistryRelationship as DBRegistryRelationship
        
        concepts_query = self.db.query(DBRegistryObject).join(
            DBRegistryRelationship,
            DBRegistryObject.id == DBRegistryRelationship.to_object_id
        ).filter(
            DBRegistryRelationship.from_object_id == obj.id,
            DBRegistryRelationship.relationship_type == "mentions",
            DBRegistryObject.object_type == "concept"
        ).all()
        
        connected_concepts = [
            {"id": c.id, "uuid": c.uuid, "title": c.title}
            for c in concepts_query
        ]

        referenced_query = self.db.query(DBRegistryObject).join(
            DBRegistryRelationship,
            DBRegistryObject.id == DBRegistryRelationship.to_object_id
        ).filter(
            DBRegistryRelationship.from_object_id == obj.id,
            DBRegistryRelationship.relationship_type == "references"
        ).all()

        referenced_objects = [
            {
                "id": r.id,
                "uuid": r.uuid,
                "title": r.title,
                "object_type": r.object_type,
                "location": r.location
            }
            for r in referenced_query
        ]

        # Fetch relationships where current object is the source
        import json
        rel_query = self.db.query(
            DBRegistryRelationship,
            DBRegistryObject
        ).join(
            DBRegistryObject,
            DBRegistryObject.id == DBRegistryRelationship.to_object_id
        ).filter(
            DBRegistryRelationship.from_object_id == obj.id
        ).all()
        
        relationships = []
        for rel, target in rel_query:
            try:
                evidence = json.loads(rel.evidence_json) if rel.evidence_json else {}
            except Exception:
                evidence = rel.evidence_json
                
            relationships.append({
                "uuid": rel.uuid,
                "target_object_uuid": target.uuid,
                "target_object_title": target.title,
                "target_object_type": target.object_type,
                "relationship_type": rel.relationship_type,
                "confidence": rel.confidence,
                "evidence": evidence,
                "created_at": rel.created_at,
                "updated_at": rel.updated_at
            })

        return {
            "uuid": obj.uuid,
            "type": obj.object_type,
            "title": obj.title,
            "source": obj.source_system,
            "location": obj.location,
            "status": obj.status,
            "metadata_json": obj.metadata_json,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "connected_concepts": connected_concepts,
            "referenced_objects": referenced_objects,
            "relationships": relationships
        }


    def recent_objects(self, limit: int = 10) -> List[DBRegistryObject]:
        """Return newest active objects ordered by created_at descending."""
        return self.db.query(DBRegistryObject).filter(
            DBRegistryObject.status == "active"
        ).order_by(
            DBRegistryObject.created_at.desc()
        ).limit(limit).all()

    def recent_memories(self, limit: int = 10) -> List[DBRegistryObject]:
        """Return newest active human-created knowledge sources ordered by created_at descending."""
        return self.db.query(DBRegistryObject).filter(
            DBRegistryObject.status == "active",
            DBRegistryObject.object_type.in_(["note", "video", "document"])
        ).order_by(
            DBRegistryObject.created_at.desc()
        ).limit(limit).all()

    def get_dashboard_counts(self) -> dict:
        """Return counts for the dashboard: memory_count, concept_count, approved_concepts, relationship_count."""
        from deepcore.storage.sqlite.models import RegistryRelationship as DBRegistryRelationship
        
        memory_count = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.status == "active",
            DBRegistryObject.object_type.in_(["note", "video", "document"])
        ).count()
        
        concept_count = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.object_type == "concept",
            DBRegistryObject.status != "merged"
        ).count()
        
        approved_concepts = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.object_type == "concept",
            DBRegistryObject.status != "merged",
            func.json_extract(DBRegistryObject.metadata_json, '$.concept_status') == "approved"
        ).count()
        
        relationship_count = self.db.query(DBRegistryRelationship).count()
        
        return {
            "memory_count": memory_count,
            "concept_count": concept_count,
            "approved_concepts": approved_concepts,
            "relationship_count": relationship_count
        }

    def get_recently_connected(self, limit: int = 5) -> List[dict]:
        """Return parent memory objects with their active connected child objects counts."""
        from deepcore.storage.sqlite.models import RegistryRelationship as DBRegistryRelationship
        
        parents_query = self.db.query(
            DBRegistryObject
        ).join(
            DBRegistryRelationship,
            DBRegistryObject.id == DBRegistryRelationship.from_object_id
        ).filter(
            DBRegistryRelationship.relationship_type == "references",
            DBRegistryObject.status == "active"
        ).group_by(
            DBRegistryObject.id
        ).order_by(
            DBRegistryObject.updated_at.desc()
        ).limit(limit).all()

        recently_connected = []
        for parent in parents_query:
            children = self.db.query(DBRegistryObject).join(
                DBRegistryRelationship,
                DBRegistryObject.id == DBRegistryRelationship.to_object_id
            ).filter(
                DBRegistryRelationship.from_object_id == parent.id,
                DBRegistryRelationship.relationship_type == "references",
                DBRegistryObject.status == "active"
            ).all()
            
            total_count = len(children)
            repo_count = sum(1 for c in children if c.object_type == "repository")
            video_count = sum(1 for c in children if c.object_type == "video")
            doc_count = sum(1 for c in children if c.object_type == "document")
            
            recently_connected.append({
                "uuid": parent.uuid,
                "title": parent.title,
                "object_type": parent.object_type,
                "total_connected": total_count,
                "repo_connected": repo_count,
                "video_connected": video_count,
                "doc_connected": doc_count
            })
            
        return recently_connected

    def get_connected_concepts(self, object_id: int) -> List[DBRegistryObject]:
        """Retrieve active concepts mentioned by the given object ID."""
        from deepcore.storage.sqlite.models import RegistryRelationship as DBRegistryRelationship
        return self.db.query(DBRegistryObject).join(
            DBRegistryRelationship,
            DBRegistryObject.id == DBRegistryRelationship.to_object_id
        ).filter(
            DBRegistryRelationship.from_object_id == object_id,
            DBRegistryRelationship.relationship_type == "mentions",
            DBRegistryObject.object_type == "concept",
            DBRegistryObject.status == "active"
        ).all()

    def get_referenced_memories(self, object_id: int) -> List[DBRegistryObject]:
        """Retrieve active memories referenced by the given object ID."""
        from deepcore.storage.sqlite.models import RegistryRelationship as DBRegistryRelationship
        return self.db.query(DBRegistryObject).join(
            DBRegistryRelationship,
            DBRegistryObject.id == DBRegistryRelationship.to_object_id
        ).filter(
            DBRegistryRelationship.from_object_id == object_id,
            DBRegistryRelationship.relationship_type == "references",
            DBRegistryObject.status == "active"
        ).all()

    def get_objects_mentioning_concepts(self, concept_ids: List[int]) -> List[DBRegistryObject]:
        """Retrieve active objects that mention any of the specified concept IDs."""
        from deepcore.storage.sqlite.models import RegistryRelationship as DBRegistryRelationship
        if not concept_ids:
            return []
        return self.db.query(DBRegistryObject).join(
            DBRegistryRelationship,
            DBRegistryObject.id == DBRegistryRelationship.from_object_id
        ).filter(
            DBRegistryRelationship.to_object_id.in_(concept_ids),
            DBRegistryRelationship.relationship_type == "mentions",
            DBRegistryObject.status == "active"
        ).all()

    def get_objects_referencing_objects(self, object_ids: List[int]) -> List[DBRegistryObject]:
        """Retrieve active objects that reference any of the specified object IDs."""
        from deepcore.storage.sqlite.models import RegistryRelationship as DBRegistryRelationship
        if not object_ids:
            return []
        return self.db.query(DBRegistryObject).join(
            DBRegistryRelationship,
            DBRegistryObject.id == DBRegistryRelationship.from_object_id
        ).filter(
            DBRegistryRelationship.to_object_id.in_(object_ids),
            DBRegistryRelationship.relationship_type == "references",
            DBRegistryObject.status == "active"
        ).all()

    def get_concept_connection_count(self, concept_id: int) -> int:
        """Retrieve the total connection count for a concept."""
        from deepcore.storage.sqlite.models import RegistryRelationship as DBRegistryRelationship
        return self.db.query(DBRegistryRelationship).filter(
            DBRegistryRelationship.to_object_id == concept_id,
            DBRegistryRelationship.relationship_type == "mentions"
        ).count()

