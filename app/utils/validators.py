from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from app.models.schemas import AppointmentRequest, TimeSlot


class InputValidator:
    """Validate user inputs for appointment booking"""
    
    def __init__(self):
        self.min_duration = 15  # minutes
        self.max_duration = 240  # minutes (4 hours)
        self.business_hours_start = 9  # 9 AM
        self.business_hours_end = 18   # 6 PM
        self.max_days_ahead = 90  # 3 months
    
    def validate_appointment_request(self, request: AppointmentRequest) -> Tuple[bool, Optional[str]]:
        """Validate appointment request"""
        # Check if we have enough information
        if not request.start_date and not request.end_date:
            return False, "Please specify a date and time for the appointment"
        
        # Validate duration
        if request.duration_minutes:
            if request.duration_minutes < self.min_duration:
                return False, f"Duration must be at least {self.min_duration} minutes"
            if request.duration_minutes > self.max_duration:
                return False, f"Duration cannot exceed {self.max_duration} minutes"
        
        # Validate date range
        if request.start_date and request.end_date:
            if request.start_date >= request.end_date:
                return False, "Start time must be before end time"
            
            # Check if it's too far in the future
            if request.start_date > datetime.now() + timedelta(days=self.max_days_ahead):
                return False, f"Cannot book appointments more than {self.max_days_ahead} days in advance"
            
            # Check if it's in the past
            if request.start_date < datetime.now():
                return False, "Cannot book appointments in the past"
        
        return True, None
    
    def validate_time_slot(self, slot: TimeSlot) -> Tuple[bool, Optional[str]]:
        """Validate time slot"""
        # Check duration
        if slot.duration_minutes < self.min_duration:
            return False, f"Slot duration must be at least {self.min_duration} minutes"
        
        if slot.duration_minutes > self.max_duration:
            return False, f"Slot duration cannot exceed {self.max_duration} minutes"
        
        # Check if start time is before end time
        if slot.start_time >= slot.end_time:
            return False, "Start time must be before end time"
        
        # Check if it's in the past
        if slot.start_time < datetime.now():
            return False, "Cannot book slots in the past"
        
        # Check if it's too far in the future
        if slot.start_time > datetime.now() + timedelta(days=self.max_days_ahead):
            return False, f"Cannot book slots more than {self.max_days_ahead} days in advance"
        
        return True, None
    
    def is_business_hours(self, dt: datetime) -> bool:
        """Check if datetime is within business hours"""
        # Check if it's a working day (Monday-Friday)
        if dt.weekday() >= 5:  # Weekend
            return False
        
        # Check if it's within business hours
        hour = dt.hour
        return self.business_hours_start <= hour < self.business_hours_end
    
    def validate_date_range(self, start_date: datetime, end_date: datetime) -> Tuple[bool, Optional[str]]:
        """Validate date range"""
        if start_date >= end_date:
            return False, "Start date must be before end date"
        
        if start_date < datetime.now():
            return False, "Start date cannot be in the past"
        
        if start_date > datetime.now() + timedelta(days=self.max_days_ahead):
            return False, f"Cannot check availability more than {self.max_days_ahead} days in advance"
        
        return True, None
    
    def sanitize_input(self, text: str) -> str:
        """Sanitize user input to prevent injection attacks"""
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '{', '}']
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        # Limit length
        if len(text) > 1000:
            text = text[:1000]
        
        return text.strip()
    
    def validate_email(self, email: str) -> bool:
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_phone(self, phone: str) -> bool:
        """Basic phone number validation"""
        import re
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        # Check if it's a reasonable length (7-15 digits)
        return 7 <= len(digits_only) <= 15
    
    def get_validation_errors(self, request: AppointmentRequest) -> List[str]:
        """Get all validation errors for an appointment request"""
        errors = []
        
        # Check required fields
        if not request.start_date and not request.end_date:
            errors.append("Date and time are required")
        
        # Validate duration
        if request.duration_minutes:
            if request.duration_minutes < self.min_duration:
                errors.append(f"Duration must be at least {self.min_duration} minutes")
            elif request.duration_minutes > self.max_duration:
                errors.append(f"Duration cannot exceed {self.max_duration} minutes")
        
        # Validate date range
        if request.start_date and request.end_date:
            if request.start_date >= request.end_date:
                errors.append("Start time must be before end time")
            
            if request.start_date < datetime.now():
                errors.append("Cannot book appointments in the past")
            
            if request.start_date > datetime.now() + timedelta(days=self.max_days_ahead):
                errors.append(f"Cannot book appointments more than {self.max_days_ahead} days in advance")
        
        return errors


# Global instance
input_validator = InputValidator() 