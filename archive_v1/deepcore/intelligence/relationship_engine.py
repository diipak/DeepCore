import os
import re
import json
from typing import List, Dict, Any, Set, Optional
from sqlalchemy.orm import Session
from deepcore.storage.sqlite.models import (
    RegistryObject as DBRegistryObject,
    RegistryRelationship as DBRegistryRelationship,
    ContentIndex as DBContentIndex,
    generate_uuid,
    get_utc_now
)
from deepcore.core.objects.schemas import RelationshipType
from deepcore.core.providers.base import SyncResult

class RelationshipEngine:
    """
    Intelligence stage that processes deterministic relationships between Canonical Objects.
    Designed to consume canonical metadata and indexed content, separating data discovery
    from the raw provider-specific details where practical.
    """
    def __init__(self, db: Session, workspace_id: Optional[int] = None):
        self.db = db
        if workspace_id is None:
            from deepcore.storage.sqlite.models import Workspace
            personal = db.query(Workspace).filter(Workspace.name == "Personal Workspace").first()
            if not personal:
                personal = Workspace(name="Personal Workspace")
                db.add(personal)
                db.commit()
                db.refresh(personal)
            self.workspace_id = personal.id
        else:
            self.workspace_id = workspace_id

    def process_sync_result(self, sync_result: SyncResult, pipeline_result: Optional[Any] = None) -> int:
        """
        Incrementally process relationships for objects affected by the sync.
        Cleans up stale relationships for modified/missing/archived objects.
        """
        # Determine affected objects: created or updated
        affected_objects = sync_result.created + sync_result.updated
        
        processed_count = 0
        for obj in affected_objects:
            if obj.object_type == "note":
                self.evaluate_object(obj, pipeline_result)
                processed_count += 1
                
        # Purge relationships for deleted/missing/archived objects
        all_affected_ids = [obj.id for obj in affected_objects]
        missing_or_archived_ids = [obj.id for obj in sync_result.missing]
        
        # Also clean up relationships for any note that became inactive
        inactive_objects = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.id.in_(all_affected_ids),
            DBRegistryObject.status != "active"
        ).all()
        inactive_ids = [obj.id for obj in inactive_objects] + missing_or_archived_ids

        if inactive_ids:
            self.db.query(DBRegistryRelationship).filter(
                (DBRegistryRelationship.from_object_id.in_(inactive_ids)) |
                (DBRegistryRelationship.to_object_id.in_(inactive_ids))
            ).filter(
                DBRegistryRelationship.relationship_source == "relationship_engine"
            ).delete(synchronize_session=False)
            self.db.commit()

        return processed_count

    def evaluate_object(self, obj: DBRegistryObject, pipeline_result: Optional[Any] = None) -> None:
        """
        Evaluate a single object against all other active objects in the registry.
        Removes pre-existing relations for this object and recreates current ones.
        """
        # 1. Clean up existing relationships created by relationship_engine involving this object
        self.db.query(DBRegistryRelationship).filter(
            (DBRegistryRelationship.from_object_id == obj.id) |
            (DBRegistryRelationship.to_object_id == obj.id)
        ).filter(
            DBRegistryRelationship.relationship_source == "relationship_engine"
        ).delete(synchronize_session=False)
        self.db.commit()

        # If object is not active, do not compute new relationships (it was cleaned up above)
        if obj.status != "active":
            return

        # Get all other active objects in the registry
        other_objects = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.workspace_id == obj.workspace_id,
            DBRegistryObject.id != obj.id,
            DBRegistryObject.status == "active"
        ).all()

        # Retrieve canonical raw text from the content index
        raw_text = self._get_raw_text(obj)
        props = self._extract_properties(raw_text, obj)

        # Cache for other objects' properties during evaluation
        other_props_cache = {}
        created_triples = set()

        for other in other_objects:
            relationships = []

            # 1. DUPLICATE: Content hash matches (100% confidence in deterministic match)
            if obj.content_hash and other.content_hash and obj.content_hash == other.content_hash:
                evidence = {
                    "type": "identical_hash",
                    "detail": f"Identical content hash: {obj.content_hash}",
                    "location": obj.location,
                    "producing_stage": "relationship_engine"
                }
                relationships.append((RelationshipType.DUPLICATE, 1.0, evidence))

            # 2. SAME_FOLDER: Reside in same parent folder (100% confidence in match)
            folder_obj = self._get_folder_path(obj)
            folder_other = self._get_folder_path(other)
            if folder_obj and folder_other and folder_obj == folder_other:
                evidence = {
                    "type": "shared_folder",
                    "detail": f"Both objects reside in folder: {folder_obj}",
                    "location": obj.location,
                    "producing_stage": "relationship_engine"
                }
                relationships.append((RelationshipType.SAME_FOLDER, 1.0, evidence))

            # 3. SAME_SOURCE: Synced from the same provider/system
            if obj.source_system == other.source_system:
                evidence = {
                    "type": "shared_source",
                    "detail": f"Both objects synced from source: {obj.source_system}",
                    "location": obj.location,
                    "producing_stage": "relationship_engine"
                }
                relationships.append((RelationshipType.SAME_SOURCE, 1.0, evidence))

            # 4. SAME_PROJECT: Shared project tags from frontmatter or hashtags
            other_raw_text = self._get_raw_text(other)
            if other.id not in other_props_cache:
                other_props_cache[other.id] = self._extract_properties(other_raw_text, other)
            other_props = other_props_cache[other.id]

            shared_tags = props["tags"].intersection(other_props["tags"])
            if shared_tags:
                shared_tag_str = ", ".join(sorted(list(shared_tags)))
                evidence = {
                    "type": "shared_project",
                    "detail": f"Both objects share project tags: {shared_tag_str}",
                    "location": obj.location,
                    "producing_stage": "relationship_engine"
                }
                relationships.append((RelationshipType.SAME_PROJECT, 1.0, evidence))

            # 5. REFERENCES / REFERENCED_BY: Explicit markdown links
            is_referencing = self._matches_reference(other, props["links"])
            if is_referencing:
                evidence = {
                    "type": "markdown_link",
                    "detail": f"Link found in note: [[{other.title}]]",
                    "location": obj.location,
                    "producing_stage": "relationship_engine"
                }
                relationships.append((RelationshipType.REFERENCES, 1.0, evidence))

            is_referenced_by = self._matches_reference(obj, other_props["links"])
            if is_referenced_by:
                evidence = {
                    "type": "markdown_link",
                    "detail": f"Referenced in note: [[{other.title}]]",
                    "location": other.location,
                    "producing_stage": "relationship_engine"
                }
                relationships.append((RelationshipType.REFERENCED_BY, 1.0, evidence))

            # 6. CHILD_OF / PARENT_OF: Explicit hierarchy tags
            if props["parent"] and self._matches_name_or_path(other, props["parent"]):
                evidence = {
                    "type": "parent_frontmatter",
                    "detail": f"Explicit parent frontmatter in {obj.title}: {other.title}",
                    "location": obj.location,
                    "producing_stage": "relationship_engine"
                }
                relationships.append((RelationshipType.CHILD_OF, 1.0, evidence))

            if other_props["parent"] and self._matches_name_or_path(obj, other_props["parent"]):
                evidence = {
                    "type": "parent_frontmatter",
                    "detail": f"Explicit parent frontmatter in {other.title}: {obj.title}",
                    "location": other.location,
                    "producing_stage": "relationship_engine"
                }
                relationships.append((RelationshipType.PARENT_OF, 1.0, evidence))

            # 7. VERSION_OF: Versioning relationships
            if props["version_of"] and self._matches_name_or_path(other, props["version_of"]):
                evidence = {
                    "type": "version_frontmatter",
                    "detail": f"Explicit version_of frontmatter in {obj.title}: {other.title}",
                    "location": obj.location,
                    "producing_stage": "relationship_engine"
                }
                relationships.append((RelationshipType.VERSION_OF, 1.0, evidence))

            if other_props["version_of"] and self._matches_name_or_path(obj, other_props["version_of"]):
                evidence = {
                    "type": "version_frontmatter",
                    "detail": f"Explicit version_of frontmatter in {other.title}: {obj.title}",
                    "location": other.location,
                    "producing_stage": "relationship_engine"
                }
                relationships.append((RelationshipType.VERSION_OF, 1.0, evidence))

            # Commit relationships symmetrically with their inverse complements
            for rel_type, confidence, evidence in relationships:
                # Complements mapping
                inverse_map = {
                    RelationshipType.REFERENCES: RelationshipType.REFERENCED_BY,
                    RelationshipType.REFERENCED_BY: RelationshipType.REFERENCES,
                    RelationshipType.CHILD_OF: RelationshipType.PARENT_OF,
                    RelationshipType.PARENT_OF: RelationshipType.CHILD_OF,
                    RelationshipType.SAME_FOLDER: RelationshipType.SAME_FOLDER,
                    RelationshipType.SAME_SOURCE: RelationshipType.SAME_SOURCE,
                    RelationshipType.SAME_PROJECT: RelationshipType.SAME_PROJECT,
                    RelationshipType.DUPLICATE: RelationshipType.DUPLICATE,
                    RelationshipType.VERSION_OF: RelationshipType.VERSION_OF
                }

                inv_type = inverse_map.get(rel_type, rel_type)

                # Direct relationship: obj -> rel_type -> other
                triple_1 = (obj.id, other.id, rel_type.value)
                if triple_1 not in created_triples:
                    new_rel = DBRegistryRelationship(
                        uuid=generate_uuid(),
                        workspace_id=obj.workspace_id,
                        from_object_id=obj.id,
                        to_object_id=other.id,
                        relationship_type=rel_type.value,
                        confidence=confidence, # represents deterministic validity (1.0)
                        evidence_json=json.dumps(evidence),
                        relationship_source="relationship_engine",
                        created_at=get_utc_now(),
                        updated_at=get_utc_now()
                    )
                    self.db.add(new_rel)
                    created_triples.add(triple_1)
 
                # Complement relationship: other -> inv_type -> obj
                triple_2 = (other.id, obj.id, inv_type.value)
                if triple_2 not in created_triples:
                    inv_evidence = evidence.copy()
                    # Location points to target in the context of the source
                    inv_evidence["location"] = other.location if rel_type == RelationshipType.REFERENCES else obj.location
                    new_rel_inv = DBRegistryRelationship(
                        uuid=generate_uuid(),
                        workspace_id=obj.workspace_id,
                        from_object_id=other.id,
                        to_object_id=obj.id,
                        relationship_type=inv_type.value,
                        confidence=confidence,
                        evidence_json=json.dumps(inv_evidence),
                        relationship_source="relationship_engine",
                        created_at=get_utc_now(),
                        updated_at=get_utc_now()
                    )
                    self.db.add(new_rel_inv)
                    created_triples.add(triple_2)

        self.db.commit()

        # Identify unresolved links for broken reference detection in Signal Engine
        if pipeline_result is not None:
            resolved_link_targets = set()
            for link in props["links"]:
                link_lower = link.lower()
                for other in other_objects:
                    other_title_lower = other.title.lower()
                    other_base = os.path.splitext(os.path.basename(other.external_id))[0].lower() if other.external_id else ""
                    if link_lower == other_title_lower or link_lower == other_base:
                        resolved_link_targets.add(link)
                        break
            unresolved_links = props["links"] - resolved_link_targets
            pipeline_result.context[f"unresolved_links:{obj.id}"] = list(unresolved_links)

    def _get_raw_text(self, obj: DBRegistryObject) -> str:
        """Fetch raw content from canonical index if available, otherwise read location."""
        idx = self.db.query(DBContentIndex).filter(DBContentIndex.object_id == obj.id).first()
        if idx:
            return idx.raw_text
        if obj.location and os.path.exists(obj.location):
            try:
                with open(obj.location, "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            except Exception:
                pass
        return ""

    def _get_folder_path(self, obj: DBRegistryObject) -> Optional[str]:
        if obj.location:
            return os.path.dirname(os.path.abspath(obj.location))
        if obj.metadata_json:
            try:
                meta = json.loads(obj.metadata_json)
                if "folder" in meta:
                    return meta["folder"]
            except Exception:
                pass
        return None

    def _extract_properties(self, raw_text: str, obj: DBRegistryObject) -> Dict[str, Any]:
        """Parse frontmatter and markdown body to extract links, tags, parent hierarchy, and version relationships."""
        frontmatter = {}
        content_lines = []
        
        lines = raw_text.splitlines()
        in_frontmatter = False
        frontmatter_lines = []
        
        if lines and lines[0].strip() == "---":
            in_frontmatter = True
            for line in lines[1:]:
                if line.strip() == "---":
                    in_frontmatter = False
                    continue
                if in_frontmatter:
                    frontmatter_lines.append(line)
                else:
                    content_lines.append(line)
        else:
            content_lines = lines

        for line in frontmatter_lines:
            if ":" in line:
                parts = line.split(":", 1)
                key = parts[0].strip()
                val = parts[1].strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                
                if val.startswith("[") and val.endswith("]"):
                    items = [item.strip().strip('"').strip("'") for item in val[1:-1].split(",") if item.strip()]
                    frontmatter[key] = items
                else:
                    frontmatter[key] = val

        body_text = "\n".join(content_lines)

        # Extract wikilinks and standard links
        wikilinks = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', raw_text)
        links = {w.strip() for w in wikilinks if w.strip()}
        
        md_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', raw_text)
        for text, target in md_links:
            target = target.strip()
            if not target.startswith(("http://", "https://", "mailto:", "#")):
                target_name = os.path.splitext(os.path.basename(target))[0]
                if target_name:
                    links.add(target_name)

        # Extract project tags
        tags = set()
        for key in ("tags", "tag", "projects", "project"):
            if key in frontmatter:
                val = frontmatter[key]
                if isinstance(val, list):
                    for item in val:
                        tags.add(item.strip().lower().lstrip("#"))
                elif isinstance(val, str):
                    for item in re.split(r'[,; ]+', val):
                        tags.add(item.strip().lower().lstrip("#"))

        body_tags = re.findall(r'#([a-zA-Z][a-zA-Z0-9_-]*)', body_text)
        for tag in body_tags:
            tags.add(tag.strip().lower())

        parent = frontmatter.get("parent")
        if parent:
            parent = os.path.splitext(os.path.basename(parent))[0].strip()

        version_of = frontmatter.get("version_of")
        if version_of:
            version_of = os.path.splitext(os.path.basename(version_of))[0].strip()

        return {
            "links": links,
            "tags": tags,
            "parent": parent,
            "version_of": version_of
        }

    def _matches_reference(self, other: DBRegistryObject, links: Set[str]) -> bool:
        other_title_lower = other.title.lower()
        if other_title_lower in {l.lower() for l in links}:
            return True
        if other.external_id:
            basename = os.path.splitext(os.path.basename(other.external_id))[0]
            if basename.lower() in {l.lower() for l in links}:
                return True
        return False

    def _matches_name_or_path(self, target: DBRegistryObject, name_or_path: str) -> bool:
        name_lower = name_or_path.lower()
        if target.title.lower() == name_lower:
            return True
        if target.external_id:
            basename = os.path.splitext(os.path.basename(target.external_id))[0]
            if basename.lower() == name_lower:
                return True
        return False
