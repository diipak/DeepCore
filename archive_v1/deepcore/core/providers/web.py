import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import List, Optional, Any
import httpx

from deepcore.core.providers.base import BaseProvider
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObjectCreate

def is_valid_web_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False

def extract_web_metadata(html: str) -> dict:
    metadata = {
        "title": None,
        "description": None
    }
    # Title tag extraction
    title_tag = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    if title_tag:
        metadata["title"] = title_tag.group(1).strip()
        
    # og:title extraction
    t_match = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html)
    if not t_match:
        t_match = re.search(r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:title["\']', html)
    if t_match:
        metadata["title"] = t_match.group(1)
        
    # og:description extraction
    d_match = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']+)["\']', html)
    if not d_match:
        d_match = re.search(r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:description["\']', html)
    if d_match:
        metadata["description"] = d_match.group(1)
        
    return metadata


class WebProvider(BaseProvider):
    @classmethod
    def can_handle(cls, content: Any) -> bool:
        if isinstance(content, str):
            return is_valid_web_url(content)
        return False

    def __init__(self, urls: Optional[List[str]] = None):
        self.urls = urls or []

    def add_url(self, url: str) -> None:
        self.urls.append(url)

    def discover(self, *args, **kwargs) -> List[str]:
        discovered = list(self.urls)
        self.urls.clear()
        return discovered

    def normalize(self, raw_data: str) -> dict:
        url = raw_data
        
        metadata = {
            "title": None,
            "description": None
        }
        
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
            response = httpx.get(url, headers=headers, timeout=3.0)
            if response.status_code == 200:
                metadata = extract_web_metadata(response.text)
        except Exception:
            pass

        # Fallback to URL netloc/path if title not found
        fallback_title = url
        try:
            parsed = urlparse(url)
            fallback_title = parsed.netloc + parsed.path
            if fallback_title.endswith("/"):
                fallback_title = fallback_title[:-1]
        except Exception:
            pass

        title = metadata.get("title") or fallback_title
        description = metadata.get("description")

        metadata_payload = {
            "url": url,
            "provider": "web",
            "captured_at": datetime.now(timezone.utc).isoformat()
        }

        return {
            "object_type": "document",
            "title": title,
            "source_system": "web",
            "external_id": url,
            "location": url,
            "description": description,
            "status": "active",
            "metadata_json": json.dumps(metadata_payload),
            "provider_version": "web_v0.1"
        }

    def sync(self, registry_service: RegistryService, *args, **kwargs) -> List[Any]:
        urls = self.discover()
        registered_objects = []

        for url in urls:
            if not is_valid_web_url(url):
                continue
            
            # Duplicate check
            existing = registry_service.list_objects(filters={
                "source_system": "web",
                "external_id": url
            })
            if existing:
                continue

            try:
                normalized = self.normalize(url)
                obj_create = RegistryObjectCreate(**normalized)
                db_obj = registry_service.register_object(obj_create)
                registered_objects.append(db_obj)
            except Exception:
                continue

        return registered_objects
