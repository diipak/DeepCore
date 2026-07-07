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

class RegistryObjectCreate(RegistryObjectBase):
    pass

class RegistryObjectUpdate(BaseModel):
    title: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    metadata_json: Optional[str] = None
    provider_version: Optional[str] = None

class RegistryObject(RegistryObjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    created_at: datetime
    updated_at: datetime


class RegistryRelationshipBase(BaseModel):
    relationship_type: str = Field(..., min_length=1)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

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
