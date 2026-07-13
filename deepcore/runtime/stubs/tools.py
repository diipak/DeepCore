"""
deepcore.runtime.stubs.tools

Canonical stub Tool implementations:

- EchoTool         — echoes the input message back as output.
- RegistrySearchMockTool — queries the RegistryService and returns matching objects.

These are used by the Capability Discovery bootstrap and in automated tests.
They must not depend on the test package.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from deepcore.runtime.tools.base import (
    BaseTool,
    ToolStatus,
    ToolDiagnostics,
    ToolRequest,
    ToolResult,
)
from deepcore.core.registry.service import RegistryService


# ────────────────────────────────────────────────
# EchoTool
# ────────────────────────────────────────────────

class EchoInput(BaseModel):
    message: str

class EchoOutput(BaseModel):
    message: str

class EchoTool(BaseTool):
    """Reflects any message back unchanged. Used to exercise the tool execution pipeline."""
    name = "echo_tool"
    description = "Echoes inputs back"
    category = "ReadWrite"
    input_schema = EchoInput
    output_schema = EchoOutput

    def execute(self, request: ToolRequest) -> ToolResult:
        inputs_obj = self.input_schema(**request.inputs)
        return ToolResult(
            request_id=request.request_id,
            status=ToolStatus.SUCCESS,
            outputs={"message": inputs_obj.message},
            diagnostics=ToolDiagnostics(execution_time_ms=0.0)
        )


# ────────────────────────────────────────────────
# RegistrySearchMockTool
# ────────────────────────────────────────────────

class RegistrySearchInput(BaseModel):
    query: str
    object_type: Optional[str] = None

class RegistrySearchOutput(BaseModel):
    results: List[Dict[str, Any]]

class RegistrySearchMockTool(BaseTool):
    """Delegates a full-text search to RegistryService and returns serialized objects."""
    name = "registry_search_mock"
    description = "Mock tool to search the platform registry"
    category = "Query"
    input_schema = RegistrySearchInput
    output_schema = RegistrySearchOutput

    def __init__(self, registry_service: Optional[RegistryService] = None):
        self._registry_service = registry_service

    def execute(self, request: ToolRequest) -> ToolResult:
        inputs_obj = self.input_schema(**request.inputs)
        
        should_close = False
        if self._registry_service is not None:
            reg_service = self._registry_service
        else:
            from deepcore.storage.sqlite.db import db_session_ctx, SessionLocal
            try:
                db = db_session_ctx.get()
                reg_service = RegistryService(db)
            except LookupError:
                db = SessionLocal()
                reg_service = RegistryService(db)
                should_close = True

        try:
            db_objs = reg_service.search_objects(
                query=inputs_obj.query,
                object_type=inputs_obj.object_type
            )
            serialized_results = [
                {
                    "id": obj.id,
                    "uuid": obj.uuid,
                    "title": obj.title,
                    "description": obj.description,
                    "object_type": obj.object_type,
                    "location": obj.location,
                }
                for obj in db_objs
            ]
            return ToolResult(
                request_id=request.request_id,
                status=ToolStatus.SUCCESS,
                outputs={"results": serialized_results},
                diagnostics=ToolDiagnostics(execution_time_ms=0.0)
            )
        finally:
            if should_close:
                reg_service.db.close()
