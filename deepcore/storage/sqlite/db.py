import contextvars
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import Generator
from sqlalchemy.orm import Session
from deepcore.config import settings

# Strictly for bridging request-scoped database sessions to singleton runtime components.
# This context variable MUST NOT be utilized as a general-purpose service locator.
db_session_ctx: contextvars.ContextVar[Session] = contextvars.ContextVar("db_session")

# For SQLite, we set check_same_thread to False to allow multiple threads to access it
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator:
    """FastAPI database session dependency."""
    db = SessionLocal()
    token = db_session_ctx.set(db)
    try:
        yield db
    finally:
        try:
            db_session_ctx.reset(token)
        except ValueError:
            pass
        db.close()
