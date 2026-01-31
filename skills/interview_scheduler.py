"""
Interview Scheduling System for Job Application Assistant

Features:
- Parse interview requests from emails
- Check calendar availability
- Generate scheduling responses
- Create calendar events for confirmed interviews
- Send reminders before interviews
- Track interview outcomes
"""
import os
import re
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Google Calendar integration
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    GCAL_AVAILABLE = True
except ImportError:
    GCAL_AVAILABLE = False


@dataclass
class InterviewSlot:
    """Represents an interview time slot."""
    date: datetime
    duration_minutes: int = 60
    confirmed: bool = False
    company: str = ""
    position: str = ""
    interviewer: str = ""
    meeting_link: str = ""
    notes: str = ""


def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_calendar_service():
    """Get Google Calendar API service."""
    if not GCAL_AVAILABLE:
        return None
    
    # Reuse Gmail credentials (they include calendar scope)
    from gmail_handler import get_credentials
    creds = get_credentials()
    if not creds:
        return None
    
    return build('calendar', 'v3', credentials=creds)


def get_busy_times(days_ahead: int = 14) -> List[Tuple[datetime, datetime]]:
    """
    Get busy time slots from Google Calendar.
    """
    service = get_calendar_service()
    if not service:
        return []
    
    now = datetime.utcnow()
    time_min = now.isoformat() + 'Z'
    time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
    
    try:
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        busy_times = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            
            busy_times.append((start_dt, end_dt))
        
        return busy_times
        
    except Exception as e:
        print(f"Error fetching calendar: {e}")
        return []


def generate_available_slots(
    days_ahead: int = 14,
    slot_duration: int = 60,
    working_hours: Tuple[int, int] = (9, 17),
    exclude_weekends: bool = True
) -> List[datetime]:
    """
    Generate available time slots based on calendar and preferences.
    """
    config = load_config()
    
    # Get busy times
    busy_times = get_busy_times(days_ahead)
    
    # Generate potential slots
    available = []
    current = datetime.now().replace(hour=working_hours[0], minute=0, second=0, microsecond=0)
    
    if current < datetime.now():
        current += timedelta(days=1)
    
    end_date = datetime.now() + timedelta(days=days_ahead)
    
    while current < end_date:
        # Skip weekends if configured
        if exclude_weekends and current.weekday() >= 5:
            current += timedelta(days=1)
            current = current.replace(hour=working_hours[0])
            continue
        
        # Check if within working hours
        if current.hour >= working_hours[1]:
            current += timedelta(days=1)
            current = current.replace(hour=working_hours[0])
            continue
        
        # Check if slot conflicts with busy times
        slot_end = current + timedelta(minutes=slot_duration)
        is_available = True
        
        for busy_start, busy_end in busy_times:
            # Make timezone-naive for comparison
            busy_start = busy_start.replace(tzinfo=None)
            busy_end = busy_end.replace(tzinfo=None)
            
            if (current < busy_end and slot_end > busy_start):
                is_available = False
                break
        
        if is_available:
            available.append(current)
        
        current += timedelta(minutes=30)  # 30-min increments
    
    return available


def format_slots_for_email(slots: List[datetime], max_slots: int = 5) -> str:
    """
    Format available slots for email response.
    """
    if not slots:
        return "I have limited availability this week. Could you please suggest some times that work for you?"
    
    # Group by day
    days = {}
    for slot in slots[:max_slots * 2]:  # Get extra to have options
        day_key = slot.strftime('%A, %B %d')
        if day_key not in days:
            days[day_key] = []
        if len(days[day_key]) < 3:  # Max 3 slots per day
            days[day_key].append(slot.strftime('%I:%M %p'))
    
    lines = []
    for day, times in list(days.items())[:max_slots]:
        times_str = ', '.join(times[:2])
        if len(times) > 2:
            times_str += f", or {times[2]}"
        lines.append(f"  • {day}: {times_str}")
    
    return '\n'.join(lines)


def create_interview_event(
    interview: InterviewSlot,
    add_reminder: bool = True
) -> Optional[str]:
    """
    Create a calendar event for a confirmed interview.
    """
    service = get_calendar_service()
    if not service:
        return None
    
    event = {
        'summary': f'Interview: {interview.position} at {interview.company}',
        'description': f"""Interview Details:
Company: {interview.company}
Position: {interview.position}
Interviewer: {interview.interviewer}
Meeting Link: {interview.meeting_link}

Notes: {interview.notes}

Preparation Checklist:
□ Research company recent news
□ Review job description
□ Prepare questions to ask
□ Test video/audio setup
□ Have resume ready to reference
""",
        'start': {
            'dateTime': interview.date.isoformat(),
            'timeZone': 'America/Los_Angeles',
        },
        'end': {
            'dateTime': (interview.date + timedelta(minutes=interview.duration_minutes)).isoformat(),
            'timeZone': 'America/Los_Angeles',
        },
        'colorId': '9',  # Blue for interviews
    }
    
    if interview.meeting_link:
        event['location'] = interview.meeting_link
    
    if add_reminder:
        event['reminders'] = {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 60},  # 1 hour before
                {'method': 'popup', 'minutes': 15},  # 15 min before
                {'method': 'email', 'minutes': 1440},  # 1 day before
            ],
        }
    
    try:
        result = service.events().insert(
            calendarId='primary',
            body=event
        ).execute()
        
        return result.get('htmlLink')
        
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        return None


def parse_proposed_times(email_body: str) -> List[Dict]:
    """
    Extract proposed interview times from an email.
    """
    proposed = []
    
    # Common patterns for proposed times
    patterns = [
        # "Tuesday, January 15 at 2:00 PM"
        r'(Monday|Tuesday|Wednesday|Thursday|Friday),?\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s*(\d{1,2})(?:st|nd|rd|th)?\s*(?:at|@)?\s*(\d{1,2}):?(\d{2})?\s*(AM|PM|am|pm)?',
        # "1/15 at 2pm"
        r'(\d{1,2})/(\d{1,2})(?:/\d{2,4})?\s*(?:at|@)\s*(\d{1,2}):?(\d{2})?\s*(AM|PM|am|pm)?',
        # "2:00 PM PST"
        r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)\s*(?:PST|EST|CST|MST|PT|ET)?',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, email_body, re.IGNORECASE)
        for match in matches:
            proposed.append({
                'raw': match,
                'pattern': pattern,
            })
    
    return proposed


def generate_interview_confirmation(
    interview: InterviewSlot,
    include_prep_notes: bool = True
) -> str:
    """
    Generate a confirmation message for a scheduled interview.
    """
    config = load_config()
    user = config.get('user', {})
    
    message = f"""Dear Hiring Team,

Thank you for scheduling this interview. I'm confirming our meeting:

📅 Date: {interview.date.strftime('%A, %B %d, %Y')}
⏰ Time: {interview.date.strftime('%I:%M %p')} PST
🏢 Company: {interview.company}
💼 Position: {interview.position}
"""

    if interview.meeting_link:
        message += f"🔗 Meeting Link: {interview.meeting_link}\n"
    
    if interview.interviewer:
        message += f"👤 Interviewer: {interview.interviewer}\n"
    
    message += """
I'm very excited about this opportunity and look forward to our conversation.

Please let me know if you need any additional information from me before our meeting.

Best regards,
"""
    message += f"{user.get('name', 'Deanna Wiley')}\n"
    message += f"{user.get('phone', '(708) 265-8734')}\n"
    message += f"{user.get('email', 'DeannaWileyCareers@gmail.com')}"
    
    return message


def get_upcoming_interviews(days_ahead: int = 7) -> List[Dict]:
    """
    Get upcoming interviews from calendar.
    """
    service = get_calendar_service()
    if not service:
        return []
    
    now = datetime.utcnow()
    time_min = now.isoformat() + 'Z'
    time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
    
    try:
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            q='interview',  # Search for interview events
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        interviews = []
        for event in events:
            if 'interview' in event.get('summary', '').lower():
                interviews.append({
                    'id': event['id'],
                    'title': event.get('summary', ''),
                    'start': event['start'].get('dateTime', event['start'].get('date')),
                    'end': event['end'].get('dateTime', event['end'].get('date')),
                    'location': event.get('location', ''),
                    'description': event.get('description', ''),
                })
        
        return interviews
        
    except Exception as e:
        print(f"Error fetching interviews: {e}")
        return []


def send_interview_reminder(interview: Dict) -> bool:
    """
    Send a Slack reminder for an upcoming interview.
    """
    try:
        from slack_notify import send_application_status
        
        start_time = datetime.fromisoformat(interview['start'].replace('Z', '+00:00'))
        
        message = f"""🎤 *Interview Reminder*

You have an interview coming up:
• *{interview['title']}*
• 📅 {start_time.strftime('%A, %B %d at %I:%M %p')}
• 📍 {interview.get('location', 'See calendar for details')}

*Quick Prep Checklist:*
□ Research recent company news
□ Review job description
□ Prepare questions to ask
□ Test video/audio
□ Have resume handy
"""
        
        # This would send via Slack
        print(message)
        return True
        
    except Exception as e:
        print(f"Error sending reminder: {e}")
        return False


if __name__ == "__main__":
    print("Interview Scheduler Module")
    print("="*50)
    
    print("\nGenerating available slots...")
    slots = generate_available_slots(days_ahead=7)
    
    if slots:
        print(f"\nFound {len(slots)} available slots:")
        print(format_slots_for_email(slots))
    else:
        print("\nNo calendar integration or no available slots found.")
    
    print("\nUpcoming interviews:")
    interviews = get_upcoming_interviews()
    if interviews:
        for interview in interviews:
            print(f"  - {interview['title']} at {interview['start']}")
    else:
        print("  No upcoming interviews scheduled.")
