from deepcore2.runtime.descriptors import ProviderDescriptor, DescriptorCategory

CONNECTOR_DESCRIPTOR = ProviderDescriptor(
    id="filesystem",
    name="Local Filesystem",
    description="Sync local Obsidian vaults, Markdown folders, and text logs privately.",
    category=DescriptorCategory.PROVIDER,
    provider_type="markdown",
    supported_formats=[".md", ".markdown"],
    capabilities=["sync"],
    permissions=["filesystem"],
    supported_types=["File", "Folder"],
    enabled=True,
    configurable=True,
    icon="Folder",
    accent_color="accent-memory",
    availability_state="available",
    config_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute path to the local directory to sync"
            }
        },
        "required": ["path"]
    }
)
