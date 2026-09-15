import os
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
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
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, default=1)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    provider_id = Column(String, nullable=True)


class RegistryRelationship(Base):
    __tablename__ = "registry_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String, unique=True, index=True, default=generate_uuid, nullable=False)
    from_object_id = Column(Integer, ForeignKey("registry_objects.id", ondelete="CASCADE"), nullable=False)
    to_object_id = Column(Integer, ForeignKey("registry_objects.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    evidence_json = Column(Text, nullable=True)
    relationship_source = Column(String, nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, default=1)



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
    progress = Column(Float, nullable=True)
    telemetry_json = Column(Text, nullable=True)
    error_message = Column(String, nullable=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, default=1)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)


class ContentIndex(Base):
    __tablename__ = "content_index"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String, unique=True, index=True, default=generate_uuid, nullable=False)
    object_id = Column(Integer, ForeignKey("registry_objects.id", ondelete="CASCADE"), nullable=False)
    content_type = Column(String, nullable=False)
    raw_text = Column(Text, nullable=False)
    content_hash = Column(String, nullable=False, index=True)
    word_count = Column(Integer, default=0, nullable=False)
    indexed_at = Column(DateTime, default=get_utc_now, nullable=False)
    index_version = Column(String, default="content_v0.1", nullable=False)


class ObjectActivityLog(Base):
    __tablename__ = "object_activity_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    object_id = Column(Integer, ForeignKey("registry_objects.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String, nullable=False)  # "created" or "updated"
    timestamp = Column(DateTime, default=get_utc_now, nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, default=1)


class RegistrySignal(Base):
    __tablename__ = "registry_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String, unique=True, index=True, default=generate_uuid, nullable=False)
    signal_type = Column(String, nullable=False, index=True)
    target_object_id = Column(Integer, ForeignKey("registry_objects.id", ondelete="CASCADE"), nullable=False)
    relationship_id = Column(Integer, ForeignKey("registry_relationships.id", ondelete="SET NULL"), nullable=True)
    value = Column(String, nullable=True)
    confidence = Column(Float, nullable=False, default=1.0)
    generated_by = Column(String, nullable=False, default="temporal_signal_engine")
    evidence_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, default=1)


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String, unique=True, index=True, default=generate_uuid, nullable=False)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)


class KnowledgeSource(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String, unique=True, index=True, default=generate_uuid, nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    provider_id = Column(String, nullable=False)  # e.g., "markdown"
    kind = Column(String, nullable=False)         # e.g., "filesystem", "github"
    name = Column(String, nullable=False)         # e.g., "Personal Obsidian Vault"
    location = Column(String, nullable=False)     # e.g., "/path/to/folder" or URL
    config_json = Column(Text, nullable=True)     # provider-specific config
    status = Column(String, nullable=False, default="Configured")
    cursor_state = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)


class ThinkingSession(Base):
    __tablename__ = "thinking_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String, unique=True, index=True, default=generate_uuid, nullable=False)
    title = Column(String, nullable=False)
    active_thinking_mode = Column(String, nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, default=1)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String, unique=True, index=True, default=generate_uuid, nullable=False)
    thinking_session_id = Column(Integer, ForeignKey("thinking_sessions.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, default=1)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String, unique=True, index=True, default=generate_uuid, nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    evidence_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)


def run_migrations(engine) -> None:
    """Run database table initialization and self-healing schema updates."""
    # 1. Ensure tables are created first
    Base.metadata.create_all(bind=engine)

    from sqlalchemy import inspect, text
    from sqlalchemy.orm import Session
    inspector = inspect(engine)

    # 2. Ensure default "Personal Workspace" exists
    db = Session(bind=engine)
    try:
        personal_ws = db.query(Workspace).filter(Workspace.name == "Personal Workspace").first()
        if not personal_ws:
            personal_ws = Workspace(name="Personal Workspace")
            db.add(personal_ws)
            db.commit()
            db.refresh(personal_ws)
        personal_ws_id = personal_ws.id
    finally:
        db.close()

    # 3. Check and alter registry_objects table for missing columns
    obj_columns = [col["name"] for col in inspector.get_columns("registry_objects")]
    if "content_hash" not in obj_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE registry_objects ADD COLUMN content_hash TEXT;"))
            conn.execute(text("CREATE INDEX ix_registry_objects_content_hash ON registry_objects (content_hash);"))

    # Workspace columns alterations and backfills
    with engine.begin() as conn:
        if "workspace_id" not in obj_columns:
            conn.execute(text("ALTER TABLE registry_objects ADD COLUMN workspace_id INTEGER REFERENCES workspaces(id) ON DELETE CASCADE;"))
            conn.execute(text(f"UPDATE registry_objects SET workspace_id = {personal_ws_id} WHERE workspace_id IS NULL;"))
        if "source_id" not in obj_columns:
            conn.execute(text("ALTER TABLE registry_objects ADD COLUMN source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL;"))
        if "provider_id" not in obj_columns:
            conn.execute(text("ALTER TABLE registry_objects ADD COLUMN provider_id TEXT;"))
            conn.execute(text("UPDATE registry_objects SET provider_id = 'markdown' WHERE provider_id IS NULL;"))

    # 4. Check sync_runs columns
    if "sync_runs" in inspector.get_table_names():
        run_columns = [col["name"] for col in inspector.get_columns("sync_runs")]
        if "objects_missing" not in run_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE sync_runs ADD COLUMN objects_missing INTEGER DEFAULT 0;"))
        if "progress" not in run_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE sync_runs ADD COLUMN progress FLOAT;"))
        if "telemetry_json" not in run_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE sync_runs ADD COLUMN telemetry_json TEXT;"))
        if "error_message" not in run_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE sync_runs ADD COLUMN error_message TEXT;"))

        with engine.begin() as conn:
            if "workspace_id" not in run_columns:
                conn.execute(text("ALTER TABLE sync_runs ADD COLUMN workspace_id INTEGER REFERENCES workspaces(id) ON DELETE CASCADE;"))
                conn.execute(text(f"UPDATE sync_runs SET workspace_id = {personal_ws_id} WHERE workspace_id IS NULL;"))
            if "source_id" not in run_columns:
                conn.execute(text("ALTER TABLE sync_runs ADD COLUMN source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL;"))

    # 4b. Check sources columns
    if "sources" in inspector.get_table_names():
        src_columns = [col["name"] for col in inspector.get_columns("sources")]
        if "status" not in src_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE sources ADD COLUMN status TEXT DEFAULT 'Configured';"))
        if "cursor_state" not in src_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE sources ADD COLUMN cursor_state TEXT;"))

    # 5. Check registry_relationships columns
    if "registry_relationships" in inspector.get_table_names():
        rel_columns = [col["name"] for col in inspector.get_columns("registry_relationships")]
        if "evidence_json" not in rel_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE registry_relationships ADD COLUMN evidence_json TEXT;"))
        if "relationship_source" not in rel_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE registry_relationships ADD COLUMN relationship_source TEXT;"))
        if "uuid" not in rel_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE registry_relationships ADD COLUMN uuid TEXT;"))
            
            # Generate UUIDs for any existing relationships
            db = Session(bind=engine)
            try:
                rows = db.execute(text("SELECT id FROM registry_relationships WHERE uuid IS NULL")).fetchall()
                for row in rows:
                    db.execute(
                        text("UPDATE registry_relationships SET uuid = :uuid WHERE id = :id"),
                        {"uuid": generate_uuid(), "id": row[0]}
                    )
                db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()

            with engine.begin() as conn:
                conn.execute(text("CREATE UNIQUE INDEX ix_registry_relationships_uuid ON registry_relationships (uuid);"))

        if "updated_at" not in rel_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE registry_relationships ADD COLUMN updated_at DATETIME;"))
            with engine.begin() as conn:
                if "created_at" in rel_columns:
                    conn.execute(text("UPDATE registry_relationships SET updated_at = created_at WHERE updated_at IS NULL;"))
                else:
                    conn.execute(text("UPDATE registry_relationships SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL;"))

        with engine.begin() as conn:
            if "workspace_id" not in rel_columns:
                conn.execute(text("ALTER TABLE registry_relationships ADD COLUMN workspace_id INTEGER REFERENCES workspaces(id) ON DELETE CASCADE;"))
                conn.execute(text(f"UPDATE registry_relationships SET workspace_id = {personal_ws_id} WHERE workspace_id IS NULL;"))

    # 6. Check registry_signals columns
    if "registry_signals" in inspector.get_table_names():
        sig_columns = [col["name"] for col in inspector.get_columns("registry_signals")]
        with engine.begin() as conn:
            if "workspace_id" not in sig_columns:
                conn.execute(text("ALTER TABLE registry_signals ADD COLUMN workspace_id INTEGER REFERENCES workspaces(id) ON DELETE CASCADE;"))
                conn.execute(text(f"UPDATE registry_signals SET workspace_id = {personal_ws_id} WHERE workspace_id IS NULL;"))

    # 7. Check object_activity_log columns
    if "object_activity_log" in inspector.get_table_names():
        log_columns = [col["name"] for col in inspector.get_columns("object_activity_log")]
        with engine.begin() as conn:
            if "workspace_id" not in log_columns:
                conn.execute(text("ALTER TABLE object_activity_log ADD COLUMN workspace_id INTEGER REFERENCES workspaces(id) ON DELETE CASCADE;"))
                conn.execute(text(f"UPDATE object_activity_log SET workspace_id = {personal_ws_id} WHERE workspace_id IS NULL;"))

    # 8. Ensure default workspaces and knowledge sources are registered
    db = Session(bind=engine)
    try:
        # Check / create Personal Workspace
        personal_ws = db.query(Workspace).filter(Workspace.name == "Personal Workspace").first()
        if not personal_ws:
            personal_ws = Workspace(name="Personal Workspace")
            db.add(personal_ws)
            db.commit()
            db.refresh(personal_ws)
        
        default_vault_location = os.path.expanduser(os.getenv("DEEPCORE_VAULT_ROOT", "~/Documents/Notes"))
        default_demo_location = os.path.realpath(os.path.expanduser(os.getenv("DEEPCORE_DEMO_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "..", "demo", "markdown"))))

        # Check / create Obsidian Vault source inside Personal Workspace
        obsidian_source = db.query(KnowledgeSource).filter(
            KnowledgeSource.workspace_id == personal_ws.id,
            KnowledgeSource.provider_id == "markdown",
            KnowledgeSource.location == default_vault_location
        ).first()
        if not obsidian_source:
            obsidian_source = KnowledgeSource(
                workspace_id=personal_ws.id,
                provider_id="markdown",
                kind="filesystem",
                name="Obsidian Vault",
                location=default_vault_location,
                config_json="{}"
            )
            db.add(obsidian_source)
            db.commit()

        # Check / create Demo Workspace
        demo_ws = db.query(Workspace).filter(Workspace.name == "Demo Workspace").first()
        if not demo_ws:
            demo_ws = Workspace(name="Demo Workspace")
            db.add(demo_ws)
            db.commit()
            db.refresh(demo_ws)

        # Check / create Demo Notes source inside Demo Workspace
        demo_source = db.query(KnowledgeSource).filter(
            KnowledgeSource.workspace_id == demo_ws.id,
            KnowledgeSource.provider_id == "markdown",
            KnowledgeSource.location == default_demo_location
        ).first()
        if not demo_source:
            demo_source = KnowledgeSource(
                workspace_id=demo_ws.id,
                provider_id="markdown",
                kind="filesystem",
                name="Demo Notes",
                location=default_demo_location,
                config_json="{}"
            )
            db.add(demo_source)
            db.commit()

        # Run Workspace Integrity Repair on startup for both workspaces
        from deepcore.core.integrity.service import WorkspaceIntegrityService
        for ws in [personal_ws, demo_ws]:
            if ws:
                integrity_service = WorkspaceIntegrityService(db, ws.id)
                integrity_service.repair_integrity()

    except Exception as e:
        db.rollback()
        print(f"Error registering default workspaces/sources/repair: {e}")
    finally:
        db.close()



