import json
import re
from datetime import datetime, timezone
from typing import List, Optional, Any
import httpx

from deepcore.core.providers.base import BaseProvider
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObjectCreate
from deepcore.intelligence.object_detector import GitHubDetector

def extract_github_info(url: str) -> Optional[dict]:
    detector = GitHubDetector()
    results = detector.detect(url)
    if results:
        return results[0]["meta"]
    return None

def extract_github_metadata(html: str) -> dict:
    metadata = {
        "title": None,
        "description": None
    }
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


class GitHubProvider(BaseProvider):
    @classmethod
    def can_handle(cls, content: Any) -> bool:
        if isinstance(content, str):
            return extract_github_info(content) is not None
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
        info = extract_github_info(url)
        if not info:
            raise ValueError(f"Could not extract GitHub info from URL: {url}")
            
        user = info["user"]
        repo = info["repo"]
        
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
                metadata = extract_github_metadata(response.text)
        except Exception:
            pass

        title = metadata.get("title") or f"{user}/{repo}"
        description = metadata.get("description")

        metadata_payload = {
            "user": user,
            "repo": repo,
            "provider": "github",
            "captured_at": datetime.now(timezone.utc).isoformat()
        }

        return {
            "object_type": "repository",
            "title": title,
            "source_system": "github",
            "external_id": f"{user}/{repo}",
            "location": url,
            "description": description,
            "status": "active",
            "metadata_json": json.dumps(metadata_payload),
            "provider_version": "github_v0.1"
        }

    def sync(self, registry_service: RegistryService, *args, **kwargs) -> List[Any]:
        urls = self.discover()
        registered_objects = []

        for url in urls:
            info = extract_github_info(url)
            if not info:
                continue

            external_id = f"{info['user']}/{info['repo']}"
            
            # Duplicate check
            existing = registry_service.list_objects(filters={
                "source_system": "github",
                "external_id": external_id
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
