import json
from datetime import datetime
from unittest.mock import patch, MagicMock
import httpx
import pytest

from deepcore.core.providers.youtube import extract_video_id, extract_metadata, YouTubeProvider
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import ObjectType

def test_url_extraction():
    """Verify correct video ID is extracted from various YouTube URL formats."""
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ&feature=share",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ?t=10",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "http://youtube.com/watch?v=dQw4w9WgXcQ"
    ]
    for url in urls:
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    invalid_urls = [
        "https://google.com",
        "https://youtube.com/watch?v=dQw4w9WgXc",  # 10 chars (invalid)
        "https://youtube.com/shorts/dQw4w9WgXcQQ",  # 12 chars (invalid)
        "https://youtube.com/channel/UCxxxxxxxxx"
    ]
    for url in invalid_urls:
        assert extract_video_id(url) is None

def test_extract_metadata_helper():
    """Verify that extract_metadata regex extracts attributes correctly from HTML strings."""
    mock_html = """
    <html>
        <head>
            <meta property="og:title" content="Never Gonna Give You Up">
            <meta property="og:image" content="https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg">
            <link itemprop="name" content="Rick Astley">
        </head>
    </html>
    """
    meta = extract_metadata("https://youtube.com/watch?v=dQw4w9WgXcQ", mock_html)
    assert meta["title"] == "Never Gonna Give You Up"
    assert meta["thumbnail"] == "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
    assert meta["channel"] == "Rick Astley"

    # Test reverse order attributes
    mock_html_reverse = """
    <html>
        <head>
            <meta content="Alternative Title" property="og:title">
            <meta content="https://alternate.jpg" property="og:image">
            <link content="Alternative Channel" itemprop="name">
        </head>
    </html>
    """
    meta_rev = extract_metadata("https://youtube.com/watch?v=dQw4w9WgXcQ", mock_html_reverse)
    assert meta_rev["title"] == "Alternative Title"
    assert meta_rev["thumbnail"] == "https://alternate.jpg"
    assert meta_rev["channel"] == "Alternative Channel"


@patch("deepcore.core.providers.youtube.httpx.get")
def test_youtube_provider_sync_success(mock_get, db_session):
    """Test full normal sync flow of YouTubeProvider with mocked successful response."""
    mock_html = """
    <html>
        <head>
            <meta property="og:title" content="Never Gonna Give You Up">
            <meta property="og:image" content="https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg">
            <link itemprop="name" content="Rick Astley">
        </head>
    </html>
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = mock_html
    mock_get.return_value = mock_response

    service = RegistryService(db_session)
    provider = YouTubeProvider(urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])
    
    synced_objs = provider.sync(service)
    assert len(synced_objs) == 1
    
    db_obj = synced_objs[0]
    assert db_obj.object_type == ObjectType.VIDEO
    assert db_obj.title == "Never Gonna Give You Up"
    assert db_obj.source_system == "youtube"
    assert db_obj.external_id == "dQw4w9WgXcQ"
    assert db_obj.location == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert db_obj.provider_version == "youtube_v0.1"

    # Verify metadata_json content
    meta_payload = json.loads(db_obj.metadata_json)
    assert meta_payload["channel"] == "Rick Astley"
    assert meta_payload["thumbnail"] == "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
    assert meta_payload["provider"] == "youtube"
    
    # Ensure captured_at is in ISO format
    captured_at = datetime.fromisoformat(meta_payload["captured_at"])
    assert captured_at is not None


@patch("deepcore.core.providers.youtube.httpx.get")
def test_youtube_provider_sync_fallback_offline(mock_get, db_session):
    """Verify that when network request fails, we gracefully fallback and still register the video."""
    # Simulate network exception (timeout / offline)
    mock_get.side_effect = httpx.RequestError("No Internet")

    service = RegistryService(db_session)
    provider = YouTubeProvider(urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])
    
    synced_objs = provider.sync(service)
    assert len(synced_objs) == 1
    
    db_obj = synced_objs[0]
    # Check that fallback title is used
    assert db_obj.title == "YouTube Video dQw4w9WgXcQ"
    assert db_obj.external_id == "dQw4w9WgXcQ"
    
    meta_payload = json.loads(db_obj.metadata_json)
    assert meta_payload["channel"] is None
    assert meta_payload["thumbnail"] is None
    assert meta_payload["provider"] == "youtube"
    assert "captured_at" in meta_payload


@patch("deepcore.core.providers.youtube.httpx.get")
def test_youtube_provider_duplicate_handling(mock_get, db_session):
    """Verify that syncing the same URL multiple times does not result in duplicate db records."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html></html>"  # simple empty page
    mock_get.return_value = mock_response

    service = RegistryService(db_session)
    provider = YouTubeProvider()
    provider.add_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    
    # Sync first time
    synced1 = provider.sync(service)
    assert len(synced1) == 1
    
    # Queue the same URL again
    provider.add_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    synced2 = provider.sync(service)
    # Should not register anything on second run
    assert len(synced2) == 0
    
    # Verify database has exactly 1 record for this external ID
    records = service.list_objects(filters={"source_system": "youtube", "external_id": "dQw4w9WgXcQ"})
    assert len(records) == 1
