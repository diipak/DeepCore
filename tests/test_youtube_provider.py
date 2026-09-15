import os
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


def test_extract_playlist_id():
    """Verify playlist ID is extracted from various playlist URL formats."""
    from deepcore2.core.providers.youtube import extract_playlist_id

    assert extract_playlist_id("https://youtube.com/playlist?list=PLDummyPlaylistId123&si=sampleToken123") == "PLDummyPlaylistId123"
    assert extract_playlist_id("https://www.youtube.com/watch?v=12345678901&list=PLTest123") == "PLTest123"
    assert extract_playlist_id("https://youtube.com/watch?v=12345678901") is None


def test_format_youtube_markdown_note():
    """Verify markdown note formatting includes YAML frontmatter and spoken transcript."""
    from deepcore2.core.providers.youtube import format_youtube_markdown_note

    metadata = {
        "title": "Exceptional Memory Systems",
        "channel": "Han Zhango",
        "channel_url": "https://www.youtube.com/@hanzhango",
        "thumbnail": "https://i.ytimg.com/vi/test/hqdefault.jpg",
    }
    transcript = "Memory palace techniques allow rapid spatial encoding of facts."
    note = format_youtube_markdown_note("test1234567", metadata, transcript, "available")

    assert "type: youtube_capture" in note
    assert "video_id: \"test1234567\"" in note
    assert "title: \"Exceptional Memory Systems\"" in note
    assert "channel: \"Han Zhango\"" in note
    assert "## Spoken Transcript" in note
    assert "Memory palace techniques allow rapid spatial encoding of facts." in note


def test_sync_youtube_playlist_workflow(tmp_path):
    """Verify sync_youtube_playlist writes notes, skips duplicates, and isolates transcript errors."""
    from deepcore2.core.providers.youtube import sync_youtube_playlist

    with patch("deepcore2.core.providers.youtube.fetch_playlist_video_ids") as mock_fetch_ids, \
         patch("deepcore2.core.providers.youtube.fetch_video_metadata") as mock_meta, \
         patch("deepcore2.core.providers.youtube.fetch_video_transcript") as mock_trans:

        mock_fetch_ids.return_value = ["vid11111111", "vid22222222"]
        mock_meta.side_effect = lambda vid: {"title": f"Title for {vid}", "channel": "Test Channel"}
        mock_trans.side_effect = lambda vid: ("Transcript text", "available") if vid == "vid11111111" else (None, "unavailable")

        res1 = sync_youtube_playlist("https://youtube.com/playlist?list=PL123", output_dir=str(tmp_path))

        assert res1["scanned"] == 2
        assert res1["new_written"] == 2
        assert res1["skipped"] == 0

        # Verify files were created on disk
        files = os.listdir(str(tmp_path))
        assert len(files) == 2
        assert any("vid11111111" in f for f in files)
        assert any("vid22222222" in f for f in files)

        # Sync again: should skip both as already present
        res2 = sync_youtube_playlist("https://youtube.com/playlist?list=PL123", output_dir=str(tmp_path))
        assert res2["scanned"] == 2
        assert res2["new_written"] == 0
        assert res2["skipped"] == 2

