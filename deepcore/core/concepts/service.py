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
            # 1. Search for existing active concept using logical identity (normalized_key)
            existing_concept = self.db.query(DBRegistryObject).filter(
                DBRegistryObject.object_type == "concept",
                DBRegistryObject.status == "active",
                func.json_extract(DBRegistryObject.metadata_json, '$.normalized_key') == norm_key
            ).first()

            if existing_concept:
                concept_obj = existing_concept
            else:
                # Create a new concept registry object
                concept_obj = DBRegistryObject(
                    object_type="concept",
                    title=info["title"],
                    source_system="deepcore",
                    provider_version="concept_v0.1",
                    status="active",
                    metadata_json=json.dumps({"normalized_key": norm_key})
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

    def list_concepts(self, limit: int = 50) -> List[Tuple[DBRegistryObject, int]]:
        """Return active concepts ordered by connection (relationship) count descending."""
        results = self.db.query(
            DBRegistryObject,
            func.count(DBRegistryRelationship.id).label("connection_count")
        ).join(
            DBRegistryRelationship,
            DBRegistryObject.id == DBRegistryRelationship.to_object_id
        ).filter(
            DBRegistryObject.object_type == "concept",
            DBRegistryObject.status == "active",
            DBRegistryRelationship.relationship_type == "mentions"
        ).group_by(
            DBRegistryObject.id
        ).order_by(
            func.count(DBRegistryRelationship.id).desc(),
            DBRegistryObject.title.asc()
        ).limit(limit).all()

        return results

    def get_concept_by_name(self, name: str) -> Optional[DBRegistryObject]:
        """Find an active concept registry object by title name (logical normalized key matching)."""
        norm_key = name.lower().replace(" ", "").replace("-", "").replace("_", "")
        return self.db.query(DBRegistryObject).filter(
            DBRegistryObject.object_type == "concept",
            DBRegistryObject.status == "active",
            func.json_extract(DBRegistryObject.metadata_json, '$.normalized_key') == norm_key
        ).first()

    def get_connected_memories(self, concept_id: int) -> List[DBRegistryObject]:
        """Get active registry objects connected to this concept."""
        return self.db.query(DBRegistryObject).join(
            DBRegistryRelationship,
            DBRegistryObject.id == DBRegistryRelationship.from_object_id
        ).filter(
            DBRegistryRelationship.to_object_id == concept_id,
            DBRegistryRelationship.relationship_type == "mentions",
            DBRegistryObject.status == "active"
        ).all()
