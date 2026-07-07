import json
import re
from datetime import datetime, timezone
from typing import List, Optional, Any
import httpx

from deepcore.core.providers.base import BaseProvider
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObjectCreate

def extract_video_id(url: str) -> Optional[str]:
    """Extract the 11-character YouTube video ID from various URL formats."""
    # Standard watch URL: youtube.com/watch?v=...
    match = re.search(r'(?:youtube\.com/watch\?v=|youtube\.com/watch\?.*&v=)([a-zA-Z0-9_-]{11})(?![a-zA-Z0-9_-])', url)
    if match:
        return match.group(1)
        
    # Short URL: youtu.be/...
    match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})(?![a-zA-Z0-9_-])', url)
    if match:
        return match.group(1)
        
    # Embed URL: youtube.com/embed/...
    match = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]{11})(?![a-zA-Z0-9_-])', url)
    if match:
        return match.group(1)
        
    # Shorts URL: youtube.com/shorts/...
    match = re.search(r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})(?![a-zA-Z0-9_-])', url)
    if match:
        return match.group(1)
        
    return None

def extract_metadata(url: str, html: str) -> dict:
    """Helper function to parse OpenGraph and page tags for metadata from YouTube HTML."""
    metadata = {
        "title": None,
        "channel": None,
        "thumbnail": None
    }
    
    # Title extraction
    t_match1 = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html)
    t_match2 = re.search(r'<meta\s+content="([^"]+)"\s+property="og:title"', html)
    if t_match1:
        metadata["title"] = t_match1.group(1)
    elif t_match2:
        metadata["title"] = t_match2.group(1)
        
    # Thumbnail extraction
    img_match1 = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
    img_match2 = re.search(r'<meta\s+content="([^"]+)"\s+property="og:image"', html)
    if img_match1:
        metadata["thumbnail"] = img_match1.group(1)
    elif img_match2:
        metadata["thumbnail"] = img_match2.group(1)
        
    # Channel name extraction
    ch_match1 = re.search(r'<link\s+itemprop="name"\s+content="([^"]+)"', html)
    ch_match2 = re.search(r'<link\s+content="([^"]+)"\s+itemprop="name"', html)
    if ch_match1:
        metadata["channel"] = ch_match1.group(1)
    elif ch_match2:
        metadata["channel"] = ch_match2.group(1)
        
    return metadata


class YouTubeProvider(BaseProvider):
    def __init__(self, urls: Optional[List[str]] = None):
        """Initialize provider with an optional list of raw YouTube URLs."""
        self.urls = urls or []

    def add_url(self, url: str) -> None:
        """Add a single YouTube URL to the sync queue."""
        self.urls.append(url)

    def discover(self, *args, **kwargs) -> List[str]:
        """Discover URLs in the queue and clear it."""
        discovered = list(self.urls)
        self.urls.clear()
        return discovered

    def normalize(self, raw_data: str) -> dict:
        """Fetch and extract video details and normalize into RegistryObject format.
        
        raw_data represents the YouTube URL string.
        """
        url = raw_data
        video_id = extract_video_id(url)
        if not video_id:
            raise ValueError(f"Could not extract a valid 11-character video ID from URL: {url}")

        # Attempt to scrape metadata without authentication
        metadata = {
            "title": None,
            "channel": None,
            "thumbnail": None
        }
        try:
            # We use a standard browser User-Agent headers to fetch video page HTML
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
            # Fetch content with 3-second timeout
            response = httpx.get(url, headers=headers, timeout=3.0)
            if response.status_code == 200:
                metadata = extract_metadata(url, response.text)
        except Exception:
            # Silently catch network failures/timeouts and proceed with empty values
            pass

        # Fallback values
        title = metadata.get("title") or f"YouTube Video {video_id}"
        
        metadata_payload = {
            "channel": metadata.get("channel"),
            "thumbnail": metadata.get("thumbnail"),
            "provider": "youtube",
            "captured_at": datetime.now(timezone.utc).isoformat()
        }

        return {
            "object_type": "video",
            "title": title,
            "source_system": "youtube",
            "external_id": video_id,
            "location": url,
            "description": None,
            "status": "active",
            "metadata_json": json.dumps(metadata_payload),
            "provider_version": "youtube_v0.1"
        }

    def sync(self, registry_service: RegistryService, *args, **kwargs) -> List[Any]:
        """Process URLs, prevent duplicates, and register new videos in the database."""
        urls = self.discover()
        registered_objects = []

        for url in urls:
            video_id = extract_video_id(url)
            if not video_id:
                continue

            # Duplicate check
            existing = registry_service.list_objects(filters={
                "source_system": "youtube",
                "external_id": video_id
            })
            if existing:
                # Skip already registered video to prevent duplicates
                continue

            try:
                normalized = self.normalize(url)
                obj_create = RegistryObjectCreate(**normalized)
                db_obj = registry_service.register_object(obj_create)
                registered_objects.append(db_obj)
            except Exception:
                # Gracefully skip if normalization or db registration fails
                continue

        return registered_objects
