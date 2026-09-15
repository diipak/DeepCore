from deepcore2.runtime.descriptors import ProviderDescriptor, DescriptorCategory

CONNECTOR_DESCRIPTOR = ProviderDescriptor(
    id="spotlight",
    name="Apple Spotlight",
    description="Ambiently discover files and folder updates using macOS metadata index.",
    category=DescriptorCategory.PROVIDER,
    provider_type="spotlight",
    supported_formats=[".md", ".markdown", ".pdf", ".txt"],
    capabilities=["sync"],
    permissions=["filesystem", "spotlight"],
    supported_types=["DiscoveredArtifact"],
    enabled=True,
    configurable=True,
    icon="Search",
    accent_color="accent-assistant",
    availability_state="coming_soon",
    config_schema={
        "type": "object",
        "properties": {
            "search_path": {
                "type": "string",
                "description": "Absolute directory path defining the search scope (Workspace Scope)"
            },
            "file_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of matching file extensions (e.g. ['.md', '.txt'])"
            },
            "modified_within_hours": {
                "type": "integer",
                "description": "Filter files modified in the last N hours (Recently Modified)"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter files by macOS OS-level tags"
            }
        }
    }
)
