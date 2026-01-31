---
name: gmail-job-assistant
description: Gmail integration for job application management - read, reply, organize, and track job-related emails
metadata: {"clawdbot":{"emoji":"📧","requires":{"env":["GMAIL_CLIENT_ID","GMAIL_CLIENT_SECRET"]}}}
---

# Gmail Job Assistant

Full Gmail integration for managing job application emails. Uses OAuth 2.0 authentication.

## Setup (Already Done)

Gmail OAuth is configured. Token stored at:
```
C:\Users\deann\clawd\job-assistant\data\gmail_token.pickle
```

## Available Commands

### Read Emails

```python
# Get job-related emails summary
from gmail_handler import get_email_summary
summary = get_email_summary()
# Returns: interview_requests, rejections, offers, applications_confirmed

# Search emails with Gmail query
from gmail_handler import search_emails
emails = search_emails("from:recruiter subject:interview newer_than:7d")

# Get full email by ID
from gmail_handler import get_email_by_id
email = get_email_by_id("message_id_here")

# Get emails requiring action (interviews, offers)
from gmail_handler import get_actionable_emails
urgent = get_actionable_emails()
```

### Reply & Send

```python
# Reply to an email
from gmail_handler import reply_to_email
reply_to_email("message_id", "Thank you for the opportunity...")

# Send a new email
from gmail_handler import send_follow_up
send_follow_up("recruiter@company.com", "Following up on application", "Body text...")

# Generate interview response
from gmail_handler import generate_interview_response
response = generate_interview_response(email_data, ["Monday 2pm", "Tuesday 10am"])
```

### Organize Emails

```python
# Add a label
from gmail_handler import add_label
add_label("message_id", "Job Applications")

# Archive email
from gmail_handler import archive_email
archive_email("message_id")

# Mark as read/unread
from gmail_handler import mark_as_read, mark_as_unread
mark_as_read("message_id")

# Star important emails
from gmail_handler import star_email
star_email("message_id")
```

## Email Classification

The system automatically classifies job emails:
- **interview_request** - Contains scheduling info, meeting links
- **rejection** - "Unfortunately", "not moving forward"
- **application_received** - Confirmation emails
- **offer** - Job offers

## Gmail Query Examples

```
from:recruiter@company.com           # From specific sender
subject:interview                     # Subject contains
is:unread newer_than:7d              # Unread, last 7 days
has:attachment from:hr               # Has attachment from HR
label:job-applications               # By label
```

## Morning Rollup

Run daily summary:
```bash
cd C:\Users\deann\clawd\job-assistant
python -c "from skills.morning_rollup import run_rollup; run_rollup()"
```

Sends to Slack:
- Job application progress (applied, interviewed, etc.)
- Email summary (interview requests, offers)
- Emails needing action
- Follow-up reminders

## Scheduled Task

Morning rollup can be added to Windows Task Scheduler:
```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -Command `"cd C:\Users\deann\clawd\job-assistant; python -c 'from skills.morning_rollup import run_rollup; run_rollup()'`""
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00AM
Register-ScheduledTask -TaskName "JobAssistant-MorningRollup" -Action $action -Trigger $trigger
```
