# Job Application Assistant

An AI-powered job application workflow that automates job searching, filtering, resume/cover letter tailoring, and application tracking via Slack.

## Features

- **Job Sourcing**: Scrapes jobs from LinkedIn, Indeed, Glassdoor, and Google Jobs using JobSpy
- **Scam Filtering**: Automatically filters out scam postings and low-quality listings
- **AI Tailoring**: Uses Claude/GPT via OpenRouter to customize resumes and cover letters for each job
- **Slack Integration**: Daily job summaries with approval buttons directly in Slack DMs
- **Application Tracking**: Logs all applications with status tracking and follow-up reminders

## Setup

### 1. Install Dependencies

```bash
cd job-assistant
pip install -r requirements.txt

# Install Playwright browsers (for auto-apply features)
playwright install chromium
```

### 2. Configure Environment Variables

Set these environment variables:

```bash
# Required
export OPENROUTER_API_KEY="your-openrouter-api-key"
export SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"
export SLACK_APP_TOKEN="xapp-your-slack-app-token"

# Windows (PowerShell)
$env:OPENROUTER_API_KEY = "your-openrouter-api-key"
```

### 3. Configure Your Profile

Edit `config.yaml`:
- Add your personal info (name, email, phone)
- Customize job search keywords and locations
- Adjust filtering settings

### 4. Add Your Resume

Edit `data/base_resume.txt` with your actual resume content.

## Usage

### Run Daily Workflow

```bash
python main.py
```

This will:
1. Search for jobs matching your criteria
2. Filter out scams and irrelevant listings
3. Tailor your resume and cover letter for each job
4. Send a summary to Slack with Approve/Skip buttons

### Search Only (No Slack)

```bash
python main.py --search-only
```

### View Application Status

```bash
python main.py --status
```

### Limit Jobs Processed

```bash
python main.py --max-jobs 5
```

## Project Structure

```
job-assistant/
├── main.py                 # Main orchestrator
├── config.yaml             # Configuration
├── requirements.txt        # Dependencies
├── skills/
│   ├── job_search.py       # Job aggregation from multiple sources
│   ├── filter_jobs.py      # Scam detection and filtering
│   ├── tailor_resume.py    # AI resume customization
│   ├── write_cover_letter.py # AI cover letter generation
│   ├── slack_notify.py     # Slack notifications and approvals
│   ├── apply_job.py        # Automated application submission
│   └── track_status.py     # Application logging and tracking
├── data/
│   ├── base_resume.txt     # Your base resume
│   └── applied_jobs.csv    # Application log
└── templates/              # Document templates
```

## Slack Workflow

1. **Daily Summary**: Each morning, receive a Slack DM with job matches
2. **Review**: Each job shows title, company, location, and match score
3. **Approve**: Click to apply (documents are pre-tailored)
4. **Skip**: Click to dismiss the job
5. **Preview**: View tailored resume/cover letter before applying

## Safety Features

- **No auto-apply without approval**: Every application requires manual confirmation
- **Scam detection**: Filters out suspicious postings automatically
- **Trusted sources only**: Only processes jobs from verified job boards
- **Credential safety**: Never logs or exposes sensitive credentials

## Customization

### Adding New Job Categories

Edit `config.yaml` under `search.categories`:

```yaml
categories:
  new_category:
    keywords:
      - "Keyword 1"
      - "Keyword 2"
    required_skills:
      - "Skill 1"
```

### Adjusting Scam Filters

Edit `config.yaml` under `filtering.scam_keywords` to add/remove red flag phrases.

## Integration with Clawdbot

This assistant is designed to work with Clawdbot (Moltbot). To run via Clawdbot:

1. Ensure Clawdbot gateway is running
2. The skills can be registered as Clawdbot skills
3. Slack interactions are handled via Clawdbot's Slack plugin

## Troubleshooting

### No jobs found
- Check your search keywords in config.yaml
- Verify JobSpy is working: `python -c "from jobspy import scrape_jobs; print('OK')"`

### Slack not sending
- Verify SLACK_BOT_TOKEN and SLACK_APP_TOKEN are set
- Check bot has required permissions (chat:write, im:write)

### LLM errors
- Verify OPENROUTER_API_KEY is set and valid
- Check you have credits on OpenRouter

## License

MIT License - Use freely for personal job hunting!
