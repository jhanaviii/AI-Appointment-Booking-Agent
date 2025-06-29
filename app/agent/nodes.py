from dotenv import load_dotenv

load_dotenv("/Users/jhanaviagarwal/PycharmProjects/assignment1/.env")

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from openai import OpenAI
from app.agent.state import AgentState
from app.models.schemas import (
    ConversationStateEnum,
    IntentType,
    IntentResult,
    AppointmentRequest,
    TimeSlot
)
from app.utils.date_parser import date_parser
from app.calendar.google_calendar import google_calendar
from app.calendar.mock_calendar import mock_calendar


class ConversationNodes:
    """Enhanced conversation nodes with OpenAI integration"""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None
        if not self.client:
            print("OpenAI client not available. Using fallback intent classification.")

    def get_calendar_service(self):
        """Get calendar service based on configuration"""
        use_real = os.getenv("USE_REAL_CALENDAR", "false").lower() == "true"
        if use_real:
            return google_calendar
        return mock_calendar

    def classify_intent(self, state: AgentState) -> AgentState:
        """Enhanced intent classification with OpenAI"""
        user_message = state.get_last_user_message()
        if not user_message:
            return state

        # Try OpenAI classification first
        if self.client:
            try:
                intent_result = self._classify_with_openai_enhanced(user_message)
                state.set_intent_result(intent_result)
                return state
            except Exception as e:
                print(f"OpenAI classification failed: {e}")

        # Fallback to enhanced rule-based classification
        intent_result = self._classify_with_enhanced_rules(user_message)
        state.set_intent_result(intent_result)
        return state

    def _classify_with_openai_enhanced(self, user_message: str) -> IntentResult:
        """Enhanced OpenAI intent classification"""
        prompt = f"""
        Analyze this user message and classify the intent. Also extract any relevant entities.

        User message: "{user_message}"

        Classify into one of these intents:
        - GREETING: General greetings, hello, hi
        - HELP: Asking for help or what the system can do
        - BOOK_APPOINTMENT: Wanting to schedule, book, or create an appointment (includes time expressions)
        - CHECK_AVAILABILITY: Asking about free time, availability, open slots
        - UNKNOWN: Anything else

        Return ONLY a JSON object:
        {{
            "intent": "INTENT_NAME",
            "confidence": 0.0-1.0,
            "entities": {{
                "has_time": true/false,
                "has_duration": true/false,
                "appointment_type": "meeting/call/appointment/etc or null"
            }}
        }}

        Examples:
        - "Tomorrow at 3 PM for 1 hour" → {{"intent": "BOOK_APPOINTMENT", "confidence": 0.95, "entities": {{"has_time": true, "has_duration": true, "appointment_type": "meeting"}}}}
        - "Book a meeting between 3-5 PM next week" → {{"intent": "BOOK_APPOINTMENT", "confidence": 0.95, "entities": {{"has_time": true, "has_duration": false, "appointment_type": "meeting"}}}}
        """

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0
        )

        try:
            result = json.loads(response.choices[0].message.content.strip())

            intent_mapping = {
                "GREETING": IntentType.GREETING,
                "HELP": IntentType.HELP,
                "BOOK_APPOINTMENT": IntentType.BOOK_APPOINTMENT,
                "CHECK_AVAILABILITY": IntentType.CHECK_AVAILABILITY,
                "UNKNOWN": IntentType.UNKNOWN
            }

            intent = intent_mapping.get(result.get("intent"), IntentType.UNKNOWN)
            confidence = result.get("confidence", 0.5)
            entities = result.get("entities", {})

            return IntentResult(
                intent=intent,
                confidence=confidence,
                entities=entities
            )
        except:
            # Fallback if JSON parsing fails
            return self._classify_with_enhanced_rules(user_message)

    def _classify_with_enhanced_rules(self, user_message: str) -> IntentResult:
        """Enhanced rule-based intent classification"""
        message_lower = user_message.lower()

        # Time-related patterns suggest booking intent
        time_patterns = ['tomorrow', 'today', 'next week', 'friday', 'monday', 'tuesday', 'wednesday', 'thursday',
                         'saturday', 'sunday', 'pm', 'am', 'hour', 'minute', 'morning', 'afternoon', 'evening',
                         'between', '-']
        booking_words = ['book', 'schedule', 'appointment', 'meeting', 'call', 'reserve', 'set up', 'meet']

        # Greeting patterns
        greeting_words = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
        if any(word in message_lower for word in greeting_words):
            return IntentResult(intent=IntentType.GREETING, confidence=0.8, entities={})

        # Help patterns
        help_words = ['help', 'what can you do', 'how does this work', 'what do you do']
        if any(word in message_lower for word in help_words):
            return IntentResult(intent=IntentType.HELP, confidence=0.8, entities={})

        # If message contains time patterns, likely a booking request
        if any(pattern in message_lower for pattern in time_patterns):
            return IntentResult(intent=IntentType.BOOK_APPOINTMENT, confidence=0.8, entities={"has_time": True})

        # Explicit booking words
        if any(word in message_lower for word in booking_words):
            return IntentResult(intent=IntentType.BOOK_APPOINTMENT, confidence=0.7, entities={})

        # Availability patterns
        availability_words = ['available', 'free', 'open', 'availability', 'free time', 'open slots']
        if any(word in message_lower for word in availability_words):
            return IntentResult(intent=IntentType.CHECK_AVAILABILITY, confidence=0.7, entities={})

        # Default to unknown
        return IntentResult(intent=IntentType.UNKNOWN, confidence=0.3, entities={})

    def handle_greeting(self, state: AgentState) -> AgentState:
        """Handle greeting intent"""
        response = """Hello! I'm your AI appointment booking assistant. I can help you:

• Schedule appointments and meetings
• Check your calendar availability  
• Find the best time slots for you

What would you like to do today? You can say things like:
"I want to schedule a call for tomorrow afternoon"
"Do you have any free time this Friday?"
"Book a meeting between 3-5 PM next week" """

        state.add_assistant_message(response)
        state.update_state(ConversationStateEnum.INITIAL)
        return state

    def handle_help(self, state: AgentState) -> AgentState:
        """Handle help intent"""
        response = """I'm here to help you book appointments! Here's what I can do:

📅 **Book Appointments**: I can schedule meetings, calls, or any appointments
🕒 **Check Availability**: I can show you available time slots
📝 **Smart Scheduling**: I understand natural language like "tomorrow at 3 PM"

**Examples of what you can say:**
• "Schedule a team meeting for next Monday at 2 PM"
• "I need a 30-minute call tomorrow afternoon"
• "What's available this Friday?"
• "Book a meeting between 10 AM and 12 PM next week"

**Business Hours:** Monday-Friday, 9 AM - 6 PM

What would you like to do?"""

        state.add_assistant_message(response)
        state.update_state(ConversationStateEnum.INITIAL)
        return state

    def collect_appointment_details_with_ai(self, state: AgentState) -> AgentState:
        """Enhanced appointment detail collection using OpenAI"""
        user_message = state.get_last_user_message()
        if not user_message:
            return state

        # Get existing appointment request or create new one
        appointment_request = state.conversation_state.appointment_request or AppointmentRequest(duration_minutes=60)

        # Use OpenAI to extract structured information
        if self.client:
            try:
                extracted_info = self._extract_appointment_info_with_ai(user_message, appointment_request)

                # Update appointment request with AI-extracted info
                if extracted_info.get('start_time'):
                    try:
                        appointment_request.start_date = datetime.fromisoformat(extracted_info['start_time'])
                    except:
                        pass
                if extracted_info.get('end_time'):
                    try:
                        appointment_request.end_date = datetime.fromisoformat(extracted_info['end_time'])
                    except:
                        pass
                if extracted_info.get('duration'):
                    appointment_request.duration_minutes = extracted_info['duration']
                if extracted_info.get('title'):
                    appointment_request.title = extracted_info['title']
                if extracted_info.get('description'):
                    appointment_request.description = extracted_info['description']

            except Exception as e:
                print(f"AI extraction failed, using fallback: {e}")

        # Fallback to rule-based extraction if AI fails or not available
        if not appointment_request.start_date:
            # Try time range parsing first
            time_range = date_parser.parse_time_range(user_message)
            if time_range:
                appointment_request.start_date, appointment_request.end_date = time_range
                # Calculate duration from time range
                if appointment_request.start_date and appointment_request.end_date:
                    duration = (appointment_request.end_date - appointment_request.start_date).total_seconds() / 60
                    appointment_request.duration_minutes = int(duration)
            else:
                # Try single date/time parsing
                parsed_date = date_parser.parse_date_time(user_message)
                if parsed_date:
                    appointment_request.start_date = parsed_date

        # Try to parse duration if not set
        if not appointment_request.duration_minutes:
            duration = date_parser.parse_duration(user_message)
            if duration:
                appointment_request.duration_minutes = duration
            elif not appointment_request.end_date:
                appointment_request.duration_minutes = 60  # Default 1 hour

        # Set default title if not set
        if not appointment_request.title:
            meeting_keywords = {
                'meeting': 'Meeting',
                'call': 'Call',
                'appointment': 'Appointment',
                'interview': 'Interview',
                'consultation': 'Consultation'
            }
            for keyword, title in meeting_keywords.items():
                if keyword in user_message.lower():
                    appointment_request.title = title
                    break
            if not appointment_request.title:
                appointment_request.title = "Meeting"

        # Save the updated appointment request
        state.set_appointment_request(appointment_request)

        # Check if we have enough information to proceed
        has_start_time = appointment_request.start_date is not None
        has_duration = appointment_request.duration_minutes is not None

        if has_start_time and has_duration:
            # Calculate end time if not provided
            if not appointment_request.end_date:
                appointment_request.end_date = appointment_request.start_date + timedelta(
                    minutes=appointment_request.duration_minutes)
                state.set_appointment_request(appointment_request)

            state.update_state(ConversationStateEnum.CHECKING_AVAILABILITY)
            return self.check_availability(state)

        elif has_start_time and not has_duration:
            # Generate contextual response
            formatted_date = date_parser.format_datetime(appointment_request.start_date)
            response = f"Great! I see you want to meet on {formatted_date}. How long should the meeting be? (e.g., '30 minutes', '1 hour')"
            state.add_assistant_message(response)
            state.update_state(ConversationStateEnum.COLLECTING_DETAILS)

        elif not has_start_time:
            # Generate contextual response
            response = """I'd be happy to help you schedule an appointment! I just need to know when you'd like to meet. You can say things like:

• "Tomorrow at 3 PM for 1 hour"
• "Next Monday between 2-4 PM" 
• "A 30-minute call this afternoon"

When would you like to schedule your appointment?"""
            state.add_assistant_message(response)
            state.update_state(ConversationStateEnum.COLLECTING_DETAILS)

        return state

    def _extract_appointment_info_with_ai(self, user_message: str, current_request: AppointmentRequest) -> Dict[
        str, Any]:
        """Use OpenAI to extract structured appointment information"""
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        prompt = f"""
        Extract appointment information from the user message. Current date/time: {current_date}

        User message: "{user_message}"

        Current appointment info:
        - Title: {current_request.title or 'None'}
        - Start time: {current_request.start_date.isoformat() if current_request.start_date else 'None'}
        - Duration: {current_request.duration_minutes or 'None'} minutes

        Extract and return ONLY a JSON object with these fields (use null for missing values):
        {{
            "start_time": "ISO datetime string (e.g., 2025-07-07T15:00:00)",
            "end_time": "ISO datetime string or null",
            "duration": "duration in minutes as integer or null",
            "title": "meeting title/type or null",
            "description": "additional details or null"
        }}

        Examples:
        - "Tomorrow at 3 PM for 1 hour" → {{"start_time": "2025-06-29T15:00:00", "duration": 60, "title": "Meeting"}}
        - "Book a meeting between 3-5 PM next week" → {{"start_time": "2025-07-07T15:00:00", "end_time": "2025-07-07T17:00:00", "title": "Meeting"}}
        - "today at 9pm for an hour" → {{"start_time": "2025-06-28T21:00:00", "duration": 60, "title": "Meeting"}}
        """

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0
        )

        try:
            result = json.loads(response.choices[0].message.content.strip())
            return result
        except:
            return {}

    def check_availability(self, state: AgentState) -> AgentState:
        """Check calendar availability"""
        appointment_request = state.conversation_state.appointment_request
        if not appointment_request or not appointment_request.start_date:
            return self.collect_appointment_details_with_ai(state)

        try:
            calendar_service = self.get_calendar_service()

            # Check if the exact time is available
            is_available = calendar_service.is_time_available(
                appointment_request.start_date,
                appointment_request.end_date or (
                            appointment_request.start_date + timedelta(minutes=appointment_request.duration_minutes))
            )

            if is_available:
                # Time is available, move to confirmation
                formatted_date = date_parser.format_datetime(appointment_request.start_date)
                response = f"""Perfect! I found that {formatted_date} is available for your {appointment_request.title.lower()}.

**Appointment Details:**
• **Date & Time:** {formatted_date}
• **Duration:** {appointment_request.duration_minutes} minutes
• **Title:** {appointment_request.title}

Would you like me to book this appointment? (Yes/No)"""

                state.add_assistant_message(response)
                state.update_state(ConversationStateEnum.CONFIRMING_BOOKING)
            else:
                # Time not available, suggest alternatives
                state.update_state(ConversationStateEnum.SUGGESTING_SLOTS)
                return self.suggest_alternative_slots(state)

        except Exception as e:
            response = f"I encountered an error checking your calendar: {str(e)}. Let me try to find alternative times for you."
            state.add_assistant_message(response)
            state.update_state(ConversationStateEnum.SUGGESTING_SLOTS)
            return self.suggest_alternative_slots(state)

        return state

    def suggest_alternative_slots(self, state: AgentState) -> AgentState:
        """Suggest alternative time slots"""
        appointment_request = state.conversation_state.appointment_request
        if not appointment_request:
            return state

        try:
            calendar_service = self.get_calendar_service()

            # Get available slots around the requested time
            start_search = appointment_request.start_date or datetime.now()
            end_search = start_search + timedelta(days=7)  # Search within a week

            available_slots = calendar_service.get_availability(
                start_search,
                end_search,
                appointment_request.duration_minutes or 60
            )

            if available_slots.available_slots:
                # Store available slots in state
                state.conversation_state.available_slots = available_slots.available_slots[:5]  # Limit to 5 suggestions

                slots_text = "\n".join([
                    f"• **Option {i + 1}:** {date_parser.format_datetime(slot.start_time)}"
                    for i, slot in enumerate(state.conversation_state.available_slots)
                ])

                formatted_requested = date_parser.format_datetime(
                    appointment_request.start_date) if appointment_request.start_date else "your requested time"
                response = f"""I'm sorry, but {formatted_requested} is not available. Here are some alternative times for your {appointment_request.duration_minutes}-minute {appointment_request.title.lower()}:

{slots_text}

Which option works best for you? You can say "Option 1", "Option 2", etc., or suggest a different time."""

                state.add_assistant_message(response)
                state.update_state(ConversationStateEnum.SUGGESTING_SLOTS)
            else:
                response = f"I couldn't find any available slots for a {appointment_request.duration_minutes}-minute meeting in the next week. Could you suggest some alternative times or dates that might work for you?"
                state.add_assistant_message(response)
                state.update_state(ConversationStateEnum.COLLECTING_DETAILS)

        except Exception as e:
            response = f"I encountered an error finding alternative times: {str(e)}. Could you suggest some times that might work for you?"
            state.add_assistant_message(response)
            state.update_state(ConversationStateEnum.COLLECTING_DETAILS)

        return state

    def handle_slot_selection(self, state: AgentState) -> AgentState:
        """Handle user selection of suggested time slots"""
        user_message = state.get_last_user_message()
        if not user_message:
            return state

        available_slots = state.conversation_state.available_slots
        if not available_slots:
            return self.collect_appointment_details_with_ai(state)

        # Parse slot selection
        message_lower = user_message.lower()
        selected_slot = None

        # Check for "option X" pattern
        for i in range(len(available_slots)):
            if f"option {i + 1}" in message_lower or f"{i + 1}" in message_lower:
                selected_slot = available_slots[i]
                break

        if selected_slot:
            # Update appointment request with selected slot
            appointment_request = state.conversation_state.appointment_request
            appointment_request.start_date = selected_slot.start_time
            appointment_request.end_date = selected_slot.end_time
            state.set_appointment_request(appointment_request)

            formatted_date = date_parser.format_datetime(selected_slot.start_time)
            response = f"""Great choice! I'll book your {appointment_request.title.lower()} for:

**Appointment Details:**
• **Date & Time:** {formatted_date}
• **Duration:** {appointment_request.duration_minutes} minutes
• **Title:** {appointment_request.title}

Would you like me to confirm this booking? (Yes/No)"""

            state.add_assistant_message(response)
            state.update_state(ConversationStateEnum.CONFIRMING_BOOKING)
        else:
            # User didn't select a valid option, try to parse new time
            return self.collect_appointment_details_with_ai(state)

        return state

    def confirm_booking(self, state: AgentState) -> AgentState:
        """Handle booking confirmation"""
        user_message = state.get_last_user_message()
        if not user_message:
            return state

        message_lower = user_message.lower()

        if any(word in message_lower for word in ['yes', 'confirm', 'book', 'schedule', 'ok', 'sure']):
            # User confirmed, proceed with booking
            return self.book_appointment(state)
        elif any(word in message_lower for word in ['no', 'cancel', 'nevermind', 'not now']):
            # User cancelled
            response = "No problem! Your appointment has not been booked. Is there anything else I can help you with? You can always start over by telling me when you'd like to schedule something."
            state.add_assistant_message(response)
            state.update_state(ConversationStateEnum.INITIAL)
        else:
            # Unclear response
            response = "I didn't understand. Would you like me to book this appointment? Please say 'Yes' to confirm or 'No' to cancel."
            state.add_assistant_message(response)
            state.update_state(ConversationStateEnum.CONFIRMING_BOOKING)

        return state

    def book_appointment(self, state: AgentState) -> AgentState:
        """Book the appointment - FIXED VERSION"""
        appointment_request = state.conversation_state.appointment_request
        if not appointment_request or not appointment_request.start_date:
            return self.collect_appointment_details_with_ai(state)

        try:
            calendar_service = self.get_calendar_service()

            # Handle optional attributes safely
            attendees = getattr(appointment_request, 'attendees', [])
            description = getattr(appointment_request, 'description', None)

            booking_result = calendar_service.book_appointment(
                title=appointment_request.title,
                start_time=appointment_request.start_date,
                end_time=appointment_request.end_date or (
                            appointment_request.start_date + timedelta(minutes=appointment_request.duration_minutes)),
                description=description,
                attendees=attendees
            )

            if booking_result.success:
                formatted_date = date_parser.format_datetime(appointment_request.start_date)
                response = f"""✅ **Appointment Booked Successfully!**

**Your appointment details:**
• **Title:** {appointment_request.title}
• **Date & Time:** {formatted_date}
• **Duration:** {appointment_request.duration_minutes} minutes
• **Event ID:** {booking_result.event_id}

Your appointment has been added to your Google Calendar. Is there anything else I can help you with?"""

                state.add_assistant_message(response)
                state.update_state(ConversationStateEnum.BOOKING_COMPLETE)
            else:
                response = f"I'm sorry, there was an error booking your appointment: {booking_result.message}. Would you like to try a different time?"
                state.add_assistant_message(response)
                state.update_state(ConversationStateEnum.COLLECTING_DETAILS)

        except Exception as e:
            response = f"I encountered an error while booking your appointment: {str(e)}. Would you like to try again or choose a different time?"
            state.add_assistant_message(response)
            state.update_state(ConversationStateEnum.COLLECTING_DETAILS)

        return state

    def handle_contextual_response(self, state: AgentState) -> AgentState:
        """Handle unclear input with OpenAI context understanding"""
        user_message = state.get_last_user_message()

        if not self.client:
            return self.handle_unknown_intent(state)

        try:
            conversation_history = [msg.content for msg in state.get_conversation_history()[-5:]]

            prompt = f"""
            You are an AI appointment booking assistant. The user said something unclear.

            Recent conversation:
            {chr(10).join(conversation_history)}

            Latest user message: "{user_message}"

            Generate a helpful response that:
            - Tries to understand what they might want
            - Guides them toward booking an appointment
            - Provides specific examples
            - Stays friendly and conversational
            - Is concise (2-3 sentences max)
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.7
            )

            ai_response = response.choices[0].message.content.strip()
            state.add_assistant_message(ai_response)
            state.update_state(ConversationStateEnum.INITIAL)

        except Exception as e:
            print(f"AI contextual response failed: {e}")
            return self.handle_unknown_intent(state)

        return state

    def handle_unknown_intent(self, state: AgentState) -> AgentState:
        """Handle unknown or unclear user input"""
        response = """I'm not sure what you'd like to do. I can help you with:

• **Booking appointments and meetings**
• **Checking your calendar availability** 
• **Finding the best time slots**

Could you please clarify what you need? For example:
• "I want to schedule a meeting"
• "What times are available tomorrow?"
• "Book a call for next week" """

        state.add_assistant_message(response)
        state.update_state(ConversationStateEnum.INITIAL)
        return state


# Global instance
conversation_nodes = ConversationNodes()
