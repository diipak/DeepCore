from contextlib import asynccontextmanager
from fastapi import FastAPI
from deepcore.storage.sqlite.db import engine, Base
from deepcore.api.routes import router as objects_router, capture_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist on startup (SQLite creates file dynamically if configured)
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="DeepCore Registry MVP",
    description="Local-first personal intelligence platform foundation",
    version="0.1.0",
    lifespan=lifespan
)

# Register routes
app.include_router(objects_router)
app.include_router(capture_router)

@app.get("/")
def read_root():
    return {
        "status": "ok",
        "message": "DeepCore Registry MVP is running",
        "version": "0.1.0"
    }
