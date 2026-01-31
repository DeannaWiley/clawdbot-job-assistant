# Job Application Assistant Skills

A comprehensive job search and application automation system for Clawdbot.

## Available Commands

### Job Search
- `python main.py` - Run full daily workflow (search, filter, tailor, notify)
- `python main.py --search-only` - Only search and filter jobs
- `python main.py --status` - Show application status report
- `python main.py --max-jobs 5` - Process only top 5 matches

### Individual Skills

#### job_search.py
Search for jobs across multiple boards (LinkedIn, Indeed, Glassdoor, Google Jobs).

#### job_boards.py  
Extended job board scrapers (Ashby, Wellfound, WeWorkRemotely, RemoteOK, Greenhouse, Lever).

#### filter_jobs.py
Filter out scams, deal-breakers, and low-quality listings.

#### job_history.py
Track seen/applied/skipped jobs to prevent duplicate notifications.

#### tailor_resume.py
AI-powered resume tailoring for each job using OpenRouter LLM.

#### write_cover_letter.py
AI-generated cover letters customized per job.

#### review_content.py
Validate AI-generated content for hallucinations and ATS compliance.

#### slack_notify.py
Send job summaries to Slack with Approve/Skip buttons.

#### slack_dashboard.py
Interactive Slack dashboard with stats and settings.

#### apply_job.py
Automated application submission (LinkedIn Easy Apply, Greenhouse).

#### track_status.py
Log and track all application statuses.

#### gmail_handler.py
Monitor Gmail for recruiter responses and interview requests.

#### interview_scheduler.py
Calendar integration for scheduling interviews.

## Configuration
Edit `config.yaml` to customize:
- Job search keywords and locations
- Salary requirements ($60K-$100K)
- Deal-breakers (Part-time, Internship, etc.)
- Daily application target (2-5 recommended)

## Data Files
- `data/base_resume.txt` - Your base resume
- `data/all_resumes.txt` - All resume versions extracted
- `data/job_history.json` - Seen/applied/skipped jobs
- `data/applications_log.csv` - Detailed application tracking
