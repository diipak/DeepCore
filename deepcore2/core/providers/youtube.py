import json
import re
from datetime import datetime, timezone
from typing import List, Optional, Any
import httpx

from deepcore2.core.providers.base import BaseProvider
from deepcore2.core.registry.service import RegistryService
from deepcore2.core.objects.schemas import RegistryObjectCreate

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
    t_match1 = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html)
    t_match2 = re.search(r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:title["\']', html)
    if t_match1:
        metadata["title"] = t_match1.group(1)
    elif t_match2:
        metadata["title"] = t_match2.group(1)
        
    # Thumbnail extraction
    img_match1 = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html)
    img_match2 = re.search(r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:image["\']', html)
    if img_match1:
        metadata["thumbnail"] = img_match1.group(1)
    elif img_match2:
        metadata["thumbnail"] = img_match2.group(1)
        
    # Channel name extraction
    ch_match1 = re.search(r'<link\s+itemprop=["\']name["\']\s+content=["\']([^"\']+)["\']', html)
    ch_match2 = re.search(r'<link\s+content=["\']([^"\']+)["\']\s+itemprop=["\']name["\']', html)
    if ch_match1:
        metadata["channel"] = ch_match1.group(1)
    elif ch_match2:
        metadata["channel"] = ch_match2.group(1)
        
    return metadata


class YouTubeProvider(BaseProvider):
    @classmethod
    def can_handle(cls, content: Any) -> bool:
        """Return True if the content is a valid YouTube URL."""
        if isinstance(content, str):
            return extract_video_id(content) is not None
        return False

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
            "source_url": url,
            "video_id": video_id,
            "title": title,
            "channel": metadata.get("channel"),
            "thumbnail": metadata.get("thumbnail"),
            "transcript_placeholder": "Transcript sync pending...",
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


def extract_playlist_id(url: str) -> Optional[str]:
    """Extract playlist ID from a YouTube playlist URL."""
    match = re.search(r'[?&]list=([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return None


def fetch_playlist_video_ids(playlist_url_or_id: str) -> List[str]:
    """Discover video IDs from a YouTube playlist URL or ID with zero API keys."""
    playlist_id = extract_playlist_id(playlist_url_or_id) or playlist_url_or_id
    url = f"https://www.youtube.com/playlist?list={playlist_id}"

    cookies = {
        'SOCS': 'CAESEwgDEgk2OTU4NjgxOTMaAmRlIAEaBgiA_LyaBg',
        'CONSENT': 'PENDING+999',
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    try:
        resp = httpx.get(url, headers=headers, cookies=cookies, follow_redirects=True, timeout=15.0)
        if resp.status_code == 200:
            raw_ids = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', resp.text)
            return list(dict.fromkeys(raw_ids))
    except Exception:
        pass
    return []


def fetch_video_metadata(video_id: str) -> dict:
    """Fetch structured video metadata using oEmbed with fallback."""
    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        resp = httpx.get(oembed_url, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "title": data.get("title") or f"YouTube Video {video_id}",
                "channel": data.get("author_name") or "Unknown Channel",
                "channel_url": data.get("author_url"),
                "thumbnail": data.get("thumbnail_url") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            }
    except Exception:
        pass
    return {
        "title": f"YouTube Video {video_id}",
        "channel": "Unknown Channel",
        "channel_url": None,
        "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
    }


def fetch_video_transcript(video_id: str) -> tuple[Optional[str], str]:
    """Fetch spoken transcript using youtube-transcript-api. Returns (transcript_text, status)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id)
        if fetched and fetched.snippets:
            paragraphs = []
            current_paragraph = []
            for entry in fetched.snippets:
                text = entry.text.strip()
                if not text:
                    continue
                current_paragraph.append(text)
                if len(current_paragraph) >= 6 or text.endswith(('.', '?', '!')):
                    paragraphs.append(" ".join(current_paragraph))
                    current_paragraph = []
            if current_paragraph:
                paragraphs.append(" ".join(current_paragraph))
            return "\n\n".join(paragraphs), "available"
    except Exception as exc:
        return None, f"unavailable ({exc})"
    return None, "unavailable (empty)"


def format_youtube_markdown_note(video_id: str, metadata: dict, transcript_text: Optional[str], transcript_status: str) -> str:
    """Generate clean Obsidian-compatible Markdown note with YAML frontmatter."""
    captured_iso = datetime.now(timezone.utc).isoformat()
    clean_title = (metadata.get("title") or f"YouTube Video {video_id}").replace('"', '\\"')
    channel = (metadata.get("channel") or "Unknown Channel").replace('"', '\\"')
    thumb = metadata.get("thumbnail", "")

    frontmatter = (
        "---\n"
        f"type: youtube_capture\n"
        f"video_id: \"{video_id}\"\n"
        f"title: \"{clean_title}\"\n"
        f"channel: \"{channel}\"\n"
        f"url: \"https://www.youtube.com/watch?v={video_id}\"\n"
        f"thumbnail: \"{thumb}\"\n"
        f"transcript_status: \"{transcript_status}\"\n"
        f"captured_at: \"{captured_iso}\"\n"
        f"source: youtube\n"
        "---\n\n"
    )

    body = (
        f"# {clean_title}\n\n"
        f"> **Channel**: [{channel}]({metadata.get('channel_url') or f'https://www.youtube.com/watch?v={video_id}'})  \n"
        f"> **Source**: [Watch on YouTube](https://www.youtube.com/watch?v={video_id})  \n"
        f"> **Captured**: {captured_iso[:10]}  \n\n"
        f"## Spoken Transcript\n\n"
    )

    if transcript_text:
        body += transcript_text + "\n"
    else:
        body += f"*(Spoken transcript unavailable: {transcript_status})*\n"

    return frontmatter + body


def sync_youtube_playlist(
    playlist_url: str,
    output_dir: Optional[str] = None,
    db: Optional[Any] = None,
    vault_source_id: int = 1,
) -> dict:
    """
    Sync a YouTube playlist: discovers videos, fetches transcripts, writes .md notes
    to output_dir, triggers KnowledgeSync for the vault source, and indexes objects.
    """
    import os
    from deepcore2.config import settings

    if not output_dir:
        output_dir = getattr(settings, "YOUTUBE_CAPTURES_DIR", os.path.expanduser("~/Documents/Notes/AI/Captures/YouTube"))
    os.makedirs(output_dir, exist_ok=True)

    video_ids = fetch_playlist_video_ids(playlist_url)
    if not video_ids:
        return {"scanned": 0, "new_written": 0, "skipped": 0, "indexed": 0, "error": "No videos found in playlist"}

    # Identify already saved videos
    existing_files = os.listdir(output_dir) if os.path.exists(output_dir) else []
    existing_ids = set()
    for fname in existing_files:
        match = re.match(r'^([a-zA-Z0-9_-]{11})\b', fname)
        if match:
            existing_ids.add(match.group(1))

    new_written = 0
    skipped = 0

    for vid in video_ids:
        if vid in existing_ids:
            skipped += 1
            continue

        metadata = fetch_video_metadata(vid)
        transcript_text, status = fetch_video_transcript(vid)
        note_content = format_youtube_markdown_note(vid, metadata, transcript_text, status)

        # Sanitize filename
        safe_title = re.sub(r'[\\/*?:"<>|]', "", metadata.get("title", ""))[:60].strip()
        filename = f"{vid} - {safe_title}.md" if safe_title else f"{vid}.md"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(note_content)

        existing_ids.add(vid)
        new_written += 1

    # If new notes were written and a DB session is provided, trigger sync and indexing
    indexed_count = 0
    if db is not None and new_written > 0:
        try:
            from deepcore2.runtime.composition import get_application
            from deepcore2.core.content.service import ContentService
            app = get_application()
            if app and app.acquisition_runtime:
                connector_cls = app.acquisition_manager.get_connector_class("filesystem")
                translator_cls = app.acquisition_manager.get_translator_class("filesystem")
                app.acquisition_runtime.run_sync(
                    source_id=vault_source_id,
                    connector=connector_cls(),
                    translator=translator_cls(),
                    full_sync=False,
                    db=db,
                )
            content_service = ContentService(db)
            index_stats = content_service.index_all_active_objects()
            indexed_count = index_stats.get("indexed", 0)
        except Exception:
            pass

    return {
        "scanned": len(video_ids),
        "new_written": new_written,
        "skipped": skipped,
        "indexed": indexed_count,
    }

