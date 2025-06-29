import re
from datetime import datetime, timedelta, time
from typing import Optional, Tuple, List
from dateutil import parser, relativedelta
import calendar


class DateParser:
    """Parse natural language date and time expressions"""
    
    def __init__(self):
        self.now = datetime.now()
        
    def parse_date_time(self, text: str) -> Optional[datetime]:
        """Parse date and time from natural language text"""
        text = text.lower().strip()
        
        # Try to parse with dateutil first
        try:
            return parser.parse(text, fuzzy=True)
        except:
            pass
        
        # Handle relative dates
        relative_date = self._parse_relative_date(text)
        if relative_date:
            return relative_date
        
        # Handle specific time patterns
        time_pattern = self._parse_time_pattern(text)
        if time_pattern:
            return time_pattern
            
        return None
    
    def _parse_relative_date(self, text: str) -> Optional[datetime]:
        """Parse relative dates like 'tomorrow', 'next week', etc."""
        today = self.now.date()
        
        # Tomorrow
        if 'tomorrow' in text:
            return datetime.combine(today + timedelta(days=1), time(9, 0))
        
        # Next day
        if 'next day' in text:
            return datetime.combine(today + timedelta(days=1), time(9, 0))
        
        # Next week
        if 'next week' in text:
            next_week = today + timedelta(weeks=1)
            # Find next Monday
            days_ahead = 7 - next_week.weekday()
            if days_ahead == 7:
                days_ahead = 0
            next_monday = next_week + timedelta(days=days_ahead)
            return datetime.combine(next_monday, time(9, 0))
        
        # This week
        if 'this week' in text:
            # Find next working day
            current_day = today.weekday()
            if current_day >= 5:  # Weekend
                days_ahead = 7 - current_day
                next_working_day = today + timedelta(days=days_ahead)
            else:
                next_working_day = today + timedelta(days=1)
            return datetime.combine(next_working_day, time(9, 0))
        
        # Today
        if 'today' in text:
            return datetime.combine(today, time(9, 0))
        
        return None
    
    def _parse_time_pattern(self, text: str) -> Optional[datetime]:
        """Parse specific time patterns"""
        # Time patterns like "3 PM", "15:00", etc.
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)?',
            r'(\d{1,2})\s*(am|pm)',
            r'(\d{1,2})\s*(a\.m\.|p\.m\.)',
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2)) if match.group(2) else 0
                ampm = match.group(3) if match.group(3) else None
                
                # Convert to 24-hour format
                if ampm:
                    ampm = ampm.lower()
                    if ampm in ['pm', 'p.m.'] and hour != 12:
                        hour += 12
                    elif ampm in ['am', 'a.m.'] and hour == 12:
                        hour = 0
                
                # Use today's date if no date specified
                return datetime.combine(self.now.date(), time(hour, minute))
        
        return None
    
    def parse_duration(self, text: str) -> Optional[int]:
        """Parse duration from text (returns minutes)"""
        text = text.lower().strip()
        
        # Pattern for "X hours", "X minutes", etc.
        patterns = [
            (r'(\d+)\s*hours?\b', 60),
            (r'(\d+)\s*hrs?\b', 60),
            (r'(\d+)\s*minutes?\b', 1),
            (r'(\d+)\s*mins?\b', 1),
        ]
        
        total_minutes = 0
        
        for pattern, multiplier in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                total_minutes += value * multiplier
        
        return total_minutes if total_minutes > 0 else None
    
    def parse_time_range(self, text: str) -> Optional[Tuple[datetime, datetime]]:
        """Parse time range like '3-5 PM' or 'between 2 and 4'"""
        text = text.lower().strip()
        
        # Pattern for "X-Y" or "between X and Y"
        range_patterns = [
            r'(\d{1,2}):?(\d{2})?\s*(am|pm)?\s*[-–]\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?',
            r'between\s+(\d{1,2}):?(\d{2})?\s*(am|pm)?\s+and\s+(\d{1,2}):?(\d{2})?\s*(am|pm)?',
        ]
        
        for pattern in range_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Extract start time
                start_hour = int(match.group(1))
                start_minute = int(match.group(2)) if match.group(2) else 0
                start_ampm = match.group(3) if match.group(3) else None
                
                # Extract end time
                end_hour = int(match.group(4))
                end_minute = int(match.group(5)) if match.group(5) else 0
                end_ampm = match.group(6) if match.group(6) else None
                
                # If only one AM/PM indicator is present, apply it to both times
                if start_ampm and not end_ampm:
                    end_ampm = start_ampm
                elif end_ampm and not start_ampm:
                    start_ampm = end_ampm
                
                # Convert to 24-hour format
                if start_ampm:
                    start_ampm = start_ampm.lower()
                    if start_ampm in ['pm', 'p.m.'] and start_hour != 12:
                        start_hour += 12
                    elif start_ampm in ['am', 'a.m.'] and start_hour == 12:
                        start_hour = 0
                
                if end_ampm:
                    end_ampm = end_ampm.lower()
                    if end_ampm in ['pm', 'p.m.'] and end_hour != 12:
                        end_hour += 12
                    elif end_ampm in ['am', 'a.m.'] and end_hour == 12:
                        end_hour = 0
                
                # Use today's date if no date specified
                today = self.now.date()
                start_time = datetime.combine(today, time(start_hour, start_minute))
                end_time = datetime.combine(today, time(end_hour, end_minute))
                
                return start_time, end_time
        
        return None
    
    def get_business_hours_slots(self, date: datetime, duration_minutes: int = 60) -> List[Tuple[datetime, datetime]]:
        """Generate business hours time slots for a given date"""
        slots = []
        business_start = time(9, 0)  # 9 AM
        business_end = time(18, 0)   # 6 PM
        
        # Check if it's a working day (Monday-Friday)
        if date.weekday() >= 5:  # Weekend
            return slots
        
        start_datetime = datetime.combine(date.date(), business_start)
        end_datetime = datetime.combine(date.date(), business_end)
        
        current_time = start_datetime
        while current_time + timedelta(minutes=duration_minutes) <= end_datetime:
            slot_end = current_time + timedelta(minutes=duration_minutes)
            slots.append((current_time, slot_end))
            current_time += timedelta(minutes=30)  # 30-minute intervals
        
        return slots
    
    def format_datetime(self, dt: datetime, include_time: bool = True) -> str:
        """Format datetime for display"""
        if include_time:
            # Use a more compatible format that works across systems
            time_str = dt.strftime("%I:%M %p").lstrip("0")
            return dt.strftime("%A, %B %d at ") + time_str
        else:
            return dt.strftime("%A, %B %d")
    
    def is_business_hours(self, dt: datetime) -> bool:
        """Check if datetime is within business hours"""
        business_start = time(9, 0)
        business_end = time(18, 0)
        
        # Check if it's a working day
        if dt.weekday() >= 5:  # Weekend
            return False
        
        # Check if it's within business hours
        current_time = dt.time()
        return business_start <= current_time < business_end


# Global instance
date_parser = DateParser() 