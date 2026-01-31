"""
Job Application Assistant Skills Package
"""
from .job_search import search_all_jobs, save_jobs
from .filter_jobs import filter_jobs, get_filtered_jobs
from .tailor_resume import tailor_resume
from .write_cover_letter import write_cover_letter
from .slack_notify import send_job_summary, send_application_status
from .apply_job import apply_to_job, detect_application_platform
from .track_status import log_application, update_status, get_stats
from .job_boards import search_all_extended_boards
from .review_content import review_generated_content, get_improvement_suggestions
from .gmail_handler import (
    get_job_emails, get_email_summary, get_actionable_emails,
    search_emails, get_email_by_id, reply_to_email, send_follow_up,
    add_label, archive_email, mark_as_read, mark_as_unread, star_email
)
from .morning_rollup import send_morning_rollup, run_rollup, build_rollup_message
from .smart_scraper import SmartScraper, scrape_job_details, apply_to_job_full, load_created_accounts
from .slack_commands import send_resume_preview, process_slack_command, generate_resume_preview
from .slack_dashboard import send_dashboard, get_quick_stats, build_dashboard_blocks
from .interview_scheduler import generate_available_slots, create_interview_event, get_upcoming_interviews
from .job_history import (
    filter_new_jobs, mark_job_seen, mark_job_applied, mark_job_skipped,
    get_history_stats, is_job_seen, get_job_status
)

__all__ = [
    'search_all_jobs',
    'save_jobs',
    'filter_jobs',
    'get_filtered_jobs',
    'tailor_resume',
    'write_cover_letter',
    'send_job_summary',
    'send_application_status',
    'apply_to_job',
    'detect_application_platform',
    'log_application',
    'update_status',
    'get_stats',
    'search_all_extended_boards',
    'review_generated_content',
    'get_improvement_suggestions',
]
