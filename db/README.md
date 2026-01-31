# Supabase Backend Integration for ClawdBot

Complete backend storage and tracking system for job application automation.

## Overview & Goals

This integration provides:
- **Persistent storage** of all job application activity
- **Structured tracking** of every application attempt with full metadata
- **Analytics & reporting** for success rates and efficiency metrics
- **Scalable schema** designed for future enhancements

## Quick Start

```python
from supabase import get_db, JobData, ApplicationData

# Initialize client
db = get_db()

# Save a job
job_id = db.save_job(JobData(
    source='greenhouse',
    source_url='https://boards.greenhouse.io/company/jobs/123',
    title='Graphic Designer',
    company='Acme Inc',
    location='Remote'
))

# Track an application
app_id = db.create_application(ApplicationData(
    job_id=job_id,
    submission_method='auto'
))

# Mark as submitted
db.mark_application_submitted(app_id, confirmation_received=True)
```

---

## 1. Environment Variable Setup

### Required Variables

| Variable | Description | Where to Find |
|----------|-------------|---------------|
| `SUPABASE_URL` | Project URL | Dashboard > Settings > API > Project URL |
| `SUPABASE_ANON_KEY` | Public anonymous key | Dashboard > Settings > API > anon public |
| `SUPABASE_SERVICE_ROLE_KEY` | Admin key (optional) | Dashboard > Settings > API > service_role secret |

### Setup Methods

**PowerShell (Permanent)**:
```powershell
[Environment]::SetEnvironmentVariable("SUPABASE_URL", "https://xxxxx.supabase.co", "User")
[Environment]::SetEnvironmentVariable("SUPABASE_ANON_KEY", "your_anon_key", "User")
[Environment]::SetEnvironmentVariable("SUPABASE_SERVICE_ROLE_KEY", "your_service_key", "User")
```

**.env file** (in project root):
```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Key Selection Strategy

| Use Case | Key Type | Why |
|----------|----------|-----|
| Standard CRUD operations | `anon_key` | Respects RLS, safe for client code |
| User-scoped queries | `anon_key` | RLS filters by user automatically |
| Admin operations | `service_role_key` | Bypasses RLS for full access |
| Background cleanup jobs | `service_role_key` | Needs cross-user access |
| Analytics aggregation | `service_role_key` | Reads all data for reports |

---

## 2. Database Schema

### Core Tables

#### `users`
Stores ClawdBot user profiles.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Unique user identifier |
| email | TEXT | User email (unique) |
| full_name | TEXT | Display name |
| phone | TEXT | Phone number |
| location | TEXT | City, State |
| linkedin_url | TEXT | LinkedIn profile |
| portfolio_url | TEXT | Portfolio website |
| preferences | JSONB | User preferences (salary, remote, etc.) |
| created_at | TIMESTAMPTZ | Record creation time |

#### `jobs`
Job postings (deduplicated by URL).

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Unique job identifier |
| source | TEXT | linkedin, indeed, greenhouse, lever, etc. |
| source_url | TEXT | Original job URL (unique) |
| title | TEXT | Job title |
| company | TEXT | Company name |
| location | TEXT | Job location |
| job_type | TEXT | full-time, part-time, contract |
| remote_type | TEXT | remote, hybrid, onsite |
| salary_min/max | INTEGER | Salary range |
| description | TEXT | Full job description |
| raw_data | JSONB | Original scraped data |
| first_seen_at | TIMESTAMPTZ | When first discovered |
| is_active | BOOLEAN | Still accepting applications |

**Indexes**: source, company, title (trigram), location, source_url

#### `applications`
Each application attempt.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Unique application identifier |
| user_id | UUID (FK) | Reference to users |
| job_id | UUID (FK) | Reference to jobs |
| automation_run_id | UUID (FK) | Reference to automation_runs |
| resume_id | UUID (FK) | Resume version used |
| cover_letter_id | UUID (FK) | Cover letter used |
| match_score_id | UUID (FK) | AI match analysis |
| status | TEXT | pending, in_progress, submitted, failed, interview, offer |
| submission_method | TEXT | auto, manual, easy_apply |
| started_at | TIMESTAMPTZ | When application started |
| submitted_at | TIMESTAMPTZ | When successfully submitted |
| fields_filled | INTEGER | Number of fields filled |
| fields_failed | TEXT[] | Fields that failed to fill |
| confirmation_received | BOOLEAN | Got confirmation email |
| retry_count | INTEGER | Number of retry attempts |
| last_error | TEXT | Most recent error message |

**Indexes**: user_id, job_id, status, submitted_at

#### `resumes`
Resume versions with metadata.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Unique resume identifier |
| user_id | UUID (FK) | Owner |
| version_name | TEXT | e.g., "base", "tailored_design" |
| is_base | BOOLEAN | Is this the base resume |
| file_path | TEXT | Local file path |
| file_type | TEXT | pdf, docx, html |
| content_hash | TEXT | SHA256 for deduplication |
| tailored_for_job_id | UUID (FK) | If tailored for specific job |
| ai_modifications | JSONB | What AI changed |

#### `cover_letters`
Cover letter versions.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Unique identifier |
| user_id | UUID (FK) | Owner |
| job_id | UUID (FK) | Target job |
| content_text | TEXT | Full letter content |
| ai_generated | BOOLEAN | Generated by AI |
| ai_model_used | TEXT | Which model generated it |

#### `match_scores`
AI-generated job fit analysis.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Unique identifier |
| user_id | UUID (FK) | Owner |
| job_id | UUID (FK) | Target job |
| overall_score | DECIMAL | 0-100 match score |
| skills_match | DECIMAL | Skills alignment |
| matched_keywords | TEXT[] | Keywords found |
| missing_keywords | TEXT[] | Keywords missing |
| reasoning | TEXT | AI explanation |
| recommendation | TEXT | strong_apply, apply, maybe, skip |

#### `captcha_logs`
CAPTCHA encounter tracking.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Unique identifier |
| application_id | UUID (FK) | Parent application |
| captcha_type | TEXT | recaptcha_v2, funcaptcha, hcaptcha, etc. |
| site_key | TEXT | CAPTCHA site key |
| resolution_method | TEXT | 2captcha, human, bypass |
| solved | BOOLEAN | Successfully solved |
| solve_time_ms | INTEGER | Time to solve |
| cost_usd | DECIMAL | Cost if using service |

#### `automation_runs`
ClawdBot execution sessions.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Unique run identifier |
| user_id | UUID (FK) | Owner |
| run_type | TEXT | scheduled, manual, test |
| status | TEXT | running, completed, failed |
| started_at | TIMESTAMPTZ | When started |
| ended_at | TIMESTAMPTZ | When finished |
| jobs_found | INTEGER | Jobs discovered |
| jobs_applied | INTEGER | Successful applications |
| jobs_failed | INTEGER | Failed applications |

---

## 3. Row Level Security (RLS)

RLS ensures users can only access their own data.

### Policy Examples

**Jobs table** (publicly readable):
```sql
CREATE POLICY "Jobs are publicly readable" ON jobs
    FOR SELECT USING (true);
```

**Applications table** (user-scoped):
```sql
CREATE POLICY "Users can view own applications" ON applications
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own applications" ON applications
    FOR INSERT WITH CHECK (auth.uid() = user_id);
```

**Service role bypass**:
```sql
CREATE POLICY "Service role can manage all" ON applications
    FOR ALL USING (auth.role() = 'service_role');
```

### What Must Be Configured

1. **Enable RLS** on all tables: `ALTER TABLE tablename ENABLE ROW LEVEL SECURITY;`
2. **Create policies** for each operation (SELECT, INSERT, UPDATE, DELETE)
3. **Service role policies** for admin operations
4. **Test with anon key** to verify RLS is enforced

---

## 4. Client Strategy

### Client Instantiation

```python
from supabase import get_db, get_supabase_client, get_service_client

# Standard client (respects RLS)
db = get_db()

# Or get raw client
client = get_supabase_client()

# Admin client (bypasses RLS) - use carefully!
admin_client = get_service_client()
```

### Usage Patterns

| Context | Client Type | Example |
|---------|-------------|---------|
| Automation runner | Standard | `db = get_db()` |
| Slack bot handlers | Standard | `db = get_db(user_id)` |
| Background cleanup | Service | `admin = get_service_client()` |
| Analytics dashboard | Service | Full data access needed |
| Edge functions | Standard | Pass user context |

---

## 5. Workflow Scenarios

### Workflow 1: Save New Job

```python
from supabase.workflows import JobDiscoveryWorkflow

workflow = JobDiscoveryWorkflow()

# Process scraped job
job_id, is_new = workflow.process_job({
    'title': 'Graphic Designer',
    'company': 'Acme Inc',
    'job_url': 'https://...',
    'location': 'Remote',
    'description': '...'
})

if is_new:
    print(f"New job saved: {job_id}")
else:
    print(f"Job already exists: {job_id}")
```

### Workflow 2: Record Application

```python
from supabase.workflows import ApplicationWorkflow

workflow = ApplicationWorkflow()

# Start tracking
app_id = workflow.start_application(
    job_id=job_id,
    resume_path='/path/to/resume.pdf',
    cover_letter_text='Dear Hiring Manager...',
    match_score=85.5
)

# Update progress
workflow.update_form_progress(fields_filled=8, fields_total=10)

# On success
workflow.complete_success(confirmation_received=True)

# Or on failure
workflow.complete_failure(error="CAPTCHA timeout")
```

### Workflow 3: Log CAPTCHA

```python
workflow.log_captcha_encounter(
    captcha_type='funcaptcha',
    solved=True,
    resolution_method='2captcha',
    solve_time_ms=45000,
    cost=0.005
)
```

---

## 6. Analytics & Reporting

### Daily Report

```python
from supabase.workflows import AnalyticsWorkflow

analytics = AnalyticsWorkflow()
report = analytics.generate_daily_report()

# Returns:
# {
#     'date': '2026-01-31',
#     'applications': 5,
#     'successful': 4,
#     'failed': 1,
#     'success_rate': 80.0
# }
```

### Weekly Summary

```python
weekly = analytics.generate_weekly_report()

# Returns:
# {
#     'week_start': '2026-01-27',
#     'applications': 15,
#     'interviews': 2,
#     'top_sources': [{'source': 'greenhouse', 'applications': 8}],
#     'captcha_summary': {'total': 5, 'solved': 4, 'total_cost': 0.02}
# }
```

### Built-in Views

- `daily_application_stats` - Daily aggregations
- `weekly_summary` - Weekly summaries with interview counts
- `captcha_performance` - CAPTCHA success rates by type
- `job_source_stats` - Effectiveness by job board

---

## 7. Failure Handling

### Failure Cases Handled

| Case | Solution |
|------|----------|
| Failed writes | Retry with exponential backoff |
| Duplicate detection | Unique constraint on (user_id, job_id) |
| Timeouts | Log error, mark as failed, allow retry |
| Partial writes | Transaction-like workflow patterns |
| Stale runs | Cleanup job marks old "running" as failed |

### Retry Logic

```python
from supabase.workflows import FailureHandlingWorkflow

handler = FailureHandlingWorkflow()

# Get retryable applications
retryable = handler.get_retryable_applications(max_retries=3)

# Get error summary
errors = handler.get_error_summary(days=7)
# Returns top 10 error messages with counts

# Cleanup stale runs
cleaned = handler.cleanup_stale_runs(hours=24)
```

---

## 8. Migration Strategy

### Running Migrations

```bash
# Apply initial schema
psql $DATABASE_URL -f supabase/migrations/001_initial_schema.sql

# Or via Supabase CLI
supabase db push
```

### Adding New Fields

```sql
-- 002_add_field.sql
ALTER TABLE applications 
ADD COLUMN new_field TEXT;

-- Add index if needed
CREATE INDEX idx_applications_new_field ON applications(new_field);
```

### Schema Evolution Best Practices

1. **Always add nullable columns** or provide defaults
2. **Never delete columns** in production - deprecate first
3. **Use migrations** - never modify schema directly
4. **Version everything** - migrations numbered sequentially
5. **Test migrations** on copy of production data first

### Feature Toggles

Use the `metadata` JSONB columns for feature flags:

```python
# Store feature data
db.update_application(app_id, metadata={'feature_v2': True, 'ab_test': 'variant_a'})

# Query by feature
apps = db.client.table('applications')\
    .select('*')\
    .contains('metadata', {'feature_v2': True})\
    .execute()
```

---

## File Structure

```
job-assistant/supabase/
├── __init__.py          # Package exports
├── config.py            # Environment and client setup
├── client.py            # High-level SupabaseClient API
├── workflows.py         # Complete workflow implementations
├── README.md            # This documentation
└── migrations/
    └── 001_initial_schema.sql  # Database schema
```

---

## Testing

```bash
# Test configuration
python -m supabase.config

# Test client
python -m supabase.client

# Test workflows
python -m supabase.workflows
```
