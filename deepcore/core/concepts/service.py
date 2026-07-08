import json
import re
from typing import List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session
from deepcore.storage.sqlite.models import (
    RegistryObject as DBRegistryObject,
    RegistryRelationship as DBRegistryRelationship,
    ContentIndex as DBContentIndex
)

STOP_WORDS = {
    "the", "and", "a", "of", "to", "is", "in", "that", "it", "on", "for", "this", "with", 
    "as", "are", "be", "by", "an", "at", "from", "or", "was", "were", "which", "but", "not",
    "system", "data", "project", "file", "user", "new", "good",
    "january", "february", "march", "april", "may", "june", "july", "august", "september",
    "october", "november", "december"
}

VALID_CONCEPT_TYPES = {"tool", "technology", "project", "person", "organization", "unknown"}

def is_technical_term(word: str) -> bool:
    """Check if a word is a technical term (CamelCase, ALLCAPS, containing numbers)."""
    # Strip common punctuation
    w = word.strip(".,;:!?()[]{}'\"*`_")
    if not w.isalnum():
        return False
    
    # 1. Words containing numbers (e.g. GPT4)
    has_letter = any(c.isalpha() for c in w)
    has_digit = any(c.isdigit() for c in w)
    if has_letter and has_digit:
        return True
        
    # 2. ALLCAPS abbreviations (length >= 3, e.g. RAG, MLX)
    if w.isupper() and len(w) >= 3:
        return True
        
    # 3. CamelCase / PascalCase
    # Must start with uppercase, contain at least one lowercase letter, and at least one uppercase letter after index 0.
    if w[0].isupper() and any(c.islower() for c in w):
        if any(c.isupper() for c in w[1:]):
            return True
            
    return False

class ConceptService:
    def __init__(self, db: Session):
        self.db = db

    def _ensure_governance_metadata(self, obj: DBRegistryObject) -> DBRegistryObject:
        """Migrate concept metadata on-the-fly to include governance fields if missing."""
        if not obj or obj.object_type != "concept":
            return obj
            
        try:
            metadata = json.loads(obj.metadata_json) if obj.metadata_json else {}
        except Exception:
            metadata = {}
            
        updated = False
        if "concept_status" not in metadata:
            metadata["concept_status"] = "candidate"
            updated = True
        if "concept_type" not in metadata:
            metadata["concept_type"] = "unknown"
            updated = True
            
        if updated:
            obj.metadata_json = json.dumps(metadata)
            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)
            
        return obj

    def extract_from_object(self, object_id: int) -> dict:
        """Extract candidate concepts from a registry object's indexed raw text, creating concept objects and relationships."""
        obj = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.id == object_id,
            DBRegistryObject.status == "active"
        ).first()
        if not obj:
            return {"concepts_created": 0, "relationships_created": 0}

        content_index = self.db.query(DBContentIndex).filter(DBContentIndex.object_id == object_id).first()
        if not content_index or not content_index.raw_text:
            return {"concepts_created": 0, "relationships_created": 0}

        raw_text = content_index.raw_text
        candidates = {}  # normalized_key -> {"title": original_title, "methods": set(), "count": int}

        # --- A. Markdown Headings ---
        lines = raw_text.splitlines()
        for line in lines:
            m = re.match(r'^#+\s+(.+)$', line)
            if m:
                heading = m.group(1).strip()
                heading_clean = heading.strip("`*_-")
                if len(heading_clean) < 3:
                    continue
                norm = heading_clean.lower().replace(" ", "").replace("-", "").replace("_", "")
                if norm in STOP_WORDS:
                    continue
                if norm not in candidates:
                    candidates[norm] = {"title": heading_clean, "methods": set(), "count": 0}
                candidates[norm]["methods"].add("heading")

        # --- B. Technical Term Patterns ---
        words = re.findall(r'\b[a-zA-Z0-9_-]+\b', raw_text)
        for w in words:
            if is_technical_term(w):
                norm = w.lower().replace(" ", "").replace("-", "").replace("_", "")
                if norm in STOP_WORDS:
                    continue
                if len(w) < 3:
                    continue
                if norm not in candidates:
                    candidates[norm] = {"title": w, "methods": set(), "count": 0}
                candidates[norm]["methods"].add("technical_term")

        # --- C. Repeated Capitalized Phrases ---
        phrase_pattern = re.compile(r'\b[A-Z][a-zA-Z0-9]*(\s+[A-Z][a-zA-Z0-9]*)*\b')
        phrases = [m.group(0) for m in phrase_pattern.finditer(raw_text)]
        for p in phrases:
            p_clean = p.strip()
            if len(p_clean) < 3:
                continue
            norm = p_clean.lower().replace(" ", "").replace("-", "").replace("_", "")
            if norm in STOP_WORDS:
                continue
            if norm not in candidates:
                candidates[norm] = {"title": p_clean, "methods": set(), "count": 0}
            candidates[norm]["methods"].add("frequency")

        # Now count actual occurrences for each candidate and filter those that don't meet frequency minimum if frequency was their only source
        valid_candidates = {}
        for norm, info in candidates.items():
            # Exact occurrence count (case-insensitive)
            # Find occurrences as whole words
            escaped_title = re.escape(info["title"])
            occurrences = len(re.findall(r'\b' + escaped_title + r'\b', raw_text, re.IGNORECASE))
            
            # If "frequency" is the only method, it must appear at least 2 times
            if info["methods"] == {"frequency"} and occurrences < 2:
                continue
            
            info["count"] = occurrences
            valid_candidates[norm] = info

        concepts_created = 0
        relationships_created = 0

        # Create or reuse concepts and link them
        for norm_key, info in valid_candidates.items():
            # 1. Search for existing concept using logical identity (normalized_key)
            existing_concept = self.db.query(DBRegistryObject).filter(
                DBRegistryObject.object_type == "concept",
                func.json_extract(DBRegistryObject.metadata_json, '$.normalized_key') == norm_key
            ).first()

            if existing_concept:
                self._ensure_governance_metadata(existing_concept)
                concept_obj = existing_concept
            else:
                # Create a new concept registry object
                concept_obj = DBRegistryObject(
                    object_type="concept",
                    title=info["title"],
                    source_system="deepcore",
                    provider_version="concept_v0.1",
                    status="active",
                    metadata_json=json.dumps({
                        "normalized_key": norm_key,
                        "concept_status": "candidate",
                        "concept_type": "unknown"
                    })
                )
                self.db.add(concept_obj)
                self.db.commit()
                self.db.refresh(concept_obj)
                concepts_created += 1

            # 2. Check and establish relationship
            existing_rel = self.db.query(DBRegistryRelationship).filter(
                DBRegistryRelationship.from_object_id == object_id,
                DBRegistryRelationship.to_object_id == concept_obj.id,
                DBRegistryRelationship.relationship_type == "mentions"
            ).first()

            if not existing_rel:
                evidence = {
                    "extractor": "concept_v0.1",
                    "methods": sorted(list(info["methods"])),
                    "occurrences": info["count"]
                }
                new_rel = DBRegistryRelationship(
                    from_object_id=object_id,
                    to_object_id=concept_obj.id,
                    relationship_type="mentions",
                    confidence=1.0,
                    evidence_json=json.dumps(evidence),
                    relationship_source="concept_v0.1"
                )
                self.db.add(new_rel)
                self.db.commit()
                relationships_created += 1

        return {
            "concepts_created": concepts_created,
            "relationships_created": relationships_created
        }

    def extract_all(self) -> dict:
        """Process all active indexed registry objects to extract concepts and create relationships."""
        # Find active objects that have indexed content
        indexed_objects = self.db.query(DBRegistryObject).join(
            DBContentIndex, DBRegistryObject.id == DBContentIndex.object_id
        ).filter(
            DBRegistryObject.status == "active"
        ).all()

        scanned = len(indexed_objects)
        total_concepts = 0
        total_relationships = 0

        for obj in indexed_objects:
            res = self.extract_from_object(obj.id)
            total_concepts += res["concepts_created"]
            total_relationships += res["relationships_created"]

        return {
            "scanned": scanned,
            "concepts_created": total_concepts,
            "relationships_created": total_relationships
        }

    def list_concepts(self, limit: int = 50, show_ignored: bool = False) -> List[Tuple[DBRegistryObject, int]]:
        """Return active concepts ordered by connection (relationship) count descending."""
        # 1. Start query from concept table
        query = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.object_type == "concept",
            DBRegistryObject.status != "merged"
        )

        # 2. Apply filters on concept object's metadata_json
        if not show_ignored:
            query = query.filter(
                (func.json_extract(DBRegistryObject.metadata_json, '$.concept_status') != "ignored") |
                (func.json_extract(DBRegistryObject.metadata_json, '$.concept_status').is_(None))
            )

        # 3. Join relationships for connection count
        query = query.join(
            DBRegistryRelationship,
            DBRegistryObject.id == DBRegistryRelationship.to_object_id
        ).filter(
            DBRegistryRelationship.relationship_type == "mentions"
        ).with_entities(
            DBRegistryObject,
            func.count(DBRegistryRelationship.id).label("connection_count")
        )

        results = query.group_by(
            DBRegistryObject.id
        ).order_by(
            func.count(DBRegistryRelationship.id).desc(),
            DBRegistryObject.title.asc()
        ).limit(limit).all()

        migrated_results = []
        for obj, count in results:
            self._ensure_governance_metadata(obj)
            migrated_results.append((obj, count))

        return migrated_results

    def get_concept_by_name(self, name: str) -> Optional[DBRegistryObject]:
        """Find an active concept registry object by title name (logical normalized key matching)."""
        norm_key = name.lower().replace(" ", "").replace("-", "").replace("_", "")
        obj = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.object_type == "concept",
            func.json_extract(DBRegistryObject.metadata_json, '$.normalized_key') == norm_key
        ).first()

        if obj:
            self._ensure_governance_metadata(obj)

        return obj

    def get_connected_memories(self, concept_id: int) -> List[DBRegistryObject]:
        """Get active registry objects connected to this concept."""
        # Ensure we only fetch memories if the concept exists and is not merged
        concept = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.id == concept_id,
            DBRegistryObject.object_type == "concept",
            DBRegistryObject.status != "merged"
        ).first()
        if not concept:
            return []

        return self.db.query(DBRegistryObject).join(
            DBRegistryRelationship,
            DBRegistryObject.id == DBRegistryRelationship.from_object_id
        ).filter(
            DBRegistryRelationship.to_object_id == concept_id,
            DBRegistryRelationship.relationship_type == "mentions",
            DBRegistryObject.status == "active"
        ).all()

    def ignore_concept(self, name: str) -> DBRegistryObject:
        """Mark a concept's status as ignored in its metadata."""
        concept = self.get_concept_by_name(name)
        if not concept:
            raise ValueError(f"Concept '{name}' not found")
            
        try:
            metadata = json.loads(concept.metadata_json) if concept.metadata_json else {}
        except Exception:
            metadata = {}
            
        metadata["concept_status"] = "ignored"
        concept.metadata_json = json.dumps(metadata)
        self.db.add(concept)
        self.db.commit()
        self.db.expire_all()
        concept = self.db.get(DBRegistryObject, concept.id)
        return concept


    def approve_concept(self, name: str, concept_type: Optional[str] = None) -> DBRegistryObject:
        """Mark a concept's status as approved and optionally update its type."""
        concept = self.get_concept_by_name(name)
        if not concept:
            raise ValueError(f"Concept '{name}' not found")
            
        try:
            metadata = json.loads(concept.metadata_json) if concept.metadata_json else {}
        except Exception:
            metadata = {}
            
        metadata["concept_status"] = "approved"
        
        if concept_type:
            if concept_type not in VALID_CONCEPT_TYPES:
                raise ValueError(f"Invalid concept type '{concept_type}'. Allowed: {', '.join(sorted(VALID_CONCEPT_TYPES))}")
            metadata["concept_type"] = concept_type
            
        concept.metadata_json = json.dumps(metadata)
        self.db.add(concept)
        self.db.commit()
        self.db.expire_all()
        concept = self.db.get(DBRegistryObject, concept.id)
        return concept


    def merge_concepts(self, source_name: str, target_name: str) -> Tuple[DBRegistryObject, DBRegistryObject]:
        """Merge a source concept into a target concept, rerouting relationships cleanly with duplicate/evidence safety."""
        source = self.get_concept_by_name(source_name)
        if not source:
            raise ValueError(f"Source concept '{source_name}' not found")
            
        target = self.get_concept_by_name(target_name)
        if not target:
            raise ValueError(f"Target concept '{target_name}' not found")
            
        if source.id == target.id:
            raise ValueError("Cannot merge a concept into itself")
            
        # 1. Update source status and metadata
        source.status = "merged"
        try:
            source_meta = json.loads(source.metadata_json) if source.metadata_json else {}
        except Exception:
            source_meta = {}
        source_meta["merged_into"] = target.id
        source.metadata_json = json.dumps(source_meta)
        self.db.add(source)
        
        # 2. Reroute relationships pointing to source
        relationships = self.db.query(DBRegistryRelationship).filter(
            DBRegistryRelationship.to_object_id == source.id
        ).all()
        
        for rel in relationships:
            existing_rel = self.db.query(DBRegistryRelationship).filter(
                DBRegistryRelationship.from_object_id == rel.from_object_id,
                DBRegistryRelationship.to_object_id == target.id,
                DBRegistryRelationship.relationship_type == rel.relationship_type
            ).first()
            
            if existing_rel:
                # Merge evidence
                try:
                    target_evidence = json.loads(existing_rel.evidence_json) if existing_rel.evidence_json else {}
                except Exception:
                    target_evidence = {}
                    
                try:
                    source_evidence = json.loads(rel.evidence_json) if rel.evidence_json else {}
                except Exception:
                    source_evidence = {}
                
                # Combine methods
                target_methods = set(target_evidence.get("methods", []))
                source_methods = set(source_evidence.get("methods", []))
                merged_methods = sorted(list(target_methods.union(source_methods)))
                
                # Sum occurrences
                target_occurrences = target_evidence.get("occurrences", 0)
                source_occurrences = source_evidence.get("occurrences", 0)
                merged_occurrences = target_occurrences + source_occurrences
                
                # Record merge origin
                merge_origins = target_evidence.get("merge_origins", [])
                source_key = source_meta.get("normalized_key", source.title)
                merge_origins.append({
                    "merged_concept_id": source.id,
                    "merged_concept_title": source.title,
                    "merged_concept_key": source_key,
                    "relationship_id": rel.id,
                    "occurrences": source_occurrences
                })
                
                target_evidence["methods"] = merged_methods
                target_evidence["occurrences"] = merged_occurrences
                target_evidence["merge_origins"] = merge_origins
                
                existing_rel.evidence_json = json.dumps(target_evidence)
                self.db.add(existing_rel)
                
                # Delete duplicate relationship
                self.db.delete(rel)
            else:
                # Update destination
                rel.to_object_id = target.id
                self.db.add(rel)
                
        self.db.commit()
        self.db.expire_all()
        source = self.db.get(DBRegistryObject, source.id)
        target = self.db.get(DBRegistryObject, target.id)
        return source, target

