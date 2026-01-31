# 🚀 Quick Start Guide

Get ClawdBot running in 5 minutes!

## 1️⃣ Clone & Install

```bash
git clone https://github.com/DeannaWiley/clawdbot-job-assistant.git
cd clawdbot-job-assistant
pip install -r requirements.txt
playwright install chromium
```

## 2️⃣ Environment Setup

```bash
# Copy template
cp .env.example .env

# Edit .env (minimum required):
GROQ_API_KEY=gsk_your_key_here
SUPABASE_URL=https://your_project.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
```

### Get API Keys:
- **Groq**: https://console.groq.com/keys (Free)
- **Supabase**: https://supabase.com/dashboard → New Project

## 3️⃣ Database Setup

In Supabase SQL Editor, run:
```sql
-- Copy contents of these files in order:
-- db/migrations/001_initial_schema.sql
-- db/migrations/002_fix_rls_policies.sql  
-- db/migrations/003_fix_security_issues.sql
-- db/migrations/004_fix_cover_letters_schema.sql
-- db/migrations/005_job_queue_system.sql
```

## 4️⃣ Configure Profile

Edit `config.yaml`:
```yaml
user:
  name: "Your Name"
  email: "your.email@gmail.com"
  phone: "(555) 123-4567"
  location: "Your City, State"
```

## 5️⃣ Add Your Resume

Edit `data/base_resume.txt` with your resume content.

## 6️⃣ Test It!

```bash
# Test database
python skills/test_supabase_connection.py

# Test resume generation
python skills/test_resume_generation.py

# Test job queue
python skills/job_queue_manager.py
```

## 7️⃣ Run ClawdBot

```bash
# Interactive mode
python skills/clawdbot_workflow.py

# Commands:
# "show queue" - View jobs
# "add [URL]" - Add job
# "apply next" - Apply to job
```

## 🎯 That's it!

ClawdBot is ready to:
- ✅ Generate tailored resumes
- ✅ Write custom cover letters  
- ✅ Apply to jobs automatically
- ✅ Track everything in database

---

**Need help?** See `SETUP.md` for detailed instructions.
