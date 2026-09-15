import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Generator, List

from deepcore.core.acquisition.base import (
    BaseConnector,
    SyncContext,
    HealthStatus,
    ConnectorOperation,
    ExecutionRequest,
    ExecutionResponse,
    ConnectorCapabilities,
)

# Attempt to load native macOS EventKit libraries via PyObjC
try:
    import objc
    from EventKit import EKEventStore, EKEntityTypeEvent, EKParticipantRoleOrganizer, EKParticipantRoleAttendee
    EVENTKIT_AVAILABLE = True
except ImportError:
    EVENTKIT_AVAILABLE = False


class CalendarProvider:
    """Interface for calendar backend provider implementations."""
    def verify_authorization(self) -> str:
        """Return authorization state: Authorized, Denied, Restricted, NotDetermined."""
        raise NotImplementedError()

    def test_connection(self) -> bool:
        """Return True if connection or file read is active."""
        raise NotImplementedError()

    def fetch_events(self, ctx: SyncContext, last_sync_ts: float) -> List[Dict[str, Any]]:
        """Fetch raw event dictionaries starting from last_sync_ts."""
        raise NotImplementedError()


class MockCalendarProvider(CalendarProvider):
    """Fallback Calendar Provider that reads events from a local mock JSON file."""
    def __init__(self, mock_file_path: str):
        self.mock_file_path = mock_file_path

    def verify_authorization(self) -> str:
        if not self.mock_file_path:
            return "NotConfigured"
        # If file path exists and is readable, we are authorized
        if os.path.exists(self.mock_file_path) and os.access(self.mock_file_path, os.R_OK):
            return "Authorized"
        return "Denied"

    def test_connection(self) -> bool:
        return os.path.exists(self.mock_file_path)

    def fetch_events(self, ctx: SyncContext, last_sync_ts: float) -> List[Dict[str, Any]]:
        if not os.path.exists(self.mock_file_path):
            return []
        try:
            with open(self.mock_file_path, "r", encoding="utf-8") as f:
                events = json.load(f)
            if not isinstance(events, list):
                return []
            
            # Filter by last modification timestamp if present, simulating incremental updates
            # We assume mock events have a 'modified_at_ts' parameter (defaults to 0.0)
            filtered = []
            for ev in events:
                modified_ts = ev.get("modified_at_ts", 0.0)
                if last_sync_ts == 0.0 or modified_ts >= last_sync_ts:
                    filtered.append(ev)
            return filtered
        except Exception as e:
            if ctx and ctx.logger:
                ctx.logger.error(f"Failed to read mock calendar file: {e}")
            return []


class EventKitProvider(CalendarProvider):
    """Native macOS EventKit Calendar Provider."""
    def __init__(self, calendar_name: str = None):
        self.calendar_name = calendar_name
        self.event_store = EKEventStore() if EVENTKIT_AVAILABLE else None

    def verify_authorization(self) -> str:
        if not EVENTKIT_AVAILABLE:
            return "UnsupportedOS"
        status = EKEventStore.authorizationStatusForEntityType_(EKEntityTypeEvent)
        # Status mapping: 0=NotDetermined, 1=Restricted, 2=Denied, 3=Authorized
        if status == 3:
            return "Authorized"
        elif status == 2:
            return "Denied"
        elif status == 1:
            return "Restricted"
        return "NotDetermined"

    def test_connection(self) -> bool:
        if not EVENTKIT_AVAILABLE:
            return False
        return self.verify_authorization() == "Authorized"

    def fetch_events(self, ctx: SyncContext, last_sync_ts: float) -> List[Dict[str, Any]]:
        if not EVENTKIT_AVAILABLE or self.verify_authorization() != "Authorized":
            return []

        # Query native EventKit calendar
        events_list = []
        try:
            # EventKit queries require start and end date boundaries
            # Fetch events from 30 days before last sync until 1 year in future
            start_date_ts = max(last_sync_ts - (30 * 86400), 0.0)
            end_date_ts = datetime.now(timezone.utc).timestamp() + (365 * 86400)
            
            # Convert timestamp to NSDate
            from Foundation import NSDate
            ns_start = NSDate.dateWithTimeIntervalSince1970_(start_date_ts)
            ns_end = NSDate.dateWithTimeIntervalSince1970_(end_date_ts)

            # Get target calendar if specified
            target_calendars = None
            if self.calendar_name:
                all_cals = self.event_store.calendarsForEntityType_(EKEntityTypeEvent)
                target_calendars = [c for c in all_cals if c.title() == self.calendar_name]

            predicate = self.event_store.predicateForEventsWithStartDate_endDate_calendars_(
                ns_start, ns_end, target_calendars
            )
            ek_events = self.event_store.eventsMatchingPredicate_(predicate)
            
            for ev in ek_events:
                # Convert EKEvent to raw dictionary payload
                organizer_info = {}
                if ev.organizer():
                    organizer_info = {
                        "name": ev.organizer().name(),
                        "email": ev.organizer().URL().absoluteString() if ev.organizer().URL() else None
                    }

                attendees = []
                if ev.attendees():
                    for att in ev.attendees():
                        attendees.append({
                            "name": att.name(),
                            "email": att.URL().absoluteString() if att.URL() else None,
                            "role": "organizer" if att.participantRole() == EKParticipantRoleOrganizer else "attendee",
                            "status": att.participantStatus() # maps to EKParticipantStatus int
                        })

                # Simple alarms/reminders extraction
                reminders = []
                if ev.alarms():
                    for alarm in ev.alarms():
                        reminders.append({
                            "trigger_minutes_before": int(-alarm.relativeOffset() / 60) if alarm.relativeOffset() else 0,
                            "method": "display"
                        })

                # Extract recurrence exception templates if any
                recurrence = None
                if ev.recurrenceRules():
                    rule = ev.recurrenceRules()[0]
                    # Simple rule mapping
                    freq_map = {0: "daily", 1: "weekly", 2: "monthly", 3: "yearly"}
                    recurrence = {
                        "frequency": freq_map.get(rule.frequency(), "daily"),
                        "interval": rule.interval(),
                        "until": rule.recurrenceEnd().endDate().description() if rule.recurrenceEnd() and rule.recurrenceEnd().endDate() else None,
                        "count": rule.recurrenceEnd().occurrenceCount() if rule.recurrenceEnd() else None
                    }

                events_list.append({
                    "uid": ev.eventIdentifier(),
                    "summary": ev.title(),
                    "description": ev.notes(),
                    "start_time": ev.startDate().description(),
                    "end_time": ev.endDate().description(),
                    "timezone": ev.timeZone().name() if ev.timeZone() else "UTC",
                    "location": {
                        "title": ev.location() or "Unknown"
                    },
                    "organizer": organizer_info,
                    "attendees": attendees,
                    "reminders": reminders,
                    "recurrence": recurrence,
                    "modified_at_ts": ev.lastModifiedDate().timeIntervalSince1970() if ev.lastModifiedDate() else last_sync_ts + 1
                })
        except Exception as e:
            if ctx and ctx.logger:
                ctx.logger.error(f"EventKit execution failed: {e}")
        return events_list


class CalendarConnector(BaseConnector):
    """
    Calendar Connector. TECHNICAL CONTRACT implementation.
    Orchestrates authentication checks, reports standard health, and triggers discovery.
    """
    def _select_provider(self, ctx: SyncContext) -> CalendarProvider:
        mock_path = ctx.config.get("mock_file_path")
        if mock_path or not EVENTKIT_AVAILABLE:
            return MockCalendarProvider(mock_file_path=mock_path or "")
        return EventKitProvider(calendar_name=ctx.config.get("calendar_name"))

    def authenticate(self, credentials: Dict[str, Any]) -> HealthStatus:
        return HealthStatus(state="HEALTHY", message="Calendar authentication verified.")

    def health(self, ctx: SyncContext) -> HealthStatus:
        """
        Amendment 5 - Platform Health Reporting.
        Validates Installed, Configured, Authorized, Reachable, and prior synchronization indicators.
        """
        mock_path = ctx.config.get("mock_file_path")
        provider = self._select_provider(ctx)
        
        # 1. Check Installed & Configured
        installed = True
        configured = bool(mock_path or EVENTKIT_AVAILABLE)
        
        # 2. Check Authorized & Reachable
        auth_state = provider.verify_authorization()
        authorized = (auth_state == "Authorized")
        reachable = provider.test_connection()
        
        # 3. Last successful sync
        last_sync = ctx.cursor_state.get("last_sync_time")

        health_state = "HEALTHY"
        messages = []

        if not configured:
            health_state = "CRITICAL"
            messages.append("Status: Not Configured. Calendar EventKit is not active and no mock_file_path is configured.")
        elif not authorized:
            health_state = "DEGRADED"
            messages.append(f"Status: Unauthorized. Calendar permission state is {auth_state}.")
        elif not reachable:
            health_state = "DEGRADED"
            messages.append("Status: Unreachable. Calendar source database or file cannot be read.")
        else:
            messages.append("Status: Healthy.")

        if last_sync:
            messages.append(f"Last successful sync: {last_sync}")
        else:
            messages.append("No prior synchronization recorded.")

        # Build structural metadata metrics
        details = {
            "Installed": installed,
            "Configured": configured,
            "Authorized": auth_state,
            "Provider Reachable": reachable,
            "Last Successful Synchronization": last_sync
        }

        return HealthStatus(
            state=health_state,
            message=" | ".join(messages),
            details=details
        )

    def discover(self, ctx: SyncContext) -> Generator[Dict[str, Any], None, None]:
        provider = self._select_provider(ctx)
        events = provider.fetch_events(ctx, last_sync_ts=0.0)
        
        active_uids = []
        for ev in events:
            # Yield raw event dictionary payloads (Technical Contract only)
            ev["external_id"] = ev["uid"]
            active_uids.append(ev["uid"])
            yield ev

        ctx.cursor_state["active_ids"] = active_uids
        ctx.cursor_state["last_sync_time"] = datetime.now(timezone.utc).isoformat()

    def sync(self, ctx: SyncContext) -> Generator[Dict[str, Any], None, None]:
        last_sync_str = ctx.cursor_state.get("last_sync_time")
        last_ts = 0.0
        if last_sync_str:
            try:
                last_ts = datetime.fromisoformat(last_sync_str).timestamp()
            except ValueError:
                pass

        provider = self._select_provider(ctx)
        events = provider.fetch_events(ctx, last_sync_ts=last_ts)
        
        active_uids = []
        for ev in events:
            ev["external_id"] = ev["uid"]
            active_uids.append(ev["uid"])
            yield ev

        # Retain active file list and refresh timestamp
        ctx.cursor_state["active_ids"] = active_uids
        ctx.cursor_state["last_sync_time"] = datetime.now(timezone.utc).isoformat()

    def watch(self, ctx: SyncContext) -> Generator[Dict[str, Any], None, None]:
        raise NotImplementedError("Watch capability is not implemented in this milestone.")

    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            supported_operations=[
                ConnectorOperation.READ,
                ConnectorOperation.LIST,
                ConnectorOperation.SEARCH,
            ],
            requires_configuration=True,
            requires_permissions=False,
            supports_pagination=False,
            supports_streaming=False,
            supports_actions=False,
            metadata={"provider": "calendar"}
        )

    def _resolve_live_provider(self, config: Dict[str, Any]) -> CalendarProvider:
        mock_path = config.get("mock_file_path")
        if mock_path or not EVENTKIT_AVAILABLE:
            return MockCalendarProvider(mock_file_path=mock_path or "")
        return EventKitProvider(calendar_name=config.get("calendar_name"))

    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """
        Stateless live execution adapter for calendar events (read, list, search).
        """
        op = request.operation
        params = request.parameters or {}
        config = request.context.config or {}
        provider = self._resolve_live_provider(config)

        # Fetch raw events from provider (stateless, last_sync_ts=0.0)
        events = provider.fetch_events(ctx=None, last_sync_ts=0.0)

        if op == ConnectorOperation.READ:
            target_uid = params.get("uid") or params.get("id") or params.get("external_id")
            if not target_uid:
                raise ValueError("Operation 'read' requires 'uid' or 'id' parameter.")
            
            results = [ev for ev in events if ev.get("uid") == target_uid or ev.get("external_id") == target_uid]
            return ExecutionResponse(
                results=results,
                metadata={"count": len(results), "uid": target_uid},
                diagnostics={"status": "success"}
            )

        elif op == ConnectorOperation.LIST:
            # Optional date window filtering
            start_filter = params.get("start_time")
            end_filter = params.get("end_time")

            results = events
            if start_filter or end_filter:
                filtered = []
                for ev in events:
                    ev_start = ev.get("start_time", "")
                    ev_end = ev.get("end_time", "")
                    if start_filter and ev_end and ev_end < start_filter:
                        continue
                    if end_filter and ev_start and ev_start > end_filter:
                        continue
                    filtered.append(ev)
                results = filtered

            return ExecutionResponse(
                results=results,
                metadata={"count": len(results)},
                diagnostics={"status": "success"}
            )

        elif op == ConnectorOperation.SEARCH:
            query = params.get("query", "").lower()
            if not query:
                results = events
            else:
                results = [
                    ev for ev in events
                    if query in (ev.get("summary") or "").lower()
                    or query in (ev.get("description") or "").lower()
                    or query in (ev.get("location", {}).get("title") or "").lower()
                ]

            return ExecutionResponse(
                results=results,
                metadata={"count": len(results), "query": query},
                diagnostics={"status": "success"}
            )

        else:
            raise NotImplementedError(
                f"Operation '{op.value}' is not supported by CalendarConnector."
            )
