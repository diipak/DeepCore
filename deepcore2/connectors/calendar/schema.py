from pydantic import BaseModel, Field
from typing import List, Optional

class TemporalInterval(BaseModel):
    start_time: str = Field(..., description="UTC ISO-8601 start timestamp")
    end_time: str = Field(..., description="UTC ISO-8601 end timestamp")
    duration_seconds: int = Field(0, description="Duration in seconds")
    timezone: str = Field("UTC", description="Event time zone name")


class TemporalRecurrence(BaseModel):
    """
    Canonical Recurrence Model. Replaces provider-specific RRULE strings
    with a structured representation of frequency and exception sets.
    """
    frequency: str = Field(..., description="Recurrence frequency: daily, weekly, monthly, yearly")
    interval: int = Field(1, description="Interval multiplier")
    until: Optional[str] = Field(None, description="ISO-8601 boundary cutoff time")
    count: Optional[int] = Field(None, description="Max iterations limit")
    exceptions: List[str] = Field(default_factory=list, description="ISO-8601 exception dates")


class TemporalParticipant(BaseModel):
    """
    Future-Proof Participant Model. Supports human attendees, rooms,
    equipment, or system-level service accounts.
    """
    name: str = Field(..., description="Display name of the participant")
    email: Optional[str] = Field(None, description="Optional contact email")
    role: str = Field("attendee", description="Role: organizer, attendee")
    status: str = Field("none", description="Response status: accepted, declined, tentative, none")
    participant_type: str = Field("human", description="Type: human, room, equipment, service_account")


class TemporalLocation(BaseModel):
    title: str = Field(..., description="Location room or location name")
    address: Optional[str] = Field(None, description="Physical address string")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")


class TemporalReminder(BaseModel):
    trigger_minutes_before: int = Field(..., description="Minutes before start time")
    method: str = Field("display", description="Alarm action: display, sound, email")


class TemporalEvent(BaseModel):
    """
    Canonical Temporal Domain Object representing an event.
    Produced by TemporalTranslator. Completely database-independent.
    """
    uid: str = Field(..., description="Canonical unique identifier for the event")
    summary: str = Field(..., description="Subject or brief summary of the event")
    description: Optional[str] = Field(None, description="Event body details")
    interval: TemporalInterval = Field(..., description="Time interval boundary")
    location: Optional[TemporalLocation] = Field(None, description="Spatial coordinates and address")
    participants: List[TemporalParticipant] = Field(default_factory=list, description="Attendees and resources")
    reminders: List[TemporalReminder] = Field(default_factory=list, description="Associated alarms")
    recurrence: Optional[TemporalRecurrence] = Field(None, description="Structured recurrence configurations")
