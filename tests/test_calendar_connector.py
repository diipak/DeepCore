import os
import json
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from deepcore.storage.sqlite.models import (
    KnowledgeSource as DBKnowledgeSource,
    RegistryObject as DBRegistryObject,
    Workspace as DBWorkspace
)
from deepcore.core.acquisition.base import SyncContext, Provenance
from deepcore.core.acquisition.ingestion import IngestionService
from deepcore.core.acquisition.runtime import AcquisitionRuntime
from deepcore.core.registry.service import RegistryService
from deepcore.connectors.calendar.connector import CalendarConnector
from deepcore.connectors.calendar.translator import TemporalTranslator
from deepcore.connectors.calendar.schema import TemporalEvent

def test_calendar_descriptor_metadata():
    """Verify static connector capability parameters."""
    from deepcore.connectors.calendar.descriptor import CONNECTOR_DESCRIPTOR
    assert CONNECTOR_DESCRIPTOR.id == "calendar"
    assert "sync" in CONNECTOR_DESCRIPTOR.capabilities
    assert "watch" not in CONNECTOR_DESCRIPTOR.capabilities # watch is deferred
    assert "calendar" in CONNECTOR_DESCRIPTOR.permissions
    assert "Event" in CONNECTOR_DESCRIPTOR.supported_types


def test_temporal_schema_parsing():
    """Verify standard temporal schema validation for recurrence and resources."""
    from deepcore.connectors.calendar.schema import (
        TemporalInterval, TemporalRecurrence, TemporalParticipant, TemporalLocation, TemporalEvent
    )

    interval = TemporalInterval(
        start_time="2026-07-16T10:00:00Z",
        end_time="2026-07-16T11:00:00Z",
        duration_seconds=3600,
        timezone="America/New_York"
    )

    # Canonical Recurrence Model (Amendment 3)
    recurrence = TemporalRecurrence(
        frequency="weekly",
        interval=2,
        count=10,
        exceptions=["2026-08-01T10:00:00Z"]
    )

    # Extensible Participant Model (Amendment 4)
    human = TemporalParticipant(name="John Doe", email="john@example.com", participant_type="human")
    room = TemporalParticipant(name="Main Boardroom", participant_type="room") # non-human resource

    location = TemporalLocation(title="HQ Boardroom", address="1 Infinite Loop")

    event = TemporalEvent(
        uid="event_abc_123",
        summary="Architecture Sync",
        interval=interval,
        recurrence=recurrence,
        location=location,
        participants=[human, room]
    )

    assert event.uid == "event_abc_123"
    assert event.interval.duration_seconds == 3600
    assert event.recurrence.frequency == "weekly"
    assert len(event.participants) == 2
    assert event.participants[1].participant_type == "room"


def test_calendar_health_check_states(tmp_path):
    """Verify health indicator mapping logic for mock configurations."""
    connector = CalendarConnector()
    
    # 1. Check Not Configured
    ctx_unconfigured = SyncContext(workspace_id=1, source_id=1, config={}, credentials={})
    # If EventKit is not available, state will be CRITICAL
    health_res = connector.health(ctx_unconfigured)
    assert health_res.details["Installed"] is True

    # 2. Configure path to mock JSON
    mock_file = str(tmp_path / "events.json")
    ctx_configured = SyncContext(workspace_id=1, source_id=1, config={"mock_file_path": mock_file}, credentials={})
    health_conf = connector.health(ctx_configured)
    # File does not exist yet: Reachable = False, state = DEGRADED
    assert health_conf.state == "DEGRADED"
    assert health_conf.details["Provider Reachable"] is False

    # 3. Create mock file: Reachable = True, state = HEALTHY
    with open(mock_file, "w") as f:
        json.dump([], f)
    health_ok = connector.health(ctx_configured)
    assert health_ok.state == "HEALTHY"
    assert health_ok.details["Provider Reachable"] is True


def test_temporal_translator_decoding():
    """Verify raw EventKit or file dictionary payload parses into canonical TemporalEvent."""
    translator = TemporalTranslator()
    provenance = Provenance(
        connector_id="calendar",
        provider_id="calendar",
        source_system="Local Calendar",
        external_id="evt_101",
        sync_run_id="run_0"
    )

    raw_event = {
        "uid": "evt_101",
        "summary": "Meeting",
        "description": "Weekly status update",
        "start_time": "2026-07-16 10:00:00", # Space separator format testing
        "end_time": "2026-07-16 11:30:00",
        "timezone": "Europe/London",
        "location": {
            "title": "Meeting Room 1",
            "address": "London HQ"
        },
        "organizer": {
            "name": "Host",
            "email": "host@test.com"
        },
        "attendees": [
            {
                "name": "Attendee 1",
                "status": 2, # EventKit enum accepted status
                "role": "attendee"
            }
        ],
        "recurrence": {
            "frequency": "weekly",
            "interval": 1,
            "exceptions": ["2026-07-23 10:00:00"]
        }
    }

    event = translator.translate_object(raw_event, provenance)

    assert isinstance(event, TemporalEvent)
    assert event.uid == "evt_101"
    assert event.summary == "Meeting"
    # Duration computed: 1.5 hours = 5400 seconds
    assert event.interval.duration_seconds == 5400
    assert event.interval.timezone == "Europe/London"
    assert event.recurrence.frequency == "weekly"
    assert len(event.participants) == 2
    # Attendee 1 response status mapped to 'accepted' from EventKit enum 2
    assert event.participants[1].status == "accepted"


def test_calendar_full_and_incremental_sync(db_session: Session, tmp_path):
    """Test full sync pipeline: Mock calendar JSON -> translator -> ingestion mapping -> DB."""
    # Ensure default workspace
    ws = db_session.query(DBWorkspace).filter(DBWorkspace.id == 1).first()
    if not ws:
        ws = DBWorkspace(id=1, name="Workspace 1")
        db_session.add(ws)
        db_session.commit()

    mock_file = tmp_path / "cal.json"
    events_data = [
        {
            "uid": "event_1",
            "summary": "Strategic Sync",
            "description": "Planning next quarters sync milestones",
            "start_time": "2026-07-16T12:00:00Z",
            "end_time": "2026-07-16T13:00:00Z",
            "timezone": "UTC",
            "modified_at_ts": 1700000000.0,
            "location": {"title": "Zoom"},
            "organizer": {"name": "Manager", "email": "mgr@test.com"},
            "attendees": [{"name": "Developer", "status": "accepted"}],
            "recurrence": {"frequency": "monthly", "interval": 1}
        },
        {
            "uid": "event_2",
            "summary": "Project Update",
            "description": "Ambient update calls",
            "start_time": "2026-07-17T15:00:00Z",
            "end_time": "2026-07-17T15:30:00Z",
            "timezone": "UTC",
            "modified_at_ts": 1700000000.0,
            "location": {"title": "Zoom"},
            "organizer": {"name": "Lead", "email": "lead@test.com"},
            "attendees": []
        }
    ]
    with open(mock_file, "w") as f:
        json.dump(events_data, f)

    source = DBKnowledgeSource(
        workspace_id=1,
        provider_id="calendar",
        kind="calendar",
        name="Personal Calendar",
        location=str(mock_file),
        config_json=json.dumps({"mock_file_path": str(mock_file)}),
        status="Configured"
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    connector = CalendarConnector()
    translator = TemporalTranslator()
    ingester = IngestionService(db_session)
    runtime = AcquisitionRuntime(db_session, ingester)

    # 1. Execute full sync
    sync_run = runtime.run_sync(source.id, connector, translator, full_sync=True)
    assert sync_run.status == "success"
    assert sync_run.objects_scanned == 2
    assert sync_run.objects_created == 2

    # Check that database records exist
    objs = db_session.query(DBRegistryObject).filter(DBRegistryObject.source_id == source.id).all()
    assert len(objs) == 2
    assert objs[0].object_type == "event"
    assert objs[0].title in ["Strategic Sync", "Project Update"]

    # Verify that metadata_json stores the domain structure (including recurrence and participants)
    meta = json.loads(objs[0].metadata_json)
    assert "interval" in meta
    assert "participants" in meta

    # 2. Modify one event and add time delay
    events_data[0]["summary"] = "Strategic Sync - UPDATED SUMMARY"
    events_data[0]["modified_at_ts"] = datetime.now(timezone.utc).timestamp() + 10.0
    with open(mock_file, "w") as f:
        json.dump(events_data, f)

    # Execute incremental sync
    sync_run_inc = runtime.run_sync(source.id, connector, translator, full_sync=False)
    assert sync_run_inc.objects_scanned == 1
    assert sync_run_inc.objects_updated == 1
    assert sync_run_inc.objects_created == 0

    # 3. Orphan deletion handling (delete event_2 from source file)
    events_data.pop(1)
    with open(mock_file, "w") as f:
        json.dump(events_data, f)

    # Sync to refresh cursor active_ids list
    runtime.run_sync(source.id, connector, translator, full_sync=False)
    
    db_session.refresh(source)
    cursor = json.loads(source.cursor_state or "{}")
    active_ids = cursor.get("active_ids", [])
    assert "event_2" not in active_ids

    reg_service = RegistryService(db_session, workspace_id=1)
    missing_count = reg_service.mark_missing_objects(source.name, source.location, active_ids)
    assert missing_count == 1

    deleted_obj = db_session.query(DBRegistryObject).filter(
        DBRegistryObject.source_id == source.id,
        DBRegistryObject.external_id == "event_2"
    ).first()
    assert deleted_obj.status == "missing"
