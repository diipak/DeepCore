import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from deepcore.storage.sqlite.db import get_db
from deepcore.api.main import app

from deepcore.runtime.conversation.base import (
    ConversationMode,
    ConversationRequest,
    ConversationResponse,
    ConversationMessage,
    ConversationStatus
)
from deepcore.runtime.conversation.runtime import ConversationRuntime
from deepcore.runtime.planner.runtime import PlannerRuntime
from deepcore.runtime.health import KernelHealthReport

from tests.test_kernel_integration import kernel_setup, registry_service


@pytest.fixture
def conversation_setup(kernel_setup):
    planner_runtime = kernel_setup["planner_runtime"]
    conv_runtime = ConversationRuntime(planner_runtime)
    return {
        **kernel_setup,
        "conversation_runtime": conv_runtime
    }


def test_conversation_descriptor(conversation_setup):
    runtime = conversation_setup["conversation_runtime"]
    desc = runtime.get_descriptor()
    
    assert ConversationMode.DIRECT in desc.supported_modes
    assert ConversationMode.PLANNING in desc.supported_modes
    assert desc.supports_context is True
    assert desc.supports_planning is True
    assert desc.supports_streaming is False


def test_conversation_direct_mode_bypass(conversation_setup, db_session):
    runtime = conversation_setup["conversation_runtime"]
    
    req = ConversationRequest(
        conversation_id="conv-1",
        message=ConversationMessage(
            role="user",
            content="Hello direct mode"
        ),
        mode=ConversationMode.DIRECT
    )
    
    res = runtime.execute(req, db_session)
    
    assert res.status == ConversationStatus.SUCCESS
    assert res.response_message.content == "Echo: Hello direct mode"
    assert res.diagnostics.planner_invoked is False
    assert res.diagnostics.context_retrieved is False
    assert res.planner_result is None


def test_conversation_planning_mode_execution(conversation_setup, db_session):
    runtime = conversation_setup["conversation_runtime"]
    
    req = ConversationRequest(
        conversation_id="conv-2",
        message=ConversationMessage(
            role="user",
            content="Search for Spec"
        ),
        mode=ConversationMode.PLANNING
    )
    
    res = runtime.execute(req, db_session)
    
    assert res.status == ConversationStatus.SUCCESS
    assert res.diagnostics.planner_invoked is True
    assert res.diagnostics.context_retrieved is True  # Planning mode triggers context
    assert "DeepCore Integration Spec" in res.response_message.content
    assert res.planner_result is not None


def test_conversation_context_trigger(conversation_setup, db_session):
    runtime = conversation_setup["conversation_runtime"]
    
    req = ConversationRequest(
        conversation_id="conv-3",
        message=ConversationMessage(
            role="user",
            content="Simple direct message with context"
        ),
        mode=ConversationMode.DIRECT,
        context_object_uuid="some-uuid"
    )
    
    res = runtime.execute(req, db_session)
    assert res.status == ConversationStatus.SUCCESS
    assert res.diagnostics.context_retrieved is True  # Context retrieved because trigger uuid provided
    assert res.diagnostics.planner_invoked is False  # Still bypassed planner


# ==========================================
# FastAPI Route Tests
# ==========================================

def test_api_conversation_capabilities():
    client = TestClient(app)
    response = client.get("/api/conversation/capabilities")
    
    assert response.status_code == 200
    data = response.json()
    assert "direct" in data["supported_modes"]
    assert "planning" in data["supported_modes"]
    assert data["supports_context"] is True
    assert data["supports_planning"] is True


def test_api_conversation_execution(client, registry_service):
    # 1. Direct Mode Route Execution
    payload_direct = {
        "conversation_id": "api-conv-1",
        "message": {
            "role": "user",
            "content": "Hi API"
        },
        "mode": "direct"
    }
    response_direct = client.post("/api/conversation", json=payload_direct)
    assert response_direct.status_code == 200
    res_data = response_direct.json()
    assert res_data["status"] == "success"
    assert res_data["response_message"]["content"] == "Echo: Hi API"
    assert res_data["diagnostics"]["planner_invoked"] is False
    
    # 2. Planning Mode Route Execution
    payload_plan = {
        "conversation_id": "api-conv-2",
        "message": {
            "role": "user",
            "content": "Search for Spec"
        },
        "mode": "planning"
    }
    response_plan = client.post("/api/conversation", json=payload_plan)
    assert response_plan.status_code == 200
    res_data_plan = response_plan.json()
    assert res_data_plan["status"] == "success"
    assert "DeepCore Integration Spec" in res_data_plan["response_message"]["content"]
    assert res_data_plan["diagnostics"]["planner_invoked"] is True


# ==========================================
# Diagnostics Health Report Check
# ==========================================

def test_health_report_includes_conversation_runtime(conversation_setup):
    health = KernelHealthReport(
        tool_registry=conversation_setup["tool_registry"],
        skill_registry=conversation_setup["skill_registry"],
        execution_registry=conversation_setup["execution_registry"]
    )
    
    summary = health.get_summary()
    assert summary["runtimes"]["conversation_runtime"] == "Initialized"
    
    markdown = health.generate_report_markdown()
    assert "conversation_runtime" in markdown
