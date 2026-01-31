---
name: smart-scraper
description: AI-powered adaptive web scraper for job applications with account creation, email verification, and form automation
metadata: {"clawdbot":{"emoji":"🕸️","requires":{"bins":["python3"],"env":[]}}}
---

# Smart Web Scraper for Job Applications

Adaptive Playwright-based scraper that can handle ANY job site, including:
- Sites requiring account creation
- Email verification flows
- Complex multi-step applications
- JavaScript-heavy SPAs
- Anti-bot protected sites

## Quick Start

```bash
cd C:\Users\deann\clawd\skills\job-search-automation

# Scrape job details from any URL
python cli.py scrape --url "https://www.linkedin.com/jobs/view/123456"

# Apply to a job (opens browser, fills forms)
python cli.py apply --url "https://company.com/jobs/123" --resume "C:\path\to\resume.pdf"

# View stored accounts created on job sites
python cli.py accounts
```

## Features

### 1. Smart Form Filling
Automatically detects and fills form fields:
- First/Last name
- Email, phone
- LinkedIn, portfolio URLs
- Location, salary expectations
- Work authorization
- Education details

### 2. Account Creation
When a job site requires an account:
1. Detects signup requirement
2. Creates account with user's email
3. Generates secure password
4. Saves credentials to `data/created_accounts.json`

### 3. Email Verification
If email verification is needed:
1. Monitors Gmail for verification emails
2. Extracts verification link
3. Clicks link automatically
4. Returns to application

### 4. Anti-Detection
Built-in stealth measures:
- Realistic user agent
- Human-like typing delays
- Proper viewport/timezone
- WebDriver flag masking
- Session persistence

## Direct Python Usage

```python
import asyncio
from smart_scraper import SmartScraper, scrape_job_details, apply_to_job_full

# Scrape job details
job_data = asyncio.run(scrape_job_details("https://example.com/job/123"))
print(job_data)

# Full application workflow
result = asyncio.run(apply_to_job_full(
    "https://example.com/job/123",
    resume_path="C:/path/to/resume.pdf"
))
print(result['status'])  # 'ready_to_submit'
print(result['steps_completed'])  # ['navigated', 'filled_form', 'uploaded_resume']
```

## Stored Accounts

View all accounts created on job sites:
```bash
python cli.py accounts
```

Output:
```
=== Stored Job Site Accounts ===

greenhouse.io:
  Email: DeannaWileyCareers@gmail.com
  Password: DwAbc123Xyz!2026
  Created: 2026-01-30T10:15:30

lever.co:
  Email: DeannaWileyCareers@gmail.com
  Password: DwDef456Uvw!2026
  Created: 2026-01-30T11:20:45
```

## User Data

The scraper uses Deanna's profile from `smart_scraper.py`:
- Name: Deanna Wiley
- Email: DeannaWileyCareers@gmail.com
- Phone: (708) 265-8734
- LinkedIn: linkedin.com/in/deannafwiley/
- Portfolio: dwileydesign.myportfolio.com/
- Location: Alameda, CA

## Clawdbot Integration

Ask Clawdbot in Slack:
- "Scrape this job posting: [URL]"
- "Apply to this job: [URL]"
- "Show my job site accounts"
- "Fill out the application at [URL]"

## Troubleshooting

### Browser won't start
```bash
playwright install chromium
```

### Form not filling correctly
The scraper uses pattern matching. If a field isn't detected:
1. Check the field's name/id/placeholder
2. Add pattern to `FIELD_PATTERNS` in `smart_scraper.py`

### Email verification timeout
- Check Gmail is authenticated
- Verify the job site sent the email
- Increase `max_wait_seconds` parameter
