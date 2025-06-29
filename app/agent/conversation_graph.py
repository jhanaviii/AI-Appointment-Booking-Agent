from dotenv import load_dotenv

load_dotenv("/Users/jhanaviagarwal/PycharmProjects/assignment1/.env")

import os
from typing import Dict, Any, List
from openai import OpenAI
from app.agent.state import AgentState
from app.agent.nodes import conversation_nodes
from app.models.schemas import ConversationStateEnum, IntentType


class ConversationGraph:
    """Enhanced conversation flow with OpenAI integration"""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
            print("OpenAI client initialized successfully.")
        else:
            self.client = None
            print("OpenAI API key not found. Using fallback intent classification.")
        self.sessions = {}

    def process_message(self, message: str, session_id: str = "default") -> Dict[str, Any]:
        """Enhanced message processing with OpenAI"""
        try:
            # Get or create session state
            if session_id not in self.sessions:
                self.sessions[session_id] = AgentState()

            state = self.sessions[session_id]

            # Add user message
            state.add_user_message(message)

            # Enhanced routing with OpenAI context
            if state.is_initial_state():
                # Use OpenAI for better intent classification
                state = conversation_nodes.classify_intent(state)
                state = self._route_initial_intent(state)

            elif state.is_collecting_details():
                # Use OpenAI to better understand appointment details
                state = conversation_nodes.collect_appointment_details_with_ai(state)

            elif state.is_checking_availability():
                state = conversation_nodes.check_availability(state)

            elif state.is_suggesting_slots():
                state = conversation_nodes.handle_slot_selection(state)

            elif state.is_confirming_booking():
                state = conversation_nodes.confirm_booking(state)

            else:
                # Use OpenAI for contextual responses
                state = conversation_nodes.handle_contextual_response(state)

            # Update session
            self.sessions[session_id] = state

            # Get response
            last_assistant_message = state.get_last_assistant_message()
            if not last_assistant_message:
                last_assistant_message = "I'm here to help you book appointments. What would you like to do?"

            return {
                "message": last_assistant_message,
                "state": state.conversation_state.dict(),
                "available_slots": [slot.dict() for slot in state.conversation_state.available_slots],
                "requires_confirmation": state.is_confirming_booking(),
                "error": state.conversation_state.error_message
            }

        except Exception as e:
            error_message = f"I encountered an error: {str(e)}. Let me help you start over."
            return {
                "message": error_message,
                "state": AgentState().conversation_state.dict(),
                "available_slots": [],
                "requires_confirmation": False,
                "error": str(e)
            }

    def _route_initial_intent(self, state: AgentState) -> AgentState:
        """Enhanced routing with OpenAI context"""
        if not state.intent_result:
            return conversation_nodes.handle_contextual_response(state)

        intent = state.intent_result.intent

        if intent == IntentType.GREETING:
            return conversation_nodes.handle_greeting(state)
        elif intent == IntentType.HELP:
            return conversation_nodes.handle_help(state)
        elif intent in [IntentType.BOOK_APPOINTMENT, IntentType.CHECK_AVAILABILITY]:
            return conversation_nodes.collect_appointment_details_with_ai(state)
        else:
            return conversation_nodes.handle_contextual_response(state)

    def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        if session_id in self.sessions:
            state = self.sessions[session_id]
            return [msg.dict() for msg in state.get_conversation_history()]
        return []

    def reset_conversation(self, session_id: str) -> bool:
        """Reset conversation for a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        return True


# Global instance
conversation_graph = ConversationGraph()
