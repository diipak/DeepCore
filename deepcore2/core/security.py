"""
Security utilities for DeepCore.

Provides sanitization, API key and token redaction, and boundary enforcement
to prevent credentials from leaking into LLM context, logs, daily journal notes,
or OpenMemory stores.
"""
import re
from typing import Optional
from deepcore2.config import settings


# Pre-compiled regex patterns for secret detection
SECRET_PATTERNS = [
    # Generic API Key / Token / Secret assignments
    re.compile(r'(?i)(api[_-]?key|access[_-]?token|auth[_-]?token|secret|authorization)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{8,})["\']?'),
    # Bearer tokens
    re.compile(r'(?i)Bearer\s+([a-zA-Z0-9_\-\.]{15,})'),
    # Brave Search API Key format (BSA...)
    re.compile(r'\b(BSA[a-zA-Z0-9_\-]{20,})\b'),
    # OpenAI / Anthropic / Generic sk- keys
    re.compile(r'\b(sk-[a-zA-Z0-9_\-]{20,})\b'),
]


def redact_secrets(text: Optional[str]) -> str:
    """
    Sanitize text by masking API keys, bearer tokens, and secrets.
    Also explicitly checks and redacts the configured BRAVE_API_KEY if present.
    """
    if not text:
        return ""

    sanitized = text

    # 1. Explicitly mask the configured Brave API key if loaded
    configured_key = getattr(settings, "BRAVE_API_KEY", "").strip()
    if configured_key and len(configured_key) > 5 and configured_key in sanitized:
        sanitized = sanitized.replace(configured_key, "[REDACTED_BRAVE_KEY]")

    # 2. Mask generic key/token patterns
    for pattern in SECRET_PATTERNS:
        def _mask_match(match):
            full_match = match.group(0)
            if len(match.groups()) == 2:
                label, secret = match.group(1), match.group(2)
                return f"{label}: [REDACTED_SECRET]"
            elif len(match.groups()) == 1:
                secret = match.group(1)
                return full_match.replace(secret, "[REDACTED_SECRET]")
            return "[REDACTED_SECRET]"

        sanitized = pattern.sub(_mask_match, sanitized)

    return sanitized
