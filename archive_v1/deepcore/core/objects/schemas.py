from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class ObjectType(str, Enum):
    DOCUMENT = "document"
    PROJECT = "project"
    VIDEO = "video"
    NOTE = "note"
    REPOSITORY = "repository"
    TRANSACTION = "transaction"
    MERCHANT = "merchant"
    IDEA = "idea"
    CONCEPT = "concept"
    EVENT = "event"


class RegistryObjectBase(BaseModel):
    object_type: ObjectType
    title: str = Field(..., min_length=1)
    source_system: str = Field(..., min_length=1)
    external_id: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: str = "active"
    metadata_json: Optional[str] = None
    provider_version: Optional[str] = None
    content_hash: Optional[str] = None
    workspace_id: Optional[int] = None
    source_id: Optional[int] = None
    provider_id: Optional[str] = None

class RegistryObjectCreate(RegistryObjectBase):
    pass

class RegistryObjectUpdate(BaseModel):
    title: Optional[str] = None
    external_id: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    metadata_json: Optional[str] = None
    provider_version: Optional[str] = None
    content_hash: Optional[str] = None

class RegistryObject(RegistryObjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    created_at: datetime
    updated_at: datetime


class RelationshipType(str, Enum):
    REFERENCES = "REFERENCES"
    REFERENCED_BY = "REFERENCED_BY"
    SAME_FOLDER = "SAME_FOLDER"
    SAME_SOURCE = "SAME_SOURCE"
    SAME_PROJECT = "SAME_PROJECT"
    CHILD_OF = "CHILD_OF"
    PARENT_OF = "PARENT_OF"
    DUPLICATE = "DUPLICATE"
    VERSION_OF = "VERSION_OF"


class RegistryRelationshipBase(BaseModel):
    relationship_type: RelationshipType
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_json: Optional[str] = None
    relationship_source: Optional[str] = None


class RegistryRelationshipCreate(RegistryRelationshipBase):
    from_object_id: int
    to_object_id: int

class RegistryRelationship(RegistryRelationshipBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    from_object_id: int
    to_object_id: int
    created_at: datetime
    updated_at: datetime


class CaptureRequest(BaseModel):
    content: str = Field(..., min_length=1)


class SyncRunBase(BaseModel):
    provider: str
    source_location: Optional[str] = None
    status: str
    objects_scanned: int = 0
    objects_created: int = 0
    objects_existing: int = 0
    objects_updated: int = 0
    objects_missing: int = 0
    errors_json: Optional[str] = None

class SyncRunCreate(SyncRunBase):
    started_at: datetime
    finished_at: Optional[datetime] = None

class SyncRun(SyncRunBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    started_at: datetime
    finished_at: Optional[datetime] = None


class ContentIndexBase(BaseModel):
    object_id: int
    content_type: str
    raw_text: str
    content_hash: str
    word_count: int
    index_version: str = "content_v0.1"


class ContentIndexCreate(ContentIndexBase):
    pass


class ContentIndex(ContentIndexBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    indexed_at: datetime


class SignalType(str, Enum):
    RECENT_ACTIVITY = "RECENT_ACTIVITY"
    FREQUENT_ACTIVITY = "FREQUENT_ACTIVITY"
    DORMANT = "DORMANT"
    HIGH_REFERENCE_COUNT = "HIGH_REFERENCE_COUNT"
    ORPHAN_NOTE = "ORPHAN_NOTE"
    BROKEN_REFERENCE = "BROKEN_REFERENCE"


class RegistrySignalBase(BaseModel):
    signal_type: SignalType
    value: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    generated_by: str = "temporal_signal_engine"
    evidence_json: Optional[str] = None


class RegistrySignalCreate(RegistrySignalBase):
    target_object_id: int
    relationship_id: Optional[int] = None


class RegistrySignal(RegistrySignalBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    target_object_id: int
    relationship_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class ExecutionContext:
    """
    Immutable execution context carrying scoped active workspace, user, and other request variables.
    """
    def __init__(self, workspace_id: int, workspace_uuid: str, workspace_name: str, user: Optional[str] = None):
        self.workspace_id = workspace_id
        self.workspace_uuid = workspace_uuid
        self.workspace_name = workspace_name
        self.user = user


class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=1)


class WorkspaceCreate(WorkspaceBase):
    pass


class Workspace(WorkspaceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    created_at: datetime
    updated_at: datetime


class KnowledgeSourceBase(BaseModel):
    provider_id: str
    kind: str
    name: str
    location: str
    config_json: Optional[str] = None


class KnowledgeSourceCreate(KnowledgeSourceBase):
    pass


class KnowledgeSource(KnowledgeSourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    workspace_id: int
    created_at: datetime
    updated_at: datetime


class PreviewArtifactType(str, Enum):
    DOCUMENT = "document"
    EVENT = "event"
    VIDEO = "video"
    REPOSITORY = "repository"
    NOTE = "note"
    TRANSACTION = "transaction"
    MERCHANT = "merchant"
    IDEA = "idea"
    CONCEPT = "concept"


class SyncRunState(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class PreviewArtifact(BaseModel):
    name: str
    type: PreviewArtifactType
    location_descriptor: str
    size_bytes: Optional[int] = None


class SyncStatus(BaseModel):
    run_id: str
    state: SyncRunState
    processed: int
    total: int
    progress: float
    current_artifact: Optional[str] = None
    started_at: datetime
    updated_at: datetime
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)




