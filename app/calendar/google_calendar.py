from dotenv import load_dotenv

load_dotenv()

import os
import json
from datetime import datetime, timedelta, time
from typing import List, Optional, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.models.schemas import TimeSlot, CalendarEvent, BookingResponse, AvailabilityResponse


class GoogleCalendar:
    """Google Calendar integration with proper authentication"""

    SCOPES = ['https://www.googleapis.com/auth/calendar']

    def __init__(self, calendar_id: str = 'primary', credentials_path: Optional[str] = None):
        self.calendar_id = calendar_id
        self.business_hours_start = time(9, 0)  # 9 AM
        self.business_hours_end = time(18, 0)  # 6 PM
        self.timezone = "UTC"
        self.service = None
        self.credentials_path = credentials_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        self._initialize_service()

    def _initialize_service(self):
        """Initialize the Google Calendar service with proper authentication"""
        creds = None

        # Check if we have valid credentials in token.json
        if os.path.exists('token.json'):
            try:
                creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
                print("✅ Loaded existing credentials from token.json")
            except Exception as e:
                print(f"⚠️  Failed to load token.json: {e}")
                creds = None

        # If credentials are invalid or expired, refresh or re-authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    print("🔄 Refreshing expired credentials...")
                    creds.refresh(Request())
                    print("✅ Credentials refreshed successfully")
                except Exception as e:
                    print(f"❌ Failed to refresh credentials: {e}")
                    creds = None

            # If still no valid credentials, start OAuth flow
            if not creds and self.credentials_path and os.path.exists(self.credentials_path):
                try:
                    print("🔐 Starting OAuth2 authentication flow...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES)
                    creds = flow.run_local_server(port=8080)
                    print("✅ OAuth2 authentication successful")
                except Exception as e:
                    print(f"❌ OAuth2 authentication failed: {e}")
                    creds = None

        # Save credentials for future use
        if creds and creds.valid:
            try:
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
                print("💾 Credentials saved to token.json")
            except Exception as e:
                print(f"⚠️  Failed to save credentials: {e}")

        # Build the service
        if creds and creds.valid:
            try:
                self.service = build('calendar', 'v3', credentials=creds)
                print("✅ Google Calendar service initialized successfully")
            except Exception as e:
                print(f"❌ Failed to build calendar service: {e}")
                self.service = None
        else:
            print("❌ No valid credentials available. Google Calendar service not initialized.")
            self.service = None

    def is_time_available(self, start_time: datetime, end_time: datetime) -> bool:
        """Check if a specific time slot is available"""
        if not self.service:
            print("⚠️  Google Calendar service not available, assuming time is available")
            return True

        try:
            # Get events in the time range
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_time.isoformat() + 'Z',
                timeMax=end_time.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            # Check for conflicts
            for event in events:
                event_start_str = event['start'].get('dateTime', event['start'].get('date'))
                event_end_str = event['end'].get('dateTime', event['end'].get('date'))

                # Parse event times
                if 'T' in event_start_str:  # DateTime format
                    event_start = datetime.fromisoformat(event_start_str.replace('Z', '+00:00'))
                    event_end = datetime.fromisoformat(event_end_str.replace('Z', '+00:00'))
                else:  # Date format (all-day event)
                    continue  # Skip all-day events

                # Check for overlap
                if start_time < event_end and end_time > event_start:
                    return False

            return True

        except HttpError as error:
            print(f'❌ Error checking availability: {error}')
            return True  # Assume available if we can't check

    def get_availability(self, start_date: datetime, end_date: datetime,
                         duration_minutes: int = 60) -> AvailabilityResponse:
        """Get available time slots between start_date and end_date"""
        if not self.service:
            print("⚠️  Google Calendar service not available, returning empty availability")
            return AvailabilityResponse(
                available_slots=[],
                requested_date=start_date,
                business_hours_start=self.business_hours_start,
                business_hours_end=self.business_hours_end,
                timezone=self.timezone
            )

        try:
            # Generate all possible slots
            all_slots = self._generate_all_slots(start_date, end_date, duration_minutes)

            # Get existing events
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_date.isoformat() + 'Z',
                timeMax=end_date.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            # Filter out conflicting slots
            available_slots = self._filter_conflicting_slots(all_slots, events)

            print(f"📅 Generated {len(all_slots)} total slots, {len(available_slots)} available")

            return AvailabilityResponse(
                available_slots=available_slots,
                requested_date=start_date,
                business_hours_start=self.business_hours_start,
                business_hours_end=self.business_hours_end,
                timezone=self.timezone
            )

        except HttpError as error:
            print(f'❌ Error getting availability: {error}')
            return AvailabilityResponse(
                available_slots=[],
                requested_date=start_date,
                business_hours_start=self.business_hours_start,
                business_hours_end=self.business_hours_end,
                timezone=self.timezone
            )

    def _generate_all_slots(self, start_date: datetime, end_date: datetime, duration_minutes: int) -> List[TimeSlot]:
        """Generate all possible time slots in the date range"""
        slots = []
        current_date = start_date.date()
        end_date_only = end_date.date()

        while current_date <= end_date_only:
            # Skip weekends
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue

            # Generate slots for this day
            day_slots = self._generate_day_slots(current_date, duration_minutes)
            slots.extend(day_slots)
            current_date += timedelta(days=1)

        return slots

    def _generate_day_slots(self, date_obj, duration_minutes: int) -> List[TimeSlot]:
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

    def _filter_conflicting_slots(self, slots: List[TimeSlot], events: List[Dict]) -> List[TimeSlot]:
        """Filter out slots that conflict with existing events"""
        available_slots = []

        for slot in slots:
            is_available = True

            for event in events:
                event_start_str = event['start'].get('dateTime', event['start'].get('date'))
                event_end_str = event['end'].get('dateTime', event['end'].get('date'))

                # Skip all-day events
                if 'T' not in event_start_str:
                    continue

                # Parse event times
                try:
                    event_start = datetime.fromisoformat(event_start_str.replace('Z', '+00:00'))
                    event_end = datetime.fromisoformat(event_end_str.replace('Z', '+00:00'))

                    # Check if slot overlaps with event
                    if slot.start_time < event_end and slot.end_time > event_start:
                        is_available = False
                        break
                except:
                    continue

            if is_available:
                available_slots.append(slot)

        return available_slots

    def book_appointment(self, title: str, start_time: datetime, end_time: datetime,
                         description: Optional[str] = None, attendees: Optional[List[str]] = None) -> BookingResponse:
        """Book an appointment"""
        if not self.service:
            return BookingResponse(
                success=False,
                message="Google Calendar service not available",
                error_code="SERVICE_UNAVAILABLE"
            )

        try:
            # Create event
            event = {
                'summary': title,
                'description': description or 'Appointment booked via AI assistant',
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': self.timezone,
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': self.timezone,
                },
            }

            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]

            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()

            print(f"✅ Event created: {created_event.get('htmlLink')}")

            return BookingResponse(
                success=True,
                message=f"Appointment '{title}' booked successfully",
                event_id=created_event['id'],
                event_details=CalendarEvent(
                    id=created_event['id'],
                    title=created_event['summary'],
                    description=created_event.get('description'),
                    start_time=datetime.fromisoformat(created_event['start']['dateTime']),
                    end_time=datetime.fromisoformat(created_event['end']['dateTime']),
                    attendees=attendees or []
                )
            )

        except HttpError as error:
            print(f"❌ Failed to book appointment: {error}")
            return BookingResponse(
                success=False,
                message=f"Failed to book appointment: {error}",
                error_code="BOOKING_ERROR"
            )

    def get_events(self, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """Get events between start_date and end_date"""
        if not self.service:
            return []

        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_date.isoformat() + 'Z',
                timeMax=end_date.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            calendar_events = []

            for event in events:
                calendar_event = CalendarEvent(
                    id=event['id'],
                    title=event['summary'],
                    description=event.get('description'),
                    start_time=datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date'))),
                    end_time=datetime.fromisoformat(event['end'].get('dateTime', event['end'].get('date'))),
                    location=event.get('location'),
                    attendees=[attendee.get('email') for attendee in event.get('attendees', [])]
                )
                calendar_events.append(calendar_event)

            return calendar_events

        except HttpError as error:
            print(f'❌ Error getting events: {error}')
            return []

    def delete_event(self, event_id: str) -> bool:
        """Delete an event"""
        if not self.service:
            return False

        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            print(f"✅ Event {event_id} deleted successfully")
            return True
        except HttpError as error:
            print(f'❌ Error deleting event: {error}')
            return False


# Global instance
google_calendar = GoogleCalendar()
