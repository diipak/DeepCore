from pydantic import BaseModel, Field
from typing import List

class DiscoveredArtifact(BaseModel):
    """
    Canonical Discovery Domain Object representing a discovered resource.
    Completely decoupled from registry database schemas and search backend details.
    """
    uid: str = Field(..., description="Canonical unique identifier (typically SHA256 of absolute path)")
    title: str = Field(..., description="Display name of the discovered file/folder")
    location: str = Field(..., description="Absolute path on disk")
    mime_type: str = Field(..., description="MIME type string (e.g. text/markdown, application/pdf)")
    modified_time: str = Field(..., description="UTC ISO-8601 modification timestamp")
    tags: List[str] = Field(default_factory=list, description="OS-level metadata tag strings")
    size_bytes: int = Field(0, description="Size of file in bytes")
