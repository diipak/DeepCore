from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from deepcore2.storage.sqlite.models import RegistryObject, RegistryRelationship, RegistrySignal, KnowledgeSource, Workspace


class WorkspaceIntegrityValidator:
    """Safe, read-only validation checks verifying workspace invariants."""
    def __init__(self, db: Session, workspace_id: int):
        self.db = db
        self.workspace_id = workspace_id

    def check_workspace_ownership(self) -> dict:
        """Check if any objects or relationships belong to invalid workspaces or if demo notes mixed in Personal."""
        null_ws_count = self.db.query(RegistryObject).filter(RegistryObject.workspace_id == None).count()
        
        # Check if Personal Workspace contains objects from the demo notes directory
        demo_mix_count = 0
        if self.workspace_id == 1:
            demo_mix_count = self.db.query(RegistryObject).filter(
                RegistryObject.workspace_id == 1,
                RegistryObject.location.like("%/demo/markdown/%")
            ).count()

        is_valid = (null_ws_count == 0) and (demo_mix_count == 0)
        return {
            "status": "pass" if is_valid else "fail",
            "message": f"Verified workspace ownership. Null WS objects: {null_ws_count}. Demo files mixed: {demo_mix_count}.",
            "metrics": {"null_workspace_objects": null_ws_count, "demo_files_mixed": demo_mix_count}
        }

    def check_provider_ownership(self) -> dict:
        """Verify that all objects have a valid, non-null provider_id."""
        null_prov_count = self.db.query(RegistryObject).filter(
            RegistryObject.workspace_id == self.workspace_id,
            RegistryObject.provider_id == None
        ).count()
        
        is_valid = (null_prov_count == 0)
        return {
            "status": "pass" if is_valid else "fail",
            "message": f"Verified provider ownership. Objects with missing provider: {null_prov_count}.",
            "metrics": {"null_provider_objects": null_prov_count}
        }

    def check_knowledge_source_ownership(self) -> dict:
        """Verify that object source_id matches the workspace of the source itself (no cross-workspace sources)."""
        cross_source_count = self.db.query(RegistryObject).join(
            KnowledgeSource,
            RegistryObject.source_id == KnowledgeSource.id
        ).filter(
            RegistryObject.workspace_id == self.workspace_id,
            KnowledgeSource.workspace_id != self.workspace_id
        ).count()

        is_valid = (cross_source_count == 0)
        return {
            "status": "pass" if is_valid else "fail",
            "message": f"Verified knowledge source ownership. Cross-workspace source references: {cross_source_count}.",
            "metrics": {"cross_workspace_sources": cross_source_count}
        }

    def check_registry_integrity(self) -> dict:
        """Check general registry consistency, e.g. objects with empty location or titles."""
        empty_title_count = self.db.query(RegistryObject).filter(
            RegistryObject.workspace_id == self.workspace_id,
            (RegistryObject.title == None) | (RegistryObject.title == "")
        ).count()

        is_valid = (empty_title_count == 0)
        return {
            "status": "pass" if is_valid else "fail",
            "message": f"Registry integrity verified. Objects with empty title: {empty_title_count}.",
            "metrics": {"empty_title_objects": empty_title_count}
        }

    def check_relationship_integrity(self) -> dict:
        """Check for cross-workspace relationships or relationships pointing to non-existent objects (orphans)."""
        cross_ws_rel_count = self.db.query(RegistryRelationship).join(
            RegistryObject,
            RegistryObject.id == RegistryRelationship.from_object_id
        ).filter(
            RegistryRelationship.workspace_id == self.workspace_id,
            RegistryObject.workspace_id != self.workspace_id
        ).count()

        orphan_rel_count = self.db.query(RegistryRelationship).filter(
            RegistryRelationship.workspace_id == self.workspace_id,
            ~RegistryRelationship.to_object_id.in_(self.db.query(RegistryObject.id))
        ).count()

        is_valid = (cross_ws_rel_count == 0) and (orphan_rel_count == 0)
        return {
            "status": "pass" if is_valid else "fail",
            "message": f"Relationship integrity checked. Cross-workspace relationships: {cross_ws_rel_count}. Orphan relationships: {orphan_rel_count}.",
            "metrics": {"cross_workspace_relationships": cross_ws_rel_count, "orphan_relationships": orphan_rel_count}
        }

    def check_navigation_consistency(self) -> dict:
        """Verify that relationship targets resolve to existing and active objects."""
        inactive_target_count = self.db.query(RegistryRelationship).join(
            RegistryObject,
            RegistryObject.id == RegistryRelationship.to_object_id
        ).filter(
            RegistryRelationship.workspace_id == self.workspace_id,
            RegistryObject.status != "active"
        ).count()

        is_valid = (inactive_target_count == 0)
        return {
            "status": "pass" if is_valid else "fail",
            "message": f"Navigation consistency checked. Relationships to inactive target objects: {inactive_target_count}.",
            "metrics": {"inactive_target_relationships": inactive_target_count}
        }


class WorkspaceIntegrityRepair:
    """State-modifying routines to repair workspace ownership, orphans, and relations."""
    def __init__(self, db: Session, workspace_id: int):
        self.db = db
        self.workspace_id = workspace_id

    def repair_workspace_ownership(self) -> int:
        """Repair objects improperly placed in this workspace. Deletes demo notes in Personal Workspace."""
        deleted_count = 0
        
        # Historical compatibility cleanup: If Personal Workspace (ID 1) contains demo notes, delete them
        if self.workspace_id == 1:
            query = self.db.query(RegistryObject).filter(
                RegistryObject.workspace_id == 1,
                RegistryObject.location.like("%/demo/markdown/%")
            )
            deleted_count = query.count()
            if deleted_count > 0:
                # Deleting objects will cascade to relationships and signals
                query.delete(synchronize_session=False)
                self.db.commit()
                
        # Repair null workspace_id entries
        null_query = self.db.query(RegistryObject).filter(RegistryObject.workspace_id == None)
        null_count = null_query.count()
        if null_count > 0:
            null_query.update({"workspace_id": 1}, synchronize_session=False)
            self.db.commit()
            
        return deleted_count + null_count

    def repair_orphan_objects(self) -> int:
        """Repair objects whose source reference is invalid by setting source_id to Null."""
        invalid_sources = self.db.query(RegistryObject).filter(
            RegistryObject.workspace_id == self.workspace_id,
            RegistryObject.source_id != None,
            ~RegistryObject.source_id.in_(self.db.query(KnowledgeSource.id))
        )
        count = invalid_sources.count()
        if count > 0:
            invalid_sources.update({"source_id": None}, synchronize_session=False)
            self.db.commit()
        return count

    def repair_invalid_relationships(self) -> int:
        """Delete relationships linking to non-existent objects, crossing workspaces, or targeting inactive objects."""
        # 1. Orphan relationships (target object doesn't exist)
        orphan_rels = self.db.query(RegistryRelationship).filter(
            RegistryRelationship.workspace_id == self.workspace_id,
            ~RegistryRelationship.to_object_id.in_(self.db.query(RegistryObject.id))
        )
        orphan_count = orphan_rels.count()
        if orphan_count > 0:
            orphan_rels.delete(synchronize_session=False)
            self.db.commit()

        # 2. Cross-workspace relationships
        cross_rel_ids = [
            r.id for r in self.db.query(RegistryRelationship.id).join(
                RegistryObject,
                RegistryObject.id == RegistryRelationship.from_object_id
            ).filter(
                RegistryRelationship.workspace_id == self.workspace_id,
                RegistryObject.workspace_id != self.workspace_id
            ).all()
        ]
        cross_count = len(cross_rel_ids)
        if cross_count > 0:
            self.db.query(RegistryRelationship).filter(
                RegistryRelationship.id.in_(cross_rel_ids)
            ).delete(synchronize_session=False)
            self.db.commit()

        # 3. Relationships pointing to inactive objects
        inactive_rel_ids = [
            r.id for r in self.db.query(RegistryRelationship.id).join(
                RegistryObject,
                RegistryObject.id == RegistryRelationship.to_object_id
            ).filter(
                RegistryRelationship.workspace_id == self.workspace_id,
                RegistryObject.status != "active"
            ).all()
        ]
        inactive_count = len(inactive_rel_ids)
        if inactive_count > 0:
            self.db.query(RegistryRelationship).filter(
                RegistryRelationship.id.in_(inactive_rel_ids)
            ).delete(synchronize_session=False)
            self.db.commit()

        return orphan_count + cross_count + inactive_count


class WorkspaceIntegrityService:
    """Public orchestration interface composing Validator and Repair engines."""
    def __init__(self, db: Session, workspace_id: int):
        self.db = db
        self.workspace_id = workspace_id
        self.validator = WorkspaceIntegrityValidator(db, workspace_id)
        self.repair_engine = WorkspaceIntegrityRepair(db, workspace_id)

    def validate_integrity(self) -> dict:
        """Run all safe integrity checks and return a unified health report."""
        checks = {
            "workspace_ownership": self.validator.check_workspace_ownership(),
            "provider_ownership": self.validator.check_provider_ownership(),
            "knowledge_source_ownership": self.validator.check_knowledge_source_ownership(),
            "registry_integrity": self.validator.check_registry_integrity(),
            "relationship_integrity": self.validator.check_relationship_integrity(),
            "navigation_consistency": self.validator.check_navigation_consistency(),
        }
        
        is_healthy = all(c["status"] == "pass" for c in checks.values())
        return {
            "is_healthy": is_healthy,
            "status": "healthy" if is_healthy else "degraded",
            "checks": checks
        }

    def repair_integrity(self) -> dict:
        """Execute all state-modifying repairs and return counts of repaired items."""
        repaired_workspace = self.repair_engine.repair_workspace_ownership()
        repaired_orphans = self.repair_engine.repair_orphan_objects()
        repaired_relations = self.repair_engine.repair_invalid_relationships()
        
        return {
            "repaired_workspace_objects": repaired_workspace,
            "repaired_orphan_references": repaired_orphans,
            "repaired_invalid_relationships": repaired_relations,
            "total_repaired": repaired_workspace + repaired_orphans + repaired_relations
        }
