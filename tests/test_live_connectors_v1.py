import os
import json
import pytest
from deepcore.core.acquisition.base import (
    ConnectorOperation,
    ExecutionContext,
    ExecutionRequest,
    ExecutionResponse,
    ConnectorCapabilities,
    SyncContext,
)
from deepcore.connectors.filesystem.connector import FilesystemConnector
from deepcore.connectors.calendar.connector import CalendarConnector
from deepcore.connectors.spotlight.connector import SpotlightConnector


# ============================================================================
# 1. FilesystemConnector Live Tests
# ============================================================================

def test_filesystem_live_capabilities():
    fs = FilesystemConnector()
    caps = fs.capabilities()
    assert isinstance(caps, ConnectorCapabilities)
    assert ConnectorOperation.READ in caps.supported_operations
    assert ConnectorOperation.LIST in caps.supported_operations
    assert ConnectorOperation.SEARCH in caps.supported_operations
    assert caps.requires_configuration is True


def test_filesystem_live_read_list_search(tmp_path):
    # Setup test directory structure
    doc1 = tmp_path / "notes.md"
    doc1.write_text("# DeepCore Notes\nLive execution testing.")
    sub_dir = tmp_path / "projects"
    sub_dir.mkdir()
    doc2 = sub_dir / "tasks.markdown"
    doc2.write_text("# Project Tasks\nTask 1: Build live connector.")

    fs = FilesystemConnector()
    ctx = ExecutionContext(config={"path": str(tmp_path)})

    # Test READ
    read_req = ExecutionRequest(
        operation=ConnectorOperation.READ,
        parameters={"path": str(doc1)},
        context=ctx
    )
    read_resp = fs.execute(read_req)
    assert isinstance(read_resp, ExecutionResponse)
    assert len(read_resp.results) == 1
    assert "Live execution testing" in read_resp.results[0]["content"]

    # Test LIST
    list_req = ExecutionRequest(
        operation=ConnectorOperation.LIST,
        parameters={"path": str(tmp_path)},
        context=ctx
    )
    list_resp = fs.execute(list_req)
    filenames = [item["filename"] for item in list_resp.results]
    assert "notes.md" in filenames
    assert "projects" in filenames

    # Test SEARCH
    search_req = ExecutionRequest(
        operation=ConnectorOperation.SEARCH,
        parameters={"query": "live connector", "path": str(tmp_path)},
        context=ctx
    )
    search_resp = fs.execute(search_req)
    assert len(search_resp.results) >= 1
    assert "tasks.markdown" in search_resp.results[0]["filename"]


def test_filesystem_live_errors(tmp_path):
    fs = FilesystemConnector()
    ctx = ExecutionContext(config={"path": str(tmp_path)})

    # Unsupported operation
    with pytest.raises(NotImplementedError):
        fs.execute(ExecutionRequest(operation=ConnectorOperation.ACTION, context=ctx))

    # Read nonexistent file
    with pytest.raises(FileNotFoundError):
        fs.execute(ExecutionRequest(
            operation=ConnectorOperation.READ,
            parameters={"path": str(tmp_path / "nonexistent.md")},
            context=ctx
        ))


# ============================================================================
# 2. CalendarConnector Live Tests
# ============================================================================

def test_calendar_live_capabilities():
    cal = CalendarConnector()
    caps = cal.capabilities()
    assert isinstance(caps, ConnectorCapabilities)
    assert ConnectorOperation.READ in caps.supported_operations
    assert ConnectorOperation.LIST in caps.supported_operations
    assert ConnectorOperation.SEARCH in caps.supported_operations


def test_calendar_live_read_list_search(tmp_path):
    cal_file = tmp_path / "mock_cal.json"
    mock_events = [
        {
            "uid": "evt_101",
            "summary": "DeepCore Architecture Review",
            "description": "Live connector evolution review meeting.",
            "start_time": "2026-07-29T10:00:00Z",
            "end_time": "2026-07-29T11:00:00Z",
            "location": {"title": "Virtual Room"}
        },
        {
            "uid": "evt_102",
            "summary": "Team Standup",
            "description": "Daily sync",
            "start_time": "2026-07-29T14:00:00Z",
            "end_time": "2026-07-29T14:30:00Z",
            "location": {"title": "Standup Room"}
        }
    ]
    cal_file.write_text(json.dumps(mock_events))

    cal = CalendarConnector()
    ctx = ExecutionContext(config={"mock_file_path": str(cal_file)})

    # Test LIST
    list_resp = cal.execute(ExecutionRequest(operation=ConnectorOperation.LIST, context=ctx))
    assert len(list_resp.results) == 2

    # Test READ
    read_resp = cal.execute(ExecutionRequest(
        operation=ConnectorOperation.READ,
        parameters={"uid": "evt_101"},
        context=ctx
    ))
    assert len(read_resp.results) == 1
    assert read_resp.results[0]["summary"] == "DeepCore Architecture Review"

    # Test SEARCH
    search_resp = cal.execute(ExecutionRequest(
        operation=ConnectorOperation.SEARCH,
        parameters={"query": "standup"},
        context=ctx
    ))
    assert len(search_resp.results) == 1
    assert search_resp.results[0]["uid"] == "evt_102"


def test_calendar_live_errors(tmp_path):
    cal = CalendarConnector()
    ctx = ExecutionContext(config={"mock_file_path": str(tmp_path / "empty.json")})

    # Unsupported operation
    with pytest.raises(NotImplementedError):
        cal.execute(ExecutionRequest(operation=ConnectorOperation.QUERY, context=ctx))

    # Read missing uid
    with pytest.raises(ValueError):
        cal.execute(ExecutionRequest(operation=ConnectorOperation.READ, context=ctx))


# ============================================================================
# 3. SpotlightConnector Live Tests
# ============================================================================

def test_spotlight_live_capabilities():
    spot = SpotlightConnector()
    caps = spot.capabilities()
    assert isinstance(caps, ConnectorCapabilities)
    assert ConnectorOperation.SEARCH in caps.supported_operations
    assert ConnectorOperation.READ in caps.supported_operations


def test_spotlight_live_search_read(tmp_path):
    test_file = tmp_path / "spotlight_test_doc.md"
    test_file.write_text("# Spotlight Test Document")

    spot = SpotlightConnector()
    ctx = ExecutionContext(config={"search_path": str(tmp_path)})

    # Test SEARCH
    search_resp = spot.execute(ExecutionRequest(
        operation=ConnectorOperation.SEARCH,
        parameters={"query": "spotlight_test"},
        context=ctx
    ))
    assert isinstance(search_resp, ExecutionResponse)
    assert len(search_resp.results) >= 1
    matching_names = [item["filename"] for item in search_resp.results]
    assert "spotlight_test_doc.md" in matching_names

    # Test READ
    read_resp = spot.execute(ExecutionRequest(
        operation=ConnectorOperation.READ,
        parameters={"path": str(test_file)},
        context=ctx
    ))
    assert len(read_resp.results) == 1
    assert read_resp.results[0]["filename"] == "spotlight_test_doc.md"


def test_spotlight_live_errors(tmp_path):
    spot = SpotlightConnector()
    ctx = ExecutionContext(config={"search_path": str(tmp_path)})

    # Unsupported operation
    with pytest.raises(NotImplementedError):
        spot.execute(ExecutionRequest(operation=ConnectorOperation.LIST, context=ctx))

    # Read nonexistent file
    with pytest.raises(FileNotFoundError):
        spot.execute(ExecutionRequest(
            operation=ConnectorOperation.READ,
            parameters={"path": str(tmp_path / "missing.md")},
            context=ctx
        ))


# ============================================================================
# 4. Backward Compatibility Ingestion Tests
# ============================================================================

def test_v1_connectors_ingestion_coexistence(tmp_path):
    """Confirm existing discover/sync methods continue to function unmodified."""
    # Filesystem
    test_file = tmp_path / "ingest.md"
    test_file.write_text("# Ingestion File")
    sync_ctx = SyncContext(workspace_id=1, source_id=1, config={"path": str(tmp_path)}, credentials={})
    
    fs = FilesystemConnector()
    fs_items = list(fs.discover(sync_ctx))
    assert len(fs_items) == 1
    assert fs_items[0]["filename"] == "ingest.md"

    # Calendar
    cal_file = tmp_path / "cal_ingest.json"
    cal_file.write_text(json.dumps([{"uid": "i1", "summary": "Ingest Evt", "modified_at_ts": 100.0}]))
    cal_ctx = SyncContext(workspace_id=1, source_id=2, config={"mock_file_path": str(cal_file)}, credentials={})
    
    cal = CalendarConnector()
    cal_items = list(cal.discover(cal_ctx))
    assert len(cal_items) == 1
    assert cal_items[0]["uid"] == "i1"

    # Spotlight
    spot_ctx = SyncContext(workspace_id=1, source_id=3, config={"search_path": str(tmp_path)}, credentials={})
    spot = SpotlightConnector()
    spot_items = list(spot.discover(spot_ctx))
    assert len(spot_items) >= 1
