# Job Assistant Skill

## Overview
Complete job application automation system with Playwright-based form filling, document generation, and CAPTCHA handling.

## Location
```
C:\Users\deann\clawd\job-assistant\skills\
```

## Primary Tools

### 1. Auto Apply (`real_auto_apply.py`)
Full end-to-end job application flow.

```python
import asyncio
import sys
sys.path.insert(0, 'C:/Users/deann/clawd/job-assistant/skills')
from real_auto_apply import auto_apply_to_job

result = await auto_apply_to_job(
    job_url='https://jobs.lever.co/company/job-id',
    job_title='Job Title',
    company='Company Name',
    job_description='Description text'
)
# Returns: {"success": True, "state": "success", "fields_filled": 6}
```

### 2. Document Generator (`document_generator.py`)
Generates tailored resume and cover letter PDFs.

```python
from document_generator import generate_application_documents

docs = generate_application_documents(job_title, company, job_description)
# Creates PDF, DOCX, HTML files in data/applications/
```

### 3. Playwright Engine (`playwright_automation.py`)
Low-level automation with semantic DOM analysis.

```python
from playwright_automation import ApplicationEngine

engine = ApplicationEngine(user_data, captcha_key)
result = await engine.apply(job_url, job_title, company, resume_path, cover_letter_path)
```

## User Data
```python
user_data = {
    'first_name': 'Deanna',
    'last_name': 'Wiley',
    'email': 'DeannaWileyCareers@gmail.com',
    'phone': '708-265-8734',
    'linkedin': 'https://www.linkedin.com/in/deannafwiley/',
    'portfolio': 'https://dwileydesign.myportfolio.com/',
}
```

## Environment Variables
- `OPENROUTER_API_KEY` - AI document generation
- `CaptchaKey` - 2Captcha API (optional)

## Tested Platforms
- ✅ Lever (lever.co)
- ✅ Greenhouse (greenhouse.io)

## Features
- Semantic form field detection
- Intelligent field value mapping
- Resume/cover letter PDF upload
- CAPTCHA detection with human fallback
- Closed job detection (404, expired)
- Success page verification
- Screenshot capture

## Config
See `job-assistant/config.yaml` for settings.
