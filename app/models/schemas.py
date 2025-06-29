from datetime import datetime, time
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum

class ConversationStateEnum(str, Enum):
    INITIAL = "initial"
    COLLECTING_DETAILS = "collecting_details"
    CHECKING_AVAILABILITY = "checking_availability"
    SUGGESTING_SLOTS = "suggesting_slots"
    CONFIRMING_BOOKING = "confirming_booking"
    BOOKING_COMPLETE = "booking_complete"

class IntentType(str, Enum):
    GREETING = "greeting"
    HELP = "help"
    BOOK_APPOINTMENT = "book_appointment"
    CHECK_AVAILABILITY = "check_availability"
    UNKNOWN = "unknown"

class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = datetime.now()

class TimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    duration_minutes: int

class AppointmentRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_minutes: Optional[int] = 60
    preferred_times: Optional[List[str]] = []
    attendees: Optional[List[str]] = []

class IntentResult(BaseModel):
    intent: IntentType
    confidence: float
    entities: Dict[str, Any] = {}

class ConversationState(BaseModel):
    current_state: ConversationStateEnum = ConversationStateEnum.INITIAL
    appointment_request: Optional[AppointmentRequest] = None
    available_slots: List[TimeSlot] = []
    error_message: Optional[str] = None

class CalendarEvent(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    attendees: List[str] = []

class BookingResponse(BaseModel):
    success: bool
    message: str
    event_id: Optional[str] = None

class AvailabilityResponse(BaseModel):
    available_slots: List[TimeSlot]
    requested_date: Optional[datetime] = None
    business_hours_start: Optional[time] = None
    business_hours_end: Optional[time] = None
    timezone: str = "UTC"
    total_slots: int = 0

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    state: Dict[str, Any]
    available_slots: List[Dict[str, Any]] = []
    requires_confirmation: bool = False
    error: Optional[str] = None
 