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


class RegistryRelationshipBase(BaseModel):
    relationship_type: str = Field(..., min_length=1)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_json: Optional[str] = None
    relationship_source: Optional[str] = None


class RegistryRelationshipCreate(RegistryRelationshipBase):
    from_object_id: int
    to_object_id: int

class RegistryRelationship(RegistryRelationshipBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_object_id: int
    to_object_id: int
    created_at: datetime


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

