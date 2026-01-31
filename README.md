# ClawdBot Job Assistant

🤖 An AI-powered job application system that automates job searching, resume/cover letter tailoring, and autonomous applications with full database tracking.

## ✨ Features

- **🔍 Job Sourcing**: Scrapes jobs from LinkedIn, Indeed, Glassdoor, Greenhouse, Lever, and more
- **🎯 AI Tailoring**: Uses Groq LLM to customize resumes and cover letters for each job
- **🤖 Autonomous Applications**: Fully automated job submissions with queue management
- **📊 Database Tracking**: Complete Supabase backend for jobs, applications, resumes, and analytics
- **📧 Email Confirmations**: Gmail integration for application confirmation tracking
- **🔐 CAPTCHA Handling**: Automated CAPTCHA solving for complex forms
- **💬 Conversational Interface**: Natural language commands via ClawdBot workflow

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/DeannaWiley/clawdbot-job-assistant.git
cd clawdbot-job-assistant
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# Required:
#   GROQ_API_KEY
#   SUPABASE_URL
#   SUPABASE_ANON_KEY
```

### 4. Database Setup

Run these SQL files in Supabase SQL Editor (in order):
1. `db/migrations/001_initial_schema.sql`
2. `db/migrations/002_fix_rls_policies.sql`
3. `db/migrations/003_fix_security_issues.sql`
4. `db/migrations/004_fix_cover_letters_schema.sql`
5. `db/migrations/005_job_queue_system.sql`

### 5. Configure Profile

Edit `config.yaml` with your personal info and job preferences.

## 📖 Usage

### Interactive ClawdBot Mode

```bash
python skills/clawdbot_workflow.py
```

Commands:
- `"show queue"` - View jobs waiting to apply
- `"show stats"` - Get queue statistics
- `"apply next"` - Apply to next job in queue
- `"apply all"` - Apply to multiple jobs
- `"add [URL]"` - Add job URL to queue

### Job Queue Management

```python
from skills.job_queue_manager import *

# Add job to queue
clawdbot_add_job(url, title, company)

# Apply to next job
import asyncio
asyncio.run(clawdbot_apply_next())

# View queue
clawdbot_get_queue()
```

### Document Generation

```python
from skills.document_generator import generate_application_documents

# Generate tailored resume and cover letter
result = generate_application_documents(
    job_url="https://boards.greenhouse.io/company/jobs/123456",
    job_title="Product Designer",
    company_name="Company"
)
```

### Autonomous Application

```python
from skills.real_auto_apply import auto_apply_to_job

# Apply to job with full automation
result = await auto_apply_to_job(
    job_url,
    job_title,
    company_name,
    job_description
)
```

## 🏗️ Project Structure

```
clawdbot-job-assistant/
├── 📄 README.md              # This file
├── 📄 SETUP.md               # Complete setup guide
├── 📄 .env.example           # Environment variables template
├── 📄 .gitignore             # Excludes sensitive data
├── 📄 requirements.txt        # Python dependencies
├── ⚙️ config.yaml            # Configuration settings
├── 📂 data/                  # User data
│   ├── 📝 base_resume.txt     # Your resume template
│   └── 📂 applications/       # Generated documents
├── 📂 skills/                 # Core functionality (50+ modules)
│   ├── 🤖 clawdbot_workflow.py     # Conversational interface
│   ├── 📋 job_queue_manager.py     # Queue management
│   ├── 🚀 real_auto_apply.py       # Application automation
│   ├── 📄 document_generator.py    # Resume/CV generation
│   ├── 🎨 tailor_resume.py         # AI resume tailoring
│   ├── 📝 write_cover_letter.py    # AI cover letters
│   ├── 🤖 captcha_handler.py       # CAPTCHA solving
│   ├── 📧 gmail_handler.py         # Email tracking
│   └── 🎭 playwright_automation.py # Browser automation
├── 📂 db/                    # Database schema
│   └── 📂 migrations/             # SQL migration files
└── 🚀 main.py                # Entry point
```

## 🔧 API Keys Required

| Service | Purpose | How to Get |
|---------|---------|-------------|
| **Groq** | LLM for resume/cover letters | https://console.groq.com/keys (Free) |
| **Supabase** | Database backend | https://supabase.com/dashboard |
| **2Captcha** | CAPTCHA solving | https://2captcha.com/ |
| **OpenRouter** | Alternative LLM | https://openrouter.ai/keys |
| **Slack** | Notifications | https://api.slack.com/apps |

## 📊 What Gets Tracked

- ✅ Jobs found and filtered
- ✅ Applications submitted (with status)
- ✅ Resume/Cover letter versions
- ✅ Email confirmations received
- ✅ Success/failure rates
- ✅ CAPTCHA solving statistics
- ✅ Form field completion rates

## 🎯 Supported Job Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| **Greenhouse** | ✅ Full automation | Best support |
| **Lever** | ✅ Full automation | Excellent |
| **Workday** | ⚠️ Partial | Some forms work |
| **LinkedIn** | ❌ Manual only | Requires login |
| **Indeed** | ⚠️ Limited | Varies by site |
| **Company Sites** | ⚠️ Varies | Case by case |

## 🔒 Security Features

- **No API keys in repo** - Use `.env` file
- **Row Level Security** - Supabase RLS policies
- **CAPTCHA handling** - Automated solving
- **Form validation** - Prevents bad submissions
- **Email verification** - Tracks confirmations

## 🛠️ Advanced Features

### Custom Prompts

Edit `skills/enhanced_prompts.py` to customize:
- Resume tailoring prompts
- Cover letter styles
- Scam detection rules
- Match scoring algorithms

### Browser Automation

Configure `skills/playwright_automation.py`:
- Custom selectors
- Wait strategies
- Error handling
- Screenshot debugging

### Database Extensions

Add new tables/views in `db/migrations/`:
- Custom analytics
- Additional tracking
- User preferences
- API integrations

## 🐛 Troubleshooting

### Common Issues

```bash
# Test database connection
python skills/test_supabase_connection.py

# Test resume generation
python skills/test_resume_generation.py

# Test job queue
python skills/job_queue_manager.py

# Check Playwright
playwright install chromium
```

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Logs Location

- Application logs: `logs/`
- Screenshots: `data/applications/*_screenshot.png`
- Debug images: `data/captcha/`

## 📈 Performance Tips

1. **Use Groq** - Faster and free vs OpenRouter
2. **Greenhouse/Lever** - Best automation success rates
3. **Queue jobs** - Batch process overnight
4. **Monitor CAPTCHA** - Check solve rates
5. **Email confirmations** - Verify submissions

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Add tests for new features
4. Submit pull request

## 📄 License

MIT License - Use freely for personal job hunting!

## 🆘 Support

- 📖 Check `SETUP.md` for detailed guide
- 🐛 Issues: GitHub Issues
- 💬 Discord: [Join our community]
- 📧 Email: deannawiley.careers@gmail.com

---

**Built with ❤️ by Deanna Wiley**

🎯 **Happy job hunting with ClawdBot!**
