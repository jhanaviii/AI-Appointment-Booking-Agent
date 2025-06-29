import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
from app.models.schemas import (
    ChatRequest, ChatResponse
)
from app.agent.conversation_graph import conversation_graph
from app.calendar.google_calendar import google_calendar
from app.calendar.mock_calendar import mock_calendar
from app.utils.validators import input_validator
from dotenv import load_dotenv

# Load .env from project root with absolute path
load_dotenv("/Users/jhanaviagarwal/PycharmProjects/assignment1/.env")

# Debug print
print(f"OpenAI Key loaded: {bool(os.getenv('OPENAI_API_KEY'))}")

app = FastAPI(
    title="AI Appointment Booking Agent",
    description="A conversational AI agent for booking appointments on Google Calendar",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: Dict[str, Dict[str, Any]] = {}

def get_calendar_service():
    use_real = os.getenv("USE_REAL_CALENDAR", "false").lower() == "true"
    if use_real:
        return google_calendar
    return mock_calendar

def get_session_id(request: ChatRequest) -> str:
    if request.session_id:
        return request.session_id
    return "default"

@app.get("/")
async def root():
    return {"message": "AI Appointment Booking Agent API", "version": "1.0.0", "status": "running"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        sanitized_message = input_validator.sanitize_input(request.message)
        if not sanitized_message:
            raise HTTPException(status_code=400, detail="Invalid message")

        session_id = get_session_id(request)
        result = conversation_graph.process_message(sanitized_message, session_id)

        sessions[session_id] = {
            "user_id": request.user_id,
            "last_message": sanitized_message,
            "state": result["state"]
        }

        return ChatResponse(
            message=result["message"],
            state=result["state"],
            available_slots=result["available_slots"],
            requires_confirmation=result["requires_confirmation"],
            error=result["error"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.get("/availability")
async def get_availability(start_date: str, end_date: str, duration_minutes: int = 60):
    from datetime import datetime
    try:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        is_valid, error_msg = input_validator.validate_date_range(start_dt, end_dt)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        calendar_service = get_calendar_service()
        availability = calendar_service.get_availability(start_dt, end_dt, duration_minutes)

        return availability

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting availability: {str(e)}")

@app.post("/book")
async def book_appointment(title: str, start_time: str, end_time: str, description: Optional[str] = None, attendees: Optional[str] = None):
    from datetime import datetime
    try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

        if not title.strip():
            raise HTTPException(status_code=400, detail="Title is required")

        attendee_list = []
        if attendees:
            attendee_list = [email.strip() for email in attendees.split(',') if email.strip()]

        calendar_service = get_calendar_service()
        booking_response = calendar_service.book_appointment(
            title=title,
            start_time=start_dt,
            end_time=end_dt,
            description=description,
            attendees=attendee_list
        )

        if booking_response.success:
            return booking_response
        else:
            raise HTTPException(status_code=400, detail=booking_response.message)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid time format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error booking appointment: {str(e)}")

@app.get("/events")
async def get_events(start_date: str, end_date: str):
    from datetime import datetime
    try:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        calendar_service = get_calendar_service()
        events = calendar_service.get_events(start_dt, end_dt)

        return {"events": [event.dict() for event in events]}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting events: {str(e)}")

@app.delete("/events/{event_id}")
async def delete_event(event_id: str):
    try:
        calendar_service = get_calendar_service()
        success = calendar_service.delete_event(event_id)
        if success:
            return {"message": "Event deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Event not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting event: {str(e)}")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "calendar_service": "available",
        "agent_service": "available"
    }

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
        conversation_graph.reset_conversation(session_id)
    return {"message": "Session deleted successfully"}

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
 