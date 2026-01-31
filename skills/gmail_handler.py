"""
Gmail Integration Module for Job Application Assistant

Handles:
- Reading job-related emails (recruiter responses, interview requests)
- Parsing email content for actionable items
- Sending follow-up emails
- Detecting interview scheduling requests

Requires:
- GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET environment variables
- Google OAuth consent configured
"""
import os
import re
import json
import pickle
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Google API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("Google API libraries not installed. Run: pip install google-api-python-client google-auth-oauthlib")


# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
]

# Job-related email patterns
JOB_EMAIL_PATTERNS = {
    'interview_request': [
        r'interview',
        r'schedule.*call',
        r'phone screen',
        r'meet with',
        r'next.*step',
        r'would like to.*speak',
        r'availability',
    ],
    'rejection': [
        r'unfortunately',
        r'not.*moving forward',
        r'decided.*other candidate',
        r'not.*selected',
        r'position.*filled',
        r'will not.*proceed',
    ],
    'application_received': [
        r'application.*received',
        r'thank.*applying',
        r'confirmation.*application',
        r'successfully.*submitted',
    ],
    'offer': [
        r'pleased to offer',
        r'offer letter',
        r'job offer',
        r'extend.*offer',
    ],
}


def get_credentials() -> Optional[Credentials]:
    """
    Get valid Gmail API credentials, prompting for OAuth if needed.
    """
    if not GOOGLE_API_AVAILABLE:
        return None
    
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'gmail_token.pickle')
    credentials_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'gmail_credentials.json')
    
    # Check for existing token
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Check for credentials file or use environment variables
            if os.path.exists(credentials_path):
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            else:
                # Use environment variables
                client_id = os.environ.get('GMAIL_CLIENT_ID')
                client_secret = os.environ.get('GMAIL_CLIENT_SECRET')
                
                if not client_id or not client_secret:
                    print("ERROR: Gmail credentials not found.")
                    print("Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET environment variables")
                    return None
                
                client_config = {
                    "installed": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": ["http://localhost:8080/", "http://localhost/"]
                    }
                }
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            
            creds = flow.run_local_server(port=8080, open_browser=True)
        
        # Save credentials for future use
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    
    return creds


def get_gmail_service():
    """Get authenticated Gmail API service."""
    creds = get_credentials()
    if not creds:
        return None
    return build('gmail', 'v1', credentials=creds)


def classify_email(subject: str, body: str) -> Dict:
    """
    Classify an email based on job-related patterns.
    """
    text = f"{subject} {body}".lower()
    
    classifications = {
        'type': 'unknown',
        'confidence': 0,
        'requires_action': False,
        'action_type': None,
    }
    
    for email_type, patterns in JOB_EMAIL_PATTERNS.items():
        matches = sum(1 for p in patterns if re.search(p, text))
        confidence = matches / len(patterns)
        
        if confidence > classifications['confidence']:
            classifications['type'] = email_type
            classifications['confidence'] = confidence
    
    # Determine if action is required
    if classifications['type'] == 'interview_request':
        classifications['requires_action'] = True
        classifications['action_type'] = 'schedule_interview'
    elif classifications['type'] == 'offer':
        classifications['requires_action'] = True
        classifications['action_type'] = 'review_offer'
    
    return classifications


def extract_scheduling_info(body: str) -> Dict:
    """
    Extract scheduling information from an email body.
    """
    info = {
        'dates_mentioned': [],
        'times_mentioned': [],
        'meeting_link': None,
        'contact_name': None,
        'contact_email': None,
    }
    
    # Extract dates (various formats)
    date_patterns = [
        r'(\d{1,2}/\d{1,2}/\d{2,4})',
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}',
        r'(Monday|Tuesday|Wednesday|Thursday|Friday)\s*,?\s*(January|February|March|April|May|June|July|August|September|October|November|December)?\s*\d{1,2}',
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, body, re.IGNORECASE)
        info['dates_mentioned'].extend([m if isinstance(m, str) else ' '.join(m) for m in matches])
    
    # Extract times
    time_patterns = [
        r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)',
        r'(\d{1,2}\s*(?:AM|PM|am|pm))',
    ]
    
    for pattern in time_patterns:
        matches = re.findall(pattern, body)
        info['times_mentioned'].extend(matches)
    
    # Extract meeting links
    meeting_patterns = [
        r'(https?://[^\s]*zoom[^\s]*)',
        r'(https?://[^\s]*meet\.google[^\s]*)',
        r'(https?://[^\s]*teams\.microsoft[^\s]*)',
        r'(https?://calendly\.com/[^\s]*)',
    ]
    
    for pattern in meeting_patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            info['meeting_link'] = match.group(1)
            break
    
    return info


def get_job_emails(days_back: int = 7, max_results: int = 50) -> List[Dict]:
    """
    Fetch and classify job-related emails from the past N days.
    """
    service = get_gmail_service()
    if not service:
        return []
    
    # Calculate date range
    after_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
    
    # Search query for job-related emails
    query = f'after:{after_date} (subject:interview OR subject:application OR subject:position OR subject:opportunity OR subject:hiring OR from:recruiter OR from:talent OR from:hr)'
    
    try:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        emails = []
        
        for msg in messages:
            msg_data = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            
            # Extract headers
            headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
            
            # Extract body
            body = ''
            if 'parts' in msg_data['payload']:
                for part in msg_data['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        body = base64.urlsafe_b64decode(part['body'].get('data', '')).decode('utf-8', errors='ignore')
                        break
            elif 'body' in msg_data['payload']:
                body = base64.urlsafe_b64decode(msg_data['payload']['body'].get('data', '')).decode('utf-8', errors='ignore')
            
            # Classify email
            classification = classify_email(headers.get('Subject', ''), body)
            scheduling_info = extract_scheduling_info(body)
            
            emails.append({
                'id': msg['id'],
                'thread_id': msg_data['threadId'],
                'subject': headers.get('Subject', ''),
                'from': headers.get('From', ''),
                'date': headers.get('Date', ''),
                'snippet': msg_data.get('snippet', ''),
                'body': body[:1000],  # First 1000 chars
                'classification': classification,
                'scheduling_info': scheduling_info,
            })
        
        return emails
        
    except Exception as e:
        print(f"Error fetching emails: {e}")
        return []


def get_actionable_emails() -> List[Dict]:
    """
    Get emails that require action (interview requests, offers, etc.)
    """
    all_emails = get_job_emails()
    return [e for e in all_emails if e['classification']['requires_action']]


def send_follow_up(to_email: str, subject: str, body: str) -> bool:
    """
    Send a follow-up email.
    """
    service = get_gmail_service()
    if not service:
        return False
    
    try:
        message = MIMEMultipart()
        message['to'] = to_email
        message['subject'] = subject
        message.attach(MIMEText(body, 'plain'))
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        
        return True
        
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def generate_interview_response(email_data: Dict, available_times: List[str]) -> str:
    """
    Generate a professional response to an interview request.
    """
    sender_name = email_data.get('from', '').split('<')[0].strip()
    
    times_formatted = '\n'.join([f"  - {t}" for t in available_times])
    
    response = f"""Dear {sender_name if sender_name else 'Hiring Team'},

Thank you so much for reaching out regarding the interview opportunity. I am very excited about the possibility of joining your team.

I am available at the following times:
{times_formatted}

Please let me know which time works best for you, and I will confirm my availability.

If you need any additional information from me in the meantime, please don't hesitate to ask.

Thank you again for this opportunity. I look forward to speaking with you soon.

Best regards,
Deanna Wiley
(708) 265-8734
DeannaWileyCareers@gmail.com"""
    
    return response


def get_email_summary() -> Dict:
    """
    Get a summary of job-related emails for dashboard.
    """
    emails = get_job_emails(days_back=14)
    
    summary = {
        'total': len(emails),
        'interview_requests': 0,
        'rejections': 0,
        'applications_confirmed': 0,
        'offers': 0,
        'requires_action': [],
        'recent': emails[:5] if emails else [],
    }
    
    for email in emails:
        email_type = email['classification']['type']
        if email_type == 'interview_request':
            summary['interview_requests'] += 1
        elif email_type == 'rejection':
            summary['rejections'] += 1
        elif email_type == 'application_received':
            summary['applications_confirmed'] += 1
        elif email_type == 'offer':
            summary['offers'] += 1
        
        if email['classification']['requires_action']:
            summary['requires_action'].append({
                'subject': email['subject'],
                'from': email['from'],
                'action': email['classification']['action_type'],
            })
    
    return summary


def reply_to_email(message_id: str, body: str, reply_all: bool = False) -> bool:
    """
    Reply to an email by message ID.
    """
    service = get_gmail_service()
    if not service:
        return False
    
    try:
        # Get the original message
        original = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        headers = {h['name']: h['value'] for h in original['payload']['headers']}
        
        # Build reply
        reply = MIMEMultipart()
        reply['to'] = headers.get('Reply-To', headers.get('From', ''))
        reply['subject'] = 'Re: ' + headers.get('Subject', '').replace('Re: ', '')
        reply['In-Reply-To'] = headers.get('Message-ID', '')
        reply['References'] = headers.get('Message-ID', '')
        
        if reply_all and 'Cc' in headers:
            reply['cc'] = headers['Cc']
        
        reply.attach(MIMEText(body, 'plain'))
        raw = base64.urlsafe_b64encode(reply.as_bytes()).decode()
        
        service.users().messages().send(
            userId='me',
            body={'raw': raw, 'threadId': original['threadId']}
        ).execute()
        
        return True
        
    except Exception as e:
        print(f"Error replying to email: {e}")
        return False


def add_label(message_id: str, label_name: str) -> bool:
    """
    Add a label to an email. Creates label if it doesn't exist.
    """
    service = get_gmail_service()
    if not service:
        return False
    
    try:
        # Get or create label
        labels = service.users().labels().list(userId='me').execute().get('labels', [])
        label_id = None
        
        for label in labels:
            if label['name'].lower() == label_name.lower():
                label_id = label['id']
                break
        
        if not label_id:
            # Create the label
            new_label = service.users().labels().create(
                userId='me',
                body={'name': label_name, 'labelListVisibility': 'labelShow'}
            ).execute()
            label_id = new_label['id']
        
        # Add label to message
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'addLabelIds': [label_id]}
        ).execute()
        
        return True
        
    except Exception as e:
        print(f"Error adding label: {e}")
        return False


def archive_email(message_id: str) -> bool:
    """
    Archive an email (remove from inbox).
    """
    service = get_gmail_service()
    if not service:
        return False
    
    try:
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['INBOX']}
        ).execute()
        return True
    except Exception as e:
        print(f"Error archiving email: {e}")
        return False


def mark_as_read(message_id: str) -> bool:
    """
    Mark an email as read.
    """
    service = get_gmail_service()
    if not service:
        return False
    
    try:
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        return True
    except Exception as e:
        print(f"Error marking as read: {e}")
        return False


def mark_as_unread(message_id: str) -> bool:
    """
    Mark an email as unread.
    """
    service = get_gmail_service()
    if not service:
        return False
    
    try:
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'addLabelIds': ['UNREAD']}
        ).execute()
        return True
    except Exception as e:
        print(f"Error marking as unread: {e}")
        return False


def star_email(message_id: str) -> bool:
    """
    Star an email.
    """
    service = get_gmail_service()
    if not service:
        return False
    
    try:
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'addLabelIds': ['STARRED']}
        ).execute()
        return True
    except Exception as e:
        print(f"Error starring email: {e}")
        return False


def search_emails(query: str, max_results: int = 20) -> List[Dict]:
    """
    Search emails with a Gmail query.
    
    Example queries:
    - 'from:recruiter@company.com'
    - 'subject:interview'
    - 'is:unread newer_than:7d'
    - 'has:attachment from:hr'
    """
    service = get_gmail_service()
    if not service:
        return []
    
    try:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        emails = []
        
        for msg in messages:
            msg_data = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()
            
            headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
            
            emails.append({
                'id': msg['id'],
                'thread_id': msg_data['threadId'],
                'subject': headers.get('Subject', ''),
                'from': headers.get('From', ''),
                'date': headers.get('Date', ''),
                'snippet': msg_data.get('snippet', ''),
                'labels': msg_data.get('labelIds', []),
            })
        
        return emails
        
    except Exception as e:
        print(f"Error searching emails: {e}")
        return []


def get_email_by_id(message_id: str) -> Optional[Dict]:
    """
    Get full email details by ID.
    """
    service = get_gmail_service()
    if not service:
        return None
    
    try:
        msg_data = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
        
        # Extract body
        body = ''
        if 'parts' in msg_data['payload']:
            for part in msg_data['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(part['body'].get('data', '')).decode('utf-8', errors='ignore')
                    break
        elif 'body' in msg_data['payload']:
            body = base64.urlsafe_b64decode(msg_data['payload']['body'].get('data', '')).decode('utf-8', errors='ignore')
        
        return {
            'id': message_id,
            'thread_id': msg_data['threadId'],
            'subject': headers.get('Subject', ''),
            'from': headers.get('From', ''),
            'to': headers.get('To', ''),
            'date': headers.get('Date', ''),
            'body': body,
            'snippet': msg_data.get('snippet', ''),
            'labels': msg_data.get('labelIds', []),
        }
        
    except Exception as e:
        print(f"Error getting email: {e}")
        return None


if __name__ == "__main__":
    print("Gmail Handler - Job Application Assistant")
    print("="*50)
    
    if not GOOGLE_API_AVAILABLE:
        print("\nInstall required packages:")
        print("pip install google-api-python-client google-auth-oauthlib")
    else:
        print("\nFetching job-related emails...")
        summary = get_email_summary()
        
        print(f"\nEmail Summary (last 14 days):")
        print(f"  Total job emails: {summary['total']}")
        print(f"  Interview requests: {summary['interview_requests']}")
        print(f"  Application confirmations: {summary['applications_confirmed']}")
        print(f"  Rejections: {summary['rejections']}")
        print(f"  Offers: {summary['offers']}")
        
        if summary['requires_action']:
            print(f"\n⚠️ Emails requiring action:")
            for item in summary['requires_action']:
                print(f"  - {item['subject']} ({item['action']})")
        
        print("\n✅ Gmail integration ready!")
