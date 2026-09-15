from datetime import datetime
from typing import Dict, Any

from deepcore.core.acquisition.base import BaseTranslator, Provenance
from deepcore.connectors.calendar.schema import (
    TemporalEvent,
    TemporalInterval,
    TemporalRecurrence,
    TemporalParticipant,
    TemporalLocation,
    TemporalReminder
)

class TemporalTranslator(BaseTranslator):
    """
    Temporal Domain Translator. Converts raw calendar payloads into canonical
    TemporalEvent models that are completely independent of registry database schemas.
    """
    def translate_object(self, raw_data: Dict[str, Any], provenance: Provenance) -> TemporalEvent:
        # 1. Parse Time Interval and compute duration
        start_str = raw_data["start_time"]
        end_str = raw_data["end_time"]
        
        duration = 0
        try:
            # EventKit strings might contain offsets or spaces, we try basic ISO parsing
            # Standardize space separators to T if present
            s_clean = start_str.replace(" ", "T")
            e_clean = end_str.replace(" ", "T")
            # Strip trailing timezone info if it fails raw isoformat parsing
            if "+" in s_clean:
                s_clean = s_clean.split("+")[0]
            if "+" in e_clean:
                e_clean = e_clean.split("+")[0]

            dt_start = datetime.fromisoformat(s_clean)
            dt_end = datetime.fromisoformat(e_clean)
            duration = int((dt_end - dt_start).total_seconds())
        except Exception:
            pass

        interval = TemporalInterval(
            start_time=start_str,
            end_time=end_str,
            duration_seconds=duration,
            timezone=raw_data.get("timezone", "UTC")
        )

        # 2. Parse Canonical Recurrence Model (Amendment 3)
        raw_rec = raw_data.get("recurrence")
        recurrence = None
        if raw_rec:
            recurrence = TemporalRecurrence(
                frequency=raw_rec.get("frequency", "daily"),
                interval=raw_rec.get("interval", 1),
                until=raw_rec.get("until"),
                count=raw_rec.get("count"),
                exceptions=raw_rec.get("exceptions") or []
            )

        # 3. Parse Extensible Participant Model (Amendment 4)
        participants = []
        raw_org = raw_data.get("organizer")
        if raw_org and raw_org.get("name"):
            participants.append(TemporalParticipant(
                name=raw_org["name"],
                email=raw_org.get("email"),
                role="organizer",
                status="accepted",
                participant_type=raw_org.get("participant_type", "human")
            ))

        raw_atts = raw_data.get("attendees") or []
        for att in raw_atts:
            if att.get("name"):
                # Normalize EventKit status integers if present
                status_val = att.get("status", "none")
                if isinstance(status_val, int):
                    # EventKit EKParticipantStatus enum: 1=pending/tentative, 2=accepted, 3=declined
                    status_map = {1: "tentative", 2: "accepted", 3: "declined"}
                    status_val = status_map.get(status_val, "none")
                
                participants.append(TemporalParticipant(
                    name=att["name"],
                    email=att.get("email"),
                    role=att.get("role", "attendee"),
                    status=status_val,
                    participant_type=att.get("participant_type", "human")
                ))

        # 4. Parse Location
        raw_loc = raw_data.get("location")
        location = None
        if raw_loc and raw_loc.get("title"):
            location = TemporalLocation(
                title=raw_loc["title"],
                address=raw_loc.get("address"),
                latitude=raw_loc.get("latitude"),
                longitude=raw_loc.get("longitude")
            )

        # 5. Parse Reminders
        reminders = []
        raw_rems = raw_data.get("reminders") or []
        for rem in raw_rems:
            reminders.append(TemporalReminder(
                trigger_minutes_before=rem.get("trigger_minutes_before", 15),
                method=rem.get("method", "display")
            ))

        # Return canonical domain model instance
        return TemporalEvent(
            uid=raw_data["uid"],
            summary=raw_data["summary"],
            description=raw_data.get("description"),
            interval=interval,
            location=location,
            participants=participants,
            reminders=reminders,
            recurrence=recurrence
        )
