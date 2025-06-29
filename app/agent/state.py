from typing import List, Optional
from datetime import datetime
from app.models.schemas import (
    ConversationState,
    ConversationStateEnum,
    AppointmentRequest,
    IntentResult,
    Message  # Changed from ConversationMessage to Message
)


class AgentState:
    """Agent state management for conversation flow"""

    def __init__(self):
        self.conversation_state = ConversationState()
        self.messages: List[Message] = []
        self.intent_result: Optional[IntentResult] = None

    def add_user_message(self, content: str):
        """Add a user message to the conversation"""
        message = Message(role="user", content=content, timestamp=datetime.now())
        self.messages.append(message)

    def add_assistant_message(self, content: str):
        """Add an assistant message to the conversation"""
        message = Message(role="assistant", content=content, timestamp=datetime.now())
        self.messages.append(message)

    def get_last_user_message(self) -> Optional[str]:
        """Get the last user message content"""
        for message in reversed(self.messages):
            if message.role == "user":
                return message.content
        return None

    def get_last_assistant_message(self) -> Optional[str]:
        """Get the last assistant message content"""
        for message in reversed(self.messages):
            if message.role == "assistant":
                return message.content
        return None

    def get_conversation_history(self) -> List[Message]:
        """Get the full conversation history"""
        return self.messages

    def update_state(self, new_state: ConversationStateEnum):
        """Update the conversation state"""
        self.conversation_state.current_state = new_state

    def set_appointment_request(self, appointment_request: AppointmentRequest):
        """Set the appointment request"""
        self.conversation_state.appointment_request = appointment_request

    def set_intent_result(self, intent_result: IntentResult):
        """Set the intent result"""
        self.intent_result = intent_result

    def is_initial_state(self) -> bool:
        """Check if in initial state"""
        return self.conversation_state.current_state == ConversationStateEnum.INITIAL

    def is_collecting_details(self) -> bool:
        """Check if collecting appointment details"""
        return self.conversation_state.current_state == ConversationStateEnum.COLLECTING_DETAILS

    def is_checking_availability(self) -> bool:
        """Check if checking availability"""
        return self.conversation_state.current_state == ConversationStateEnum.CHECKING_AVAILABILITY

    def is_suggesting_slots(self) -> bool:
        """Check if suggesting time slots"""
        return self.conversation_state.current_state == ConversationStateEnum.SUGGESTING_SLOTS

    def is_confirming_booking(self) -> bool:
        """Check if confirming booking"""
        return self.conversation_state.current_state == ConversationStateEnum.CONFIRMING_BOOKING

    def is_booking_complete(self) -> bool:
        """Check if booking is complete"""
        return self.conversation_state.current_state == ConversationStateEnum.BOOKING_COMPLETE
