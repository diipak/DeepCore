import pytest
from fastapi.testclient import TestClient

from deepcore.storage.sqlite.db import get_db
from deepcore.api.main import app
from deepcore.runtime.descriptors import DescriptorCategory


@pytest.fixture
def api_client(client):
    yield client


# ==========================================
# Test Cases
# ==========================================

def test_get_capabilities_catalog(api_client):
    response = api_client.get("/api/capabilities")
    assert response.status_code == 200
    
    data = response.json()
    assert "categories" in data
    assert isinstance(data["categories"], list)
    assert len(data["categories"]) > 0
    
    # Check category groups and display names
    for group in data["categories"]:
        assert "category" in group
        assert "display_name" in group
        assert "capabilities" in group
        
        # Display name capitalization
        assert group["display_name"] == group["category"].capitalize()
        
        # Capabilities are summaries, meaning they have a standard set of keys
        for cap in group["capabilities"]:
            assert "id" in cap
            assert "name" in cap
            assert "category" in cap
            assert cap["category"] == group["category"]


def test_get_capability_details_and_errors(api_client):
    # Retrieve standard tool_calc details
    response = api_client.get("/api/capabilities/echo_tool")
    assert response.status_code == 200
    
    data = response.json()
    assert "summary" in data
    assert "details" in data
    assert data["summary"]["id"] == "echo_tool"
    assert data["summary"]["category"] == "tool"
    
    # Check that tool-specific schema fields are present inside details
    assert "input_schema" in data["details"]
    assert "output_schema" in data["details"]
    assert "safety" in data["details"]

    # Request missing ID -> 404
    response_missing = api_client.get("/api/capabilities/nonexistent_id")
    assert response_missing.status_code == 404
    assert "not found" in response_missing.json()["detail"].lower()


def test_get_by_category_and_errors(api_client):
    # 1. Valid category
    response = api_client.get("/api/capabilities/category/tool")
    assert response.status_code == 200
    
    summaries = response.json()
    assert isinstance(summaries, list)
    assert len(summaries) >= 2
    assert all(s["category"] == "tool" for s in summaries)
    
    # Case insensitivity check
    response_upper = api_client.get("/api/capabilities/category/TOOL")
    assert response_upper.status_code == 200
    assert len(response_upper.json()) == len(summaries)

    # 2. Invalid category -> 422 Unprocessable Entity
    response_invalid = api_client.get("/api/capabilities/category/invalid_cat")
    assert response_invalid.status_code == 422
    assert "invalid category" in response_invalid.json()["detail"].lower()


def test_filtering_endpoints(api_client):
    # Filter enabled capabilities
    response_enabled = api_client.get("/api/capabilities/filter?enabled=true")
    assert response_enabled.status_code == 200
    
    enabled_data = response_enabled.json()
    assert len(enabled_data) > 0
    assert all(item["enabled"] is True for item in enabled_data)
    
    # Filter configurable capabilities
    response_config = api_client.get("/api/capabilities/filter?configurable=true")
    assert response_config.status_code == 200
    config_data = response_config.json()
    assert all(item["configurable"] is True for item in config_data)
    # Check that filesystem provider is in the list
    assert any(item["id"] == "filesystem" for item in config_data)
