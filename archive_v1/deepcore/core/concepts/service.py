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
    # Pronouns & basic grammar
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", "as", "at", 
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can", "can't", "cannot", 
    "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each", 
    "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", 
    "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", 
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", 
    "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", 
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", 
    "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", 
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", 
    "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", 
    "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", 
    "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", 
    "you're", "you've", "your", "yours", "yourself", "yourselves",
    
    # Common generic verbs & UI / note actions
    "access", "action", "add", "allow", "allows", "also", "app", "apps", "back", "bad", "base", "best",
    "better", "build", "building", "change", "changed", "changes", "check", "code", "codes", "complete",
    "completed", "contain", "contains", "create", "created", "creates", "creating", "data", "date", "dates",
    "day", "days", "default", "delete", "detail", "details", "disable", "edit", "enable", "enter", "example",
    "examples", "file", "files", "find", "first", "follow", "following", "get", "gets", "getting", "good",
    "group", "groups", "high", "help", "how", "important", "include", "included", "includes", "info",
    "information", "install", "installed", "item", "items", "just", "key", "keys", "last", "line", "lines",
    "list", "lists", "low", "main", "make", "makes", "making", "master", "need", "needs", "new", "note",
    "notes", "null", "one", "open", "opened", "opens", "page", "pages", "part", "parts", "path", "paths",
    "project", "projects", "real", "remove", "return", "returns", "run", "running", "sample", "samples",
    "save", "see", "select", "service", "services", "set", "sets", "share", "show", "shows", "start", "step",
    "steps", "stop", "support", "supports", "system", "systems", "tell", "text", "time", "times", "true", "try",
    "type", "types", "update", "updated", "updates", "use", "used", "user", "users", "uses", "using",
    "val", "value", "values", "version", "versions", "view", "views", "way", "ways", "work", "working", "discuss", "explain", "give",
    
    # Months / Days / Misc generic noise & file extensions
    "january", "february", "march", "april", "may", "june", "july", "august", "september",
    "october", "november", "december", "monday", "tuesday", "wednesday", "thursday", "friday",
    "saturday", "sunday", "md", "txt", "pdf", "doc", "docx", "csv", "json", "yaml", "yml", "xml", "html", "htm"
}

VALID_CONCEPT_TYPES = {"tool", "technology", "project", "person", "organization", "unknown"}

COMMON_TECH_TERMS = {
    "docker", "python", "linux", "git", "react", "rust", "kafka", "postgres", "postgresql",
    "redis", "nginx", "kubernetes", "ollama", "obsidian", "debian", "ubuntu", "fastapi",
    "django", "flask", "pydantic", "sqlite", "graphql", "protobuf", "celery", "airflow",
    "pandas", "numpy", "pytorch", "tensorflow", "spark", "hadoop", "ansible", "terraform",
    "jenkins", "grafana", "prometheus", "elasticsearch", "logstash", "kibana", "valkey", "click"
}


def is_technical_term(word: str) -> bool:
    """Check if a word is a technical term (CamelCase, ALLCAPS, containing numbers, or known tech term)."""
    # Strip common punctuation
    w = word.strip(".,;:!?()[]{}'\"*`_")
    if not w.isalnum():
        return False

    clean = w.lower()
    if clean in COMMON_TECH_TERMS:
        return True

    # 1. Words containing numbers (e.g. GPT4, 2FA)
    has_letter = any(c.isalpha() for c in w)
    has_digit = any(c.isdigit() for c in w)
    if has_letter and has_digit:
        # Strict rules: Capitalized letters + digits, or digits + uppercase letters
        if re.match(r'^[A-Z][a-zA-Z]*\d+$', w) or re.match(r'^\d+[A-Z]+$', w):
            return True
        return False

    # 2. ALLCAPS abbreviations (length >= 2, e.g. AI, IP, UI, RAG, MLX, LLM)
    if w.isupper() and len(w) >= 2:
        return True

    # 3. CamelCase / PascalCase
    # Must start with uppercase, contain at least one lowercase letter, and at least one uppercase letter after index 0.
    if w[0].isupper() and any(c.islower() for c in w):
        if any(c.isupper() for c in w[1:]):
            return True

    return False


def is_valid_concept_candidate(term: str) -> bool:
    """Filter out URLs, UUIDs, query params, random hashes, stop words, and invalid alphanumeric tokens."""
    # Reject too short
    if len(term) < 2:
        return False

    # Reject digit-only
    if term.isdigit():
        return False

    # Check if term or normalized key is a stopword
    clean_term = term.strip().lower()
    if clean_term in STOP_WORDS:
        return False

    # Reject URLs and domain names
    if re.search(r'https?://|www\.|github\.com|youtube\.com|youtu\.be', term, re.IGNORECASE):
        return False

    # Reject query parameters or query characters
    if "?" in term or "=" in term or "&" in term:
        return False

    # Reject UUIDs
    if re.match(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$', term):
        return False

    # Reject md5/sha1/sha256 hex hashes
    if re.match(r'^[a-fA-F0-9]{32,64}$', term):
        return False

    # Filter alphanumeric tokens containing both numbers and letters (random IDs check)
    has_letter = any(c.isalpha() for c in term)
    has_digit = any(c.isdigit() for c in term)
    if has_letter and has_digit:
        words = term.split()
        for w in words:
            w_clean = w.strip(".,;:!?()[]{}'\"*`_")
            w_has_letter = any(c.isalpha() for c in w_clean)
            w_has_digit = any(c.isdigit() for c in w_clean)
            if w_has_letter and w_has_digit:
                # Must start with letter and end with number (capitalized) or start with number and end with uppercase letter
                if not (re.match(r'^[A-Z][a-zA-Z]*\d+$', w_clean) or re.match(r'^\d+[A-Z]+$', w_clean)):
                    return False

    return True


class ConceptService:
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
            DBRegistryObject.workspace_id == self.workspace_id,
            DBRegistryObject.id == object_id,
            DBRegistryObject.status == "active"
        ).first()
        if not obj:
            return {"concepts_created": 0, "relationships_created": 0}

        content_index = self.db.query(DBContentIndex).filter(DBContentIndex.object_id == object_id).first()
        if not content_index or not content_index.raw_text:
            return {"concepts_created": 0, "relationships_created": 0}

        raw_text = content_index.raw_text
        if raw_text:
            # Replace URLs with spaces
            raw_text = re.sub(r'https?://\S+', ' ', raw_text)
            raw_text = re.sub(r'www\.\S+', ' ', raw_text)
            # Replace UUID-like strings with spaces
            raw_text = re.sub(r'\b[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}\b', ' ', raw_text)
            # Replace long hex hashes with spaces
            raw_text = re.sub(r'\b[a-fA-F0-9]{32,64}\b', ' ', raw_text)
            # Replace query string fragments (e.g., ?v=abc, &v=abc)
            raw_text = re.sub(r'\?\S+', ' ', raw_text)
            raw_text = re.sub(r'&\S+', ' ', raw_text)

        candidates = {}  # normalized_key -> {"title": original_title, "methods": set(), "count": int}

        # --- A. Markdown Headings ---
        lines = raw_text.splitlines()
        for line in lines:
            m = re.match(r'^#+\s+(.+)$', line)
            if m:
                heading = m.group(1).strip()
                heading_clean = heading.strip("`*_-")
                if not is_valid_concept_candidate(heading_clean):
                    continue
                norm = heading_clean.lower().replace(" ", "").replace("-", "").replace("_", "")
                if norm in STOP_WORDS and norm not in COMMON_TECH_TERMS:
                    continue
                heading_words = [w.lower() for w in re.findall(r'\b[a-zA-Z0-9_-]+\b', heading_clean)]
                if all(w in STOP_WORDS and w not in COMMON_TECH_TERMS for w in heading_words):
                    continue
                if norm not in candidates:
                    candidates[norm] = {"title": heading_clean, "methods": set(), "count": 0}
                candidates[norm]["methods"].add("heading")

        # --- B. Technical Term Patterns ---
        words = re.findall(r'\b[a-zA-Z0-9_-]+\b', raw_text)
        for w in words:
            if is_technical_term(w) and is_valid_concept_candidate(w):
                norm = w.lower().replace(" ", "").replace("-", "").replace("_", "")
                if norm in STOP_WORDS:
                    continue
                if norm not in candidates:
                    candidates[norm] = {"title": w, "methods": set(), "count": 0}
                candidates[norm]["methods"].add("technical_term")

        # --- C. Repeated Capitalized Phrases ---
        phrase_pattern = re.compile(r'\b[A-Z][a-zA-Z0-9]*(\s+[A-Z][a-zA-Z0-9]*)*\b')
        phrases = [m.group(0) for m in phrase_pattern.finditer(raw_text)]
        for p in phrases:
            p_clean = p.strip()
            if not is_valid_concept_candidate(p_clean):
                continue
            norm = p_clean.lower().replace(" ", "").replace("-", "").replace("_", "")
            if norm in STOP_WORDS and norm not in COMMON_TECH_TERMS:
                continue
            p_words = [w.lower() for w in re.findall(r'\b[a-zA-Z0-9_-]+\b', p_clean)]
            # If all words in phrase are in STOP_WORDS, skip
            if all(w in STOP_WORDS and w not in COMMON_TECH_TERMS for w in p_words):
                continue
            # If single word, check if it's a technical term OR a valid mid-sentence / multi-occurrence capitalized word
            if len(p_words) == 1:
                if not is_technical_term(p_clean):
                    mid_sentence_matches = re.findall(r'[a-zA-Z0-9,;]\s+' + re.escape(p_clean) + r'\b', raw_text)
                    if not mid_sentence_matches and len(re.findall(r'\b' + re.escape(p_clean) + r'\b', raw_text)) < 2:
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
                DBRegistryObject.workspace_id == self.workspace_id,
                DBRegistryObject.object_type == "concept",
                func.json_extract(DBRegistryObject.metadata_json, '$.normalized_key') == norm_key
            ).first()

            if existing_concept:
                self._ensure_governance_metadata(existing_concept)
                concept_obj = existing_concept
            else:
                # Create a new concept registry object
                concept_obj = DBRegistryObject(
                    workspace_id=self.workspace_id,
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
                DBRegistryRelationship.workspace_id == self.workspace_id,
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
                    workspace_id=self.workspace_id,
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
            DBRegistryObject.workspace_id == self.workspace_id,
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
        if isinstance(show_ignored, str):
            show_ignored = show_ignored.lower() in ("true", "1", "yes", "t", "y")

        from sqlalchemy import case

        # 1. Start query from concept table
        query = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.workspace_id == self.workspace_id,
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
            DBRegistryRelationship.workspace_id == self.workspace_id,
            DBRegistryRelationship.relationship_type == "mentions"
        ).with_entities(
            DBRegistryObject,
            func.count(DBRegistryRelationship.id).label("connection_count")
        )

        approved_order = case(
            (func.json_extract(DBRegistryObject.metadata_json, '$.concept_status') == 'approved', 0),
            else_=1
        )

        results = query.group_by(
            DBRegistryObject.id
        ).order_by(
            approved_order.asc(),
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
            DBRegistryObject.workspace_id == self.workspace_id,
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
            DBRegistryObject.workspace_id == self.workspace_id,
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
            DBRegistryRelationship.workspace_id == self.workspace_id,
            DBRegistryObject.workspace_id == self.workspace_id,
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
            DBRegistryRelationship.workspace_id == self.workspace_id,
            DBRegistryRelationship.to_object_id == source.id
        ).all()
        
        for rel in relationships:
            existing_rel = self.db.query(DBRegistryRelationship).filter(
                DBRegistryRelationship.workspace_id == self.workspace_id,
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

