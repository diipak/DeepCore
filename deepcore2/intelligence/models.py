from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ContextRequest(BaseModel):
    trigger_object_uuid: Optional[str] = None
    query: Optional[str] = None
    max_concepts: int = 10
    max_memories: int = 10
    custom_metadata: Dict[str, Any] = Field(default_factory=dict)

class ContextObjectReference(BaseModel):
    uuid: str
    object_type: str
    title: str
    source_system: str
    location: Optional[str] = None
    description: Optional[str] = None
    status: str
    metadata_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, db_obj) -> "ContextObjectReference":
        return cls(
            uuid=db_obj.uuid,
            object_type=db_obj.object_type,
            title=db_obj.title,
            source_system=db_obj.source_system,
            location=db_obj.location,
            description=db_obj.description,
            status=db_obj.status,
            metadata_json=db_obj.metadata_json,
            created_at=db_obj.created_at,
            updated_at=db_obj.updated_at
        )

class EvidenceItem(BaseModel):
    matched_query: Optional[str] = None
    matched_concepts: List[str] = Field(default_factory=list)
    relationship_type: str  # e.g., "direct_mention", "direct_reference", "concept_match", "query_match", "query_concept_match"
    traversal_distance: int  # 0 for trigger itself, 1 for direct links, 2 for indirect/transitive links
    is_direct: bool

class ContextConcept(BaseModel):
    concept: ContextObjectReference
    connection_count: int
    evidence: EvidenceItem

class ContextMemory(BaseModel):
    memory: ContextObjectReference
    evidence: EvidenceItem

class ContextPackage(BaseModel):
    schema_version: str = "context_v1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request: ContextRequest
    trigger_object: Optional[ContextObjectReference] = None
    concepts: List[ContextConcept] = Field(default_factory=list)
    memories: List[ContextMemory] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
