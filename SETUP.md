# ClawdBot Job Assistant - Complete Setup Guide

## 🚀 Quick Start

This guide gets ClawdBot running from a fresh git clone.

### Prerequisites

- Python 3.8+
- Node.js (for some integrations)
- Git

---

## 1. Clone Repository

```bash
git clone <your-repo-url>
cd job-assistant
```

---

## 2. Install Dependencies

```bash
# Python packages
pip install -r requirements.txt

# Install Playwright browsers (required for auto-apply)
playwright install chromium

# Install additional packages for Supabase
pip install supabase
```

---

## 3. Environment Variables Setup

Create a `.env` file in the project root:

```bash
# Required Core
GROQ_API_KEY=your-groq-api-key
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key

# Optional (for extended features)
OPENROUTER_API_KEY=your-openrouter-key
ANTHROPIC_API_KEY=your-anthropic-key
SLACK_BOT_TOKEN=xoxb-your-slack-token
SLACK_APP_TOKEN=xapp-your-slack-token
GMAIL_EMAIL=your-email@gmail.com
GMAIL_PASSWORD=your-app-password

# CAPTCHA (for auto-apply)
CaptchaKey=your-2captcha-api-key

# Windows PowerShell alternative:
# Set these in User environment variables or PowerShell profile
```

### Getting API Keys

| Service | How to Get |
|---------|-------------|
| **Groq** | https://console.groq.com/keys (Free tier available) |
| **Supabase** | https://supabase.com/dashboard → Project → Settings → API |
| **OpenRouter** | https://openrouter.ai/keys |
| **2Captcha** | https://2captcha.com/ (for CAPTCHA solving) |

---

## 4. Supabase Database Setup

1. Create a new Supabase project
2. Run the migration files in order:

```sql
-- In Supabase SQL Editor, run these in order:

-- 1. Initial schema
-- Copy contents of: db/migrations/001_initial_schema.sql

-- 2. Fix RLS policies  
-- Copy contents of: db/migrations/002_fix_rls_policies.sql

-- 3. Fix security issues
-- Copy contents of: db/migrations/003_fix_security_issues.sql

-- 4. Fix cover letters schema
-- Copy contents of: db/migrations/004_fix_cover_letters_schema.sql

-- 5. Job queue system (optional)
-- Copy contents of: db/migrations/005_job_queue_system.sql
```

---

## 5. Configure Your Profile

Edit `config.yaml`:

```yaml
user:
  name: "Your Name"
  email: "your.email@gmail.com"
  phone: "(555) 123-4567"
  location: "Your City, State"
  linkedin: "https://linkedin.com/in/yourprofile"
  portfolio: "https://yourportfolio.com"

job_search:
  keywords: ["Product Designer", "UX Designer", "Brand Designer"]
  locations: ["Remote", "San Francisco", "New York"]
  exclude_keywords: ["entry level", "intern", "junior"]
  
llm:
  model: "llama-3.1-8b-instant"  # Groq model
  temperature: 0.7
  max_tokens: 2000
```

---

## 6. Add Your Resume

Edit `data/base_resume.txt` with your actual resume:

```
# Your Name
Your.Email@example.com | (555) 123-4567 | Your City, State

## EXPERIENCE

### Your Current Role
**Company** | City, State | Start Date - Present
- Your achievement 1 (with metrics)
- Your achievement 2 (with metrics)

## EDUCATION

### Your Degree
**University** | Graduation Year | GPA
```

---

## 7. Test the Setup

```bash
# Test database connection
python skills/test_supabase_connection.py

# Test resume generation
python skills/test_resume_generation.py

# Test job queue
python skills/job_queue_manager.py

# Test ClawdBot workflow
python skills/clawdbot_workflow.py
```

---

## 8. Run ClawdBot

### Interactive Mode
```bash
python skills/clawdbot_workflow.py
```

### Add Jobs to Queue
```python
from skills.job_queue_manager import clawdbot_add_job

# Add a job
clawdbot_add_job(
    url="https://boards.greenhouse.io/company/jobs/123456",
    title="Product Designer",
    company="Company Name"
)
```

### Apply to Jobs
```python
import asyncio
from skills.job_queue_manager import clawdbot_apply_next

# Apply to next job in queue
asyncio.run(clawdbot_apply_next())
```

---

## 9. Daily Automation (Optional)

Set up a cron job or Windows Task Scheduler:

```bash
# Run daily at 9 AM
0 9 * * * cd /path/to/job-assistant && python skills/morning_rollup.py
```

---

## 📁 Project Structure

```
job-assistant/
├── skills/                 # Core functionality
│   ├── job_queue_manager.py     # Job queue management
│   ├── clawdbot_workflow.py     # Conversational interface
│   ├── real_auto_apply.py       # Application automation
│   ├── document_generator.py    # Resume/CV generation
│   └── ...
├── data/                  # User data
│   ├── base_resume.txt         # Your resume template
│   └── applications/           # Generated documents
├── db/                    # Database schema
│   └── migrations/             # SQL migration files
├── config.yaml            # Configuration
├── requirements.txt       # Python dependencies
└── .env                   # Environment variables (create this)
```

---

## 🔧 Troubleshooting

### Common Issues

1. **"GROQ_API_KEY not set"**
   - Set the environment variable or add to .env file

2. **"Supabase connection failed"**
   - Verify SUPABASE_URL and SUPABASE_ANON_KEY
   - Check if migrations were run

3. **"Playwright not installed"**
   - Run: `playwright install chromium`

4. **"No submit button found"**
   - Some sites (LinkedIn) require manual submission
   - Use Greenhouse/Lever jobs for full automation

### Debug Mode

Add to your code:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 🤖 ClawdBot Commands

```python
# Queue management
clawdbot_get_queue()      # Show jobs in queue
clawdbot_get_stats()      # Show statistics

# Job operations
clawdbot_add_job(url, title, company)  # Add job
await clawdbot_apply_next()            # Apply to next job
await clawdbot_apply_all(5)            # Apply to 5 jobs
```

---

## 📊 What Gets Tracked

- Jobs found and filtered
- Applications submitted
- Resume/Cover letter versions
- Email confirmations
- Success/failure rates
- CAPTCHA solving stats

All data is stored in your Supabase project.

---

## 🚨 Important Notes

- **Never commit `.env`** or API keys to git
- **Generated PDFs** are in `data/applications/`
- **Screenshots** help debug failed applications
- **Some sites** (LinkedIn) require manual submission
- **CAPTCHA solving** may be needed for some forms

---

## 🆘 Need Help?

1. Check the logs in the `logs/` directory
2. Review the debug screenshots
3. Test with Greenhouse/Lever jobs first (easiest)
4. Join our Discord/Slack for support

---

**Happy job hunting with ClawdBot! 🎯**
