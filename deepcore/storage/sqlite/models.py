import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from deepcore.storage.sqlite.db import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

class RegistryObject(Base):
    __tablename__ = "registry_objects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String, unique=True, index=True, default=generate_uuid, nullable=False)
    object_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    source_system = Column(String, nullable=False)
    external_id = Column(String, nullable=True)
    location = Column(String, nullable=True)
    description = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")
    metadata_json = Column(String, nullable=True)
    provider_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)


class RegistryRelationship(Base):
    __tablename__ = "registry_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_object_id = Column(Integer, ForeignKey("registry_objects.id", ondelete="CASCADE"), nullable=False)
    to_object_id = Column(Integer, ForeignKey("registry_objects.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
