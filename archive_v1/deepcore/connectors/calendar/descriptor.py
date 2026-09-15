from deepcore.runtime.descriptors import ProviderDescriptor, DescriptorCategory

CONNECTOR_DESCRIPTOR = ProviderDescriptor(
    id="calendar",
    name="Calendar Event",
    description="Synchronize offline calendars, meetings, and participant timelines.",
    category=DescriptorCategory.PROVIDER,
    provider_type="calendar",
    supported_formats=[".json"],
    capabilities=["sync"],
    permissions=["calendar"],
    supported_types=["Event", "Participant", "Location", "Reminder", "Recurrence"],
    enabled=True,
    configurable=True,
    icon="Calendar",
    accent_color="accent-concept",
    availability_state="coming_soon",
    config_schema={
        "type": "object",
        "properties": {
            "calendar_name": {
                "type": "string",
                "description": "Name of the specific calendar to sync (all if empty)"
            },
            "mock_file_path": {
                "type": "string",
                "description": "Path to a local JSON file containing events for testing/mock fallback"
            }
        }
    }
)
