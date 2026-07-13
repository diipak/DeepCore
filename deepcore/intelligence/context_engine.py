from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from deepcore.core.registry.service import RegistryService
from deepcore.intelligence.models import (
    ContextRequest,
    ContextObjectReference,
    EvidenceItem,
    ContextConcept,
    ContextMemory,
    ContextPackage
)

class ContextEngine:
    """
    Context Engine is the source of truth for constructing context packages
    for downstream consumption by reasoning models, planners, or skills.
    
    It is model-agnostic, completely deterministic, and relies on the
    Registry Layer to perform modular database retrieval.
    """
    def __init__(self, db: Session):
        self.registry_service = RegistryService(db)

    def build_context(self, request: ContextRequest) -> ContextPackage:
        """
        Builds a ContextPackage based on the provided ContextRequest.
        
        The process is completely deterministic:
        1. Resolve active trigger object and its direct relationships.
        2. Perform text search for matching concepts and memories.
        3. Expose matching evidence (distance, matched concepts, type).
        4. Deterministically sort and limit output lists.
        """
        concepts_map: Dict[int, ContextConcept] = {}
        memories_map: Dict[int, ContextMemory] = {}
        trigger_obj: Optional[ContextObjectReference] = None
        trigger_db_obj = None

        # 1. Resolve Trigger Object
        if request.trigger_object_uuid:
            obj = self.registry_service.get_object(request.trigger_object_uuid)
            if obj and obj.status == "active":
                trigger_db_obj = obj
                trigger_obj = ContextObjectReference.from_db(obj)
                
                # Fetch direct concepts mentioned by trigger
                direct_concepts = self.registry_service.get_connected_concepts(obj.id)
                for concept in direct_concepts:
                    conn_count = self.registry_service.get_concept_connection_count(concept.id)
                    concepts_map[concept.id] = ContextConcept(
                        concept=ContextObjectReference.from_db(concept),
                        connection_count=conn_count,
                        evidence=EvidenceItem(
                            relationship_type="direct_mention",
                            traversal_distance=1,
                            is_direct=True,
                            matched_concepts=[concept.title]
                        )
                    )
                
                # Fetch direct memories referenced by trigger
                direct_memories = self.registry_service.get_referenced_memories(obj.id)
                for memory in direct_memories:
                    memories_map[memory.id] = ContextMemory(
                        memory=ContextObjectReference.from_db(memory),
                        evidence=EvidenceItem(
                            relationship_type="direct_reference",
                            traversal_distance=1,
                            is_direct=True
                        )
                    )

        # 2. Process Query Matches
        if request.query:
            matched_objs = self.registry_service.search_objects(request.query)
            for m_obj in matched_objs:
                # Avoid adding the trigger object itself as a related memory/concept
                if trigger_db_obj and m_obj.id == trigger_db_obj.id:
                    continue
                
                if m_obj.object_type == "concept":
                    if m_obj.id not in concepts_map:
                        conn_count = self.registry_service.get_concept_connection_count(m_obj.id)
                        concepts_map[m_obj.id] = ContextConcept(
                            concept=ContextObjectReference.from_db(m_obj),
                            connection_count=conn_count,
                            evidence=EvidenceItem(
                                matched_query=request.query,
                                relationship_type="query_match",
                                traversal_distance=1,
                                is_direct=True
                            )
                        )
                    else:
                        concepts_map[m_obj.id].evidence.matched_query = request.query
                    
                    # Fetch memories mentioning this concept
                    memories_for_concept = self.registry_service.get_objects_mentioning_concepts([m_obj.id])
                    for mem in memories_for_concept:
                        if trigger_db_obj and mem.id == trigger_db_obj.id:
                            continue
                        
                        if mem.id not in memories_map:
                            memories_map[mem.id] = ContextMemory(
                                memory=ContextObjectReference.from_db(mem),
                                evidence=EvidenceItem(
                                    relationship_type="concept_match",
                                    traversal_distance=2,
                                    is_direct=False,
                                    matched_concepts=[m_obj.title]
                                )
                            )
                        else:
                            if m_obj.title not in memories_map[mem.id].evidence.matched_concepts:
                                memories_map[mem.id].evidence.matched_concepts.append(m_obj.title)
                                memories_map[mem.id].evidence.matched_concepts.sort()
                
                else:  # Match is a general memory object (e.g. note, document, video)
                    if m_obj.id not in memories_map:
                        memories_map[m_obj.id] = ContextMemory(
                            memory=ContextObjectReference.from_db(m_obj),
                            evidence=EvidenceItem(
                                matched_query=request.query,
                                relationship_type="query_match",
                                traversal_distance=1,
                                is_direct=True
                            )
                        )
                    else:
                        memories_map[m_obj.id].evidence.matched_query = request.query
                    
                    # Fetch concepts mentioned by this memory
                    concepts_for_memory = self.registry_service.get_connected_concepts(m_obj.id)
                    for concept in concepts_for_memory:
                        if concept.id not in concepts_map:
                            conn_count = self.registry_service.get_concept_connection_count(concept.id)
                            concepts_map[concept.id] = ContextConcept(
                                concept=ContextObjectReference.from_db(concept),
                                connection_count=conn_count,
                                evidence=EvidenceItem(
                                    relationship_type="query_concept_match",
                                    traversal_distance=2,
                                    is_direct=False,
                                    matched_concepts=[concept.title]
                                )
                            )

        # 3. Transitive Concept Expansion
        if concepts_map:
            concept_ids = list(concepts_map.keys())
            expanded_memories = self.registry_service.get_objects_mentioning_concepts(concept_ids)
            for mem in expanded_memories:
                if trigger_db_obj and mem.id == trigger_db_obj.id:
                    continue
                
                # Retrieve all concepts this memory mentions to see which ones overlap
                mem_concepts = self.registry_service.get_connected_concepts(mem.id)
                overlapping_titles = sorted([
                    c.title for c in mem_concepts if c.id in concepts_map
                ])
                
                if not overlapping_titles:
                    continue
                
                if mem.id not in memories_map:
                    memories_map[mem.id] = ContextMemory(
                        memory=ContextObjectReference.from_db(mem),
                        evidence=EvidenceItem(
                            relationship_type="concept_match",
                            traversal_distance=2,
                            is_direct=False,
                            matched_concepts=overlapping_titles
                        )
                    )
                else:
                    existing = set(memories_map[mem.id].evidence.matched_concepts)
                    existing.update(overlapping_titles)
                    memories_map[mem.id].evidence.matched_concepts = sorted(list(existing))

        # Helper to sort datetimes safely
        def safe_timestamp(dt: Optional[datetime]) -> float:
            if not dt:
                return 0.0
            return dt.timestamp() if dt.tzinfo else dt.replace(tzinfo=None).timestamp()

        # 4. Deterministic Sorting and Slicing
        
        # Sort Concepts: connection_count (desc), title (asc), uuid (asc)
        sorted_concepts = sorted(
            concepts_map.values(),
            key=lambda item: (-item.connection_count, item.concept.title, item.concept.uuid)
        )
        final_concepts = sorted_concepts[:request.max_concepts]

        # Relationship priority mapping for memories: lower value is higher priority
        rel_priority = {
            "direct_reference": 1,
            "query_match": 2,
            "concept_match": 3,
        }

        # Sort Memories: priority (asc), traversal_distance (asc), created_at (desc), uuid (asc)
        sorted_memories = sorted(
            memories_map.values(),
            key=lambda item: (
                rel_priority.get(item.evidence.relationship_type, 4),
                item.evidence.traversal_distance,
                -safe_timestamp(item.memory.created_at),
                item.memory.uuid
            )
        )
        final_memories = sorted_memories[:request.max_memories]

        return ContextPackage(
            request=request,
            trigger_object=trigger_obj,
            concepts=final_concepts,
            memories=final_memories
        )
