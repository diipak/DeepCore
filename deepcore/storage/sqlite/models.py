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
    content_hash = Column(String, nullable=True, index=True)
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


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String, unique=True, index=True, default=generate_uuid, nullable=False)
    provider = Column(String, nullable=False)
    source_location = Column(String, nullable=True)
    started_at = Column(DateTime, default=get_utc_now, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False)
    objects_scanned = Column(Integer, default=0, nullable=False)
    objects_created = Column(Integer, default=0, nullable=False)
    objects_existing = Column(Integer, default=0, nullable=False)
    objects_updated = Column(Integer, default=0, nullable=False)
    objects_missing = Column(Integer, default=0, nullable=False)
    errors_json = Column(String, nullable=True)


def run_migrations(engine) -> None:
    """Run database table initialization and self-healing schema updates."""
    # 1. Ensure tables are created first
    Base.metadata.create_all(bind=engine)

    # 2. Check and alter registry_objects table for missing columns
    from sqlalchemy import inspect
    inspector = inspect(engine)
    
    # Check registry_objects columns
    obj_columns = [col["name"] for col in inspector.get_columns("registry_objects")]
    if "content_hash" not in obj_columns:
        with engine.begin() as conn:
            conn.execute("ALTER TABLE registry_objects ADD COLUMN content_hash TEXT;")
            conn.execute("CREATE INDEX ix_registry_objects_content_hash ON registry_objects (content_hash);")

    # Check sync_runs columns (handles incremental migration if table existed before update)
    if "sync_runs" in inspector.get_table_names():
        run_columns = [col["name"] for col in inspector.get_columns("sync_runs")]
        if "objects_missing" not in run_columns:
            with engine.begin() as conn:
                conn.execute("ALTER TABLE sync_runs ADD COLUMN objects_missing INTEGER DEFAULT 0;")
