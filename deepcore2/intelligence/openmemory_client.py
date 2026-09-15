"""
Client for the local OpenMemory service (http://127.0.0.1:8765).

Provides scoped, privacy-hardened semantic memory retrieval for DeepCore.
Includes dual-layer namespace rejection (bracket tag prefix + normalized body check)
to strictly prevent foreign project memories (Personal_Finz, PoojaMusic, AlgoMirror, Career)
from leaking into DeepCore prompts or citations.
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional
import httpx

from deepcore2.config import settings

logger = logging.getLogger(__name__)


class OpenMemoryUnavailableError(Exception):
    """Raised when the local OpenMemory service is unreachable, times out, or returns an error."""
    pass


@dataclass
class OpenMemoryItem:
    """Represents a validated memory item retrieved from OpenMemory."""
    id: str
    content: str
    app_name: str
    categories: List[str] = field(default_factory=list)
    created_at: int = 0
    namespace: Optional[str] = None


class OpenMemoryClient:
    """Synchronous HTTP client for querying local OpenMemory with privacy boundary filtering."""

    def __init__(
        self,
        host: Optional[str] = None,
        user_id: Optional[str] = None,
        timeout: Optional[float] = None,
        default_categories: Optional[List[str]] = None,
        excluded_namespaces: Optional[List[str]] = None,
    ):
        self.host = (host or settings.OPENMEMORY_HOST).rstrip("/")
        self.user_id = user_id or settings.OPENMEMORY_USER_ID
        self.timeout = timeout if timeout is not None else settings.OPENMEMORY_TIMEOUT_SECONDS
        self.default_categories = default_categories or settings.OPENMEMORY_DEFAULT_CATEGORIES
        self.excluded_namespaces = [
            n.lower().strip() for n in (excluded_namespaces or settings.OPENMEMORY_EXCLUDED_NAMESPACES)
        ]

    def extract_namespace(self, content: str) -> Optional[str]:
        """Extract the leading bracket tag prefix if present, e.g. '[Topic / Sub]' -> 'Topic / Sub'."""
        match = re.match(r"^\[(.*?)\]", content.strip())
        return match.group(1).strip() if match else None

    def is_namespace_allowed(self, content: str) -> bool:
        """
        Dual-layer privacy & namespace filter:
        1. Check bracket tag prefix: reject if tag starts with or contains any excluded namespace.
        2. Check body content: reject if any excluded project name is mentioned in the body,
           regardless of what generic cross-cutting tag (Design/, UI/, Workflow/) was used.
        """
        namespace = self.extract_namespace(content)
        if namespace:
            clean_ns = namespace.lower()
            norm_ns = clean_ns.replace("_", "").replace("-", "")
            for p in self.excluded_namespaces:
                clean_p = p.replace("_", "").replace("-", "")
                if clean_ns.startswith(p) or clean_p in norm_ns:
                    return False

        # Body content check (catches cross-cutting tag leaks like [Design/VisualLanguage] Personal_Finz ...)
        norm_content = content.lower().replace("_", "").replace("-", "")
        for p in self.excluded_namespaces:
            clean_p = p.replace("_", "").replace("-", "")
            if clean_p in norm_content:
                return False

        return True

    def search_memories(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        limit: int = 3
    ) -> List[OpenMemoryItem]:
        """
        Query OpenMemory with bounded latency and strict namespace filtering.
        Extracts salient keywords from query to rank candidates retrieved from OpenMemory.

        Raises OpenMemoryUnavailableError on network/timeout failures so callers
        can degrade gracefully to SQLite context.
        """
        cats = categories or self.default_categories
        stop_words = {
            "what", "is", "the", "for", "with", "this", "that", "how", "why",
            "can", "you", "tell", "about", "from", "and", "are", "have", "been",
            "will", "does", "were", "should", "could", "would", "which"
        }
        words = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", query.lower())
        keywords = [w for w in words if w not in stop_words]

        # OpenMemory REST API /api/v1/memories/ filters by SQL ILIKE.
        # To avoid sentence-length mismatch, fetch the active candidate pool and rank locally.
        params = {
            "user_id": self.user_id,
            "categories": ",".join(cats),
            "size": max(limit * 10, 50),
        }

        try:
            response = httpx.get(
                f"{self.host}/api/v1/memories/",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise OpenMemoryUnavailableError(
                f"Could not reach OpenMemory at {self.host}. Is OpenMemory running? ({exc})"
            ) from exc
        except httpx.TimeoutException as exc:
            raise OpenMemoryUnavailableError(
                f"OpenMemory at {self.host} timed out after {self.timeout}s for query '{query}'."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise OpenMemoryUnavailableError(
                f"OpenMemory returned HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
        except Exception as exc:
            raise OpenMemoryUnavailableError(
                f"Unexpected error communicating with OpenMemory: {exc}"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise OpenMemoryUnavailableError(
                f"OpenMemory returned invalid JSON: {response.text[:200]}"
            ) from exc

        raw_items = data.get("items", []) if isinstance(data, dict) else []
        candidates = []

        for item in raw_items:
            content = item.get("content", "")
            if not self.is_namespace_allowed(content):
                continue

            parsed_item = OpenMemoryItem(
                id=item.get("id", ""),
                content=content,
                app_name=item.get("app_name", "OpenMemory"),
                categories=item.get("categories", []),
                created_at=item.get("created_at", 0),
                namespace=self.extract_namespace(content),
            )

            # Score relevance based on keyword match density
            text_lower = content.lower()
            score = sum(2 for kw in keywords if kw in text_lower)
            candidates.append((score, parsed_item))

        # Sort by relevance score descending
        candidates.sort(key=lambda x: x[0], reverse=True)

        # If keyword matches exist, filter to matching candidates; otherwise take top recents
        if keywords and any(score > 0 for score, _ in candidates):
            filtered_items = [it for score, it in candidates if score > 0]
        else:
            filtered_items = [it for _, it in candidates]

        return filtered_items[:limit]

    def create_memory(
        self,
        text: str,
        categories: Optional[List[str]] = None,
        app_name: str = "DeepCore",
        metadata: Optional[dict] = None,
    ) -> OpenMemoryItem:
        """
        Push a permanent memory or decision to OpenMemory with enforced [DeepCore/...] namespace tagging.
        Enforces that all writes from DeepCore are explicitly tagged to prevent cross-agent context pollution.

        Raises OpenMemoryUnavailableError on network/timeout/server failures.
        """
        clean_text = text.strip()
        cats = categories or self.default_categories
        primary_category = (cats[0] if cats else "General").capitalize()

        # Enforce [DeepCore/Category] bracket prefix if not already present
        if not re.match(r"^\[DeepCore[ /\]]", clean_text, re.IGNORECASE):
            tagged_text = f"[DeepCore/{primary_category}] {clean_text}"
        else:
            tagged_text = clean_text

        payload = {
            "user_id": self.user_id,
            "text": tagged_text,
            "metadata": {
                "app": app_name,
                "categories": cats,
                **(metadata or {}),
            }
        }

        try:
            response = httpx.post(
                f"{self.host}/api/v1/memories/",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise OpenMemoryUnavailableError(
                f"Could not reach OpenMemory at {self.host} for memory creation: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise OpenMemoryUnavailableError(
                f"OpenMemory at {self.host} timed out after {self.timeout}s creating memory."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise OpenMemoryUnavailableError(
                f"OpenMemory returned HTTP {exc.response.status_code} on creation: {exc.response.text[:200]}"
            ) from exc
        except Exception as exc:
            raise OpenMemoryUnavailableError(
                f"Unexpected error creating memory in OpenMemory: {exc}"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise OpenMemoryUnavailableError(
                f"OpenMemory returned invalid JSON on memory creation: {response.text[:200]}"
            ) from exc

        # OpenMemory POST response can return a list or dict with created memory info
        mem_id = ""
        if isinstance(data, dict):
            mem_id = str(data.get("id") or data.get("memory_id") or "")
            if not mem_id and "results" in data and isinstance(data["results"], list) and data["results"]:
                mem_id = str(data["results"][0].get("id") or "")
        elif isinstance(data, list) and data:
            mem_id = str(data[0].get("id") or "")

        return OpenMemoryItem(
            id=mem_id or "om-created",
            content=tagged_text,
            app_name=app_name,
            categories=cats,
            namespace=self.extract_namespace(tagged_text),
        )
