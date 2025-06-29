from datetime import datetime, timedelta, time, date
from typing import List, Optional, Dict, Any
import random
from app.models.schemas import TimeSlot, CalendarEvent, BookingResponse, AvailabilityResponse
from app.utils.date_parser import date_parser


class MockCalendar:
    """Mock calendar implementation for testing and development"""
    
    def __init__(self):
        self.events: Dict[str, CalendarEvent] = {}
        self.business_hours_start = time(9, 0)  # 9 AM
        self.business_hours_end = time(18, 0)   # 6 PM
        self.timezone = "UTC"
        
        # Generate some mock events for testing
        self._generate_mock_events()
    
    def _generate_mock_events(self):
        """Generate some mock events for testing"""
        today = datetime.now().date()
        
        # Add some existing events for the next few days
        mock_events = [
            {
                "title": "Team Meeting",
                "start_time": datetime.combine(today + timedelta(days=1), time(10, 0)),
                "end_time": datetime.combine(today + timedelta(days=1), time(11, 0)),
                "description": "Weekly team sync"
            },
            {
                "title": "Client Call",
                "start_time": datetime.combine(today + timedelta(days=1), time(14, 0)),
                "end_time": datetime.combine(today + timedelta(days=1), time(15, 0)),
                "description": "Project discussion"
            },
            {
                "title": "Lunch Break",
                "start_time": datetime.combine(today + timedelta(days=2), time(12, 0)),
                "end_time": datetime.combine(today + timedelta(days=2), time(13, 0)),
                "description": "Lunch with colleagues"
            },
            {
                "title": "Product Review",
                "start_time": datetime.combine(today + timedelta(days=3), time(9, 0)),
                "end_time": datetime.combine(today + timedelta(days=3), time(10, 30)),
                "description": "Monthly product review meeting"
            }
        ]
        
        for i, event_data in enumerate(mock_events):
            event = CalendarEvent(
                id=f"mock_event_{i}",
                title=event_data["title"],
                description=event_data["description"],
                start_time=event_data["start_time"],
                end_time=event_data["end_time"]
            )
            if event.id:  # Ensure ID is not None
                self.events[event.id] = event
    
    def get_availability(self, start_date: datetime, end_date: datetime, duration_minutes: int = 60) -> AvailabilityResponse:
        """Get available time slots between start_date and end_date"""
        available_slots = []
        
        # Generate business hours slots for each day in the range
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            # Skip weekends
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
            
            # Generate slots for this day
            day_slots = self._generate_day_slots(current_date, duration_minutes)
            
            # Filter out slots that conflict with existing events
            available_day_slots = self._filter_conflicting_slots(day_slots)
            available_slots.extend(available_day_slots)
            
            current_date += timedelta(days=1)
        
        return AvailabilityResponse(
            available_slots=available_slots,
            requested_date=start_date,
            business_hours_start=self.business_hours_start,
            business_hours_end=self.business_hours_end,
            timezone=self.timezone
        )
    
    def _generate_day_slots(self, date_obj: date, duration_minutes: int) -> List[TimeSlot]:
        """Generate all possible slots for a given day"""
        slots = []
        start_datetime = datetime.combine(date_obj, self.business_hours_start)
        end_datetime = datetime.combine(date_obj, self.business_hours_end)
        
        current_time = start_datetime
        while current_time + timedelta(minutes=duration_minutes) <= end_datetime:
            slot_end = current_time + timedelta(minutes=duration_minutes)
            slot = TimeSlot(
                start_time=current_time,
                end_time=slot_end,
                duration_minutes=duration_minutes
            )
            slots.append(slot)
            current_time += timedelta(minutes=30)  # 30-minute intervals
        
        return slots
    
    def _filter_conflicting_slots(self, slots: List[TimeSlot]) -> List[TimeSlot]:
        """Filter out slots that conflict with existing events"""
        available_slots = []
        
        for slot in slots:
            is_available = True
            
            for event in self.events.values():
                # Check if slot overlaps with event
                if (slot.start_time < event.end_time and 
                    slot.end_time > event.start_time):
                    is_available = False
                    break
            
            if is_available:
                available_slots.append(slot)
        
        return available_slots
    
    def book_appointment(self, title: str, start_time: datetime, end_time: datetime, 
                        description: Optional[str] = None, attendees: Optional[List[str]] = None) -> BookingResponse:
        """Book an appointment"""
        try:
            # Validate the time slot
            if start_time >= end_time:
                return BookingResponse(
                    success=False,
                    message="Start time must be before end time",
                    error_code="INVALID_TIME_RANGE"
                )
            
            # Check if slot is available
            availability = self.get_availability(start_time, end_time, 
                                               int((end_time - start_time).total_seconds() / 60))
            
            if not availability.available_slots:
                return BookingResponse(
                    success=False,
                    message="The requested time slot is not available",
                    error_code="SLOT_NOT_AVAILABLE"
                )
            
            # Create the event
            event_id = f"event_{len(self.events)}_{int(datetime.now().timestamp())}"
            event = CalendarEvent(
                id=event_id,
                title=title,
                description=description or "Appointment booked via AI assistant",
                start_time=start_time,
                end_time=end_time,
                attendees=attendees or []
            )
            
            # Add to events
            self.events[event_id] = event
            
            return BookingResponse(
                success=True,
                message=f"Appointment '{title}' booked successfully for {date_parser.format_datetime(start_time)}",
                event_id=event_id,
                event_details=event
            )
            
        except Exception as e:
            return BookingResponse(
                success=False,
                message=f"Failed to book appointment: {str(e)}",
                error_code="BOOKING_ERROR"
            )
    
    def get_events(self, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """Get events between start_date and end_date"""
        events = []
        
        for event in self.events.values():
            if (event.start_time >= start_date and 
                event.start_time <= end_date):
                events.append(event)
        
        return events
    
    def delete_event(self, event_id: str) -> bool:
        """Delete an event"""
        if event_id in self.events:
            del self.events[event_id]
            return True
        return False
    
    def update_event(self, event_id: str, **kwargs) -> Optional[CalendarEvent]:
        """Update an event"""
        if event_id in self.events:
            event = self.events[event_id]
            for key, value in kwargs.items():
                if hasattr(event, key):
                    setattr(event, key, value)
            return event
        return None
    
    def get_next_available_slot(self, duration_minutes: int = 60, 
                               preferred_date: Optional[datetime] = None) -> Optional[TimeSlot]:
        """Get the next available slot"""
        if preferred_date:
            start_date = preferred_date
        else:
            start_date = datetime.now()
        
        # Look for availability in the next 7 days
        end_date = start_date + timedelta(days=7)
        
        availability = self.get_availability(start_date, end_date, duration_minutes)
        
        if availability.available_slots:
            # Return the first available slot
            return availability.available_slots[0]
        
        return None
    
    def suggest_alternative_times(self, requested_date: datetime, 
                                duration_minutes: int = 60) -> List[TimeSlot]:
        """Suggest alternative times when requested time is not available"""
        # Look for availability in the next 5 days
        start_date = requested_date
        end_date = start_date + timedelta(days=5)
        
        availability = self.get_availability(start_date, end_date, duration_minutes)
        
        # Return up to 5 suggestions
        return availability.available_slots[:5]


# Global instance
mock_calendar = MockCalendar() 