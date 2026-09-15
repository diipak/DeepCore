from contextlib import asynccontextmanager
from fastapi import FastAPI
from deepcore2.config import settings
from deepcore2.runtime.composition import bootstrap_application
from deepcore2.api.routes import (
    objects_router,
    capture_router,
    registry_api_router,
    content_api_router,
    concepts_api_router,
    system_api_router,
    assistant_api_router,
    memories_api_router,
    capabilities_api_router,
    providers_api_router,
    workspaces_api_router,
    sources_api_router,
    conversations_api_router,
    connectors_api_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Bootstrap the application (config load, run migrations, registries, services, validation)
    deepcore_app = bootstrap_application(settings)
    app.state.deepcore_app = deepcore_app
    yield
    # Graceful shutdown hooks execution
    deepcore_app.shutdown()

app = FastAPI(
    title="DeepCore Registry MVP",
    description="Local-first personal intelligence platform foundation",
    version="0.1.0",
    lifespan=lifespan
)

# Register legacy routes
app.include_router(objects_router)
app.include_router(capture_router)

# Register Phase 5 API Gateway routes
app.include_router(registry_api_router, prefix="/api")
app.include_router(content_api_router, prefix="/api")
app.include_router(concepts_api_router, prefix="/api")
app.include_router(system_api_router, prefix="/api")
app.include_router(assistant_api_router)
app.include_router(memories_api_router, prefix="/api")
app.include_router(capabilities_api_router, prefix="/api")
app.include_router(providers_api_router, prefix="/api")
app.include_router(workspaces_api_router, prefix="/api")
app.include_router(sources_api_router, prefix="/api")
app.include_router(conversations_api_router, prefix="/api")
app.include_router(connectors_api_router, prefix="/api")






@app.get("/")
def read_root():
    return {
        "status": "ok",
        "message": "DeepCore Registry MVP is running",
        "version": "0.1.0"
    }

