import json
from datetime import datetime
from unittest.mock import patch, MagicMock
import httpx
import pytest

from deepcore.core.capture.service import CaptureService, UnsupportedInputError
from deepcore.core.objects.schemas import ObjectType

@patch("deepcore.core.providers.youtube.httpx.get")
def test_capture_youtube_success(mock_get, db_session):
    """Verify that capturing a valid YouTube URL routes correctly, registers the video, and stamps metadata."""
    mock_html = """
    <html>
        <head>
            <meta property="og:title" content="Rickroll">
            <meta property="og:image" content="https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg">
            <link itemprop="name" content="Rick Astley">
        </head>
    </html>
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = mock_html
    mock_get.return_value = mock_response

    service = CaptureService(db_session)
    obj = service.capture("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    
    assert obj is not None
    assert obj.object_type == ObjectType.VIDEO
    assert obj.title == "Rickroll"
    assert obj.source_system == "youtube"
    assert obj.external_id == "dQw4w9WgXcQ"
    
    # Verify metadata_json content contains capture metadata AND provider metadata
    meta = json.loads(obj.metadata_json)
    assert meta["channel"] == "Rick Astley"
    assert meta["thumbnail"] == "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
    assert meta["provider"] == "youtube"
    assert meta["captured_via"] == "capture"
    assert "captured_at" in meta
    # Verify ISO timestamp
    captured_at = datetime.fromisoformat(meta["captured_at"])
    assert captured_at is not None

def test_capture_unsupported_input(db_session):
    """Verify that unsupported URLs or raw strings throw UnsupportedInputError."""
    service = CaptureService(db_session)
    with pytest.raises(UnsupportedInputError):
        service.capture("https://google.com")
        
    with pytest.raises(UnsupportedInputError):
        service.capture("Just random text string")

@patch("deepcore.core.providers.youtube.httpx.get")
def test_capture_youtube_duplicate(mock_get, db_session):
    """Verify that capturing a duplicate YouTube URL returns the existing record and updates capture metadata."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html></html>"
    mock_get.return_value = mock_response

    service = CaptureService(db_session)
    
    # Capture first time
    obj1 = service.capture("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert obj1 is not None
    
    # Capture second time
    obj2 = service.capture("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert obj2 is not None
    
    # Verify same object is returned
    assert obj1.id == obj2.id
    assert obj1.uuid == obj2.uuid
    
    # Verify no duplicate db entry was created
    from deepcore.storage.sqlite.models import RegistryObject
    records = db_session.query(RegistryObject).filter(
        RegistryObject.source_system == "youtube",
        RegistryObject.external_id == "dQw4w9WgXcQ"
    ).all()
    assert len(records) == 1
    
    # Verify metadata still has capture stamps
    meta = json.loads(obj2.metadata_json)
    assert meta["captured_via"] == "capture"
    assert "captured_at" in meta

@patch("deepcore.core.providers.youtube.httpx.get")
def test_capture_api_endpoint(mock_get, client):
    """Verify HTTP API endpoint behavior for POST /capture."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><head><meta property='og:title' content='Test Video'></head></html>"
    mock_get.return_value = mock_response

    # 1. Test POST /capture with valid YouTube URL
    response = client.post("/capture", json={"content": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Video"
    assert data["source_system"] == "youtube"
    
    meta = json.loads(data["metadata_json"])
    assert meta["captured_via"] == "capture"
    assert "captured_at" in meta

    # 2. Test POST /capture with unsupported URL
    response_unsupported = client.post("/capture", json={"content": "https://google.com"})
    assert response_unsupported.status_code == 400
    assert "Unsupported input content" in response_unsupported.json()["detail"]
