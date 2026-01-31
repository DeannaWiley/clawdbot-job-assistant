"""
Supabase Workflow Implementations for ClawdBot
===============================================

Complete workflow functions that integrate with the automation system.
These functions handle the full lifecycle of job tracking.

Workflows:
1. New Job Discovery - Save job when first seen
2. Application Attempt - Full application with all metadata
3. CAPTCHA Resolution - Log CAPTCHA encounters and solutions
4. Email Tracking - Process confirmation emails
5. Analytics Generation - Build reports and metrics
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from .client import SupabaseClient, JobData, ApplicationData, get_db


class JobDiscoveryWorkflow:
    """
    Workflow: Save a new job posting when first seen.
    
    Steps:
    1. Check if job URL already exists
    2. Parse job details from scraped data
    3. Insert or update job record
    4. Return job_id for further processing
    """
    
    def __init__(self, db: SupabaseClient = None):
        self.db = db or get_db()
    
    def process_job(self, raw_job: Dict) -> Tuple[str, bool]:
        """
        Process a scraped job posting.
        
        Args:
            raw_job: Raw job data from scraper
            
        Returns:
            Tuple of (job_id, is_new)
        """
        # Determine source from URL
        url = raw_job.get('job_url', raw_job.get('url', ''))
        source = self._detect_source(url)
        
        # Check if already exists
        existing = self.db.get_job_by_url(url)
        if existing:
            return existing['id'], False
        
        # Parse job data
        job = JobData(
            source=source,
            source_url=url,
            title=raw_job.get('title', 'Unknown Position'),
            company=raw_job.get('company', 'Unknown Company'),
            location=raw_job.get('location'),
            job_type=raw_job.get('job_type'),
            remote_type=self._detect_remote_type(raw_job),
            salary_min=self._parse_salary(raw_job.get('min_amount')),
            salary_max=self._parse_salary(raw_job.get('max_amount')),
            description=raw_job.get('description'),
            raw_data=raw_job
        )
        
        job_id = self.db.save_job(job)
        return job_id, True
    
    def _detect_source(self, url: str) -> str:
        """Detect job source from URL."""
        url_lower = url.lower()
        
        if 'linkedin.com' in url_lower:
            return 'linkedin'
        elif 'indeed.com' in url_lower:
            return 'indeed'
        elif 'glassdoor.com' in url_lower:
            return 'glassdoor'
        elif 'greenhouse.io' in url_lower or 'boards.greenhouse' in url_lower:
            return 'greenhouse'
        elif 'lever.co' in url_lower or 'jobs.lever' in url_lower:
            return 'lever'
        elif 'workday.com' in url_lower or 'myworkdayjobs' in url_lower:
            return 'workday'
        else:
            return 'company_site'
    
    def _detect_remote_type(self, job: Dict) -> Optional[str]:
        """Detect if job is remote, hybrid, or onsite."""
        text = f"{job.get('title', '')} {job.get('location', '')} {job.get('description', '')}".lower()
        
        if 'remote' in text:
            if 'hybrid' in text:
                return 'hybrid'
            return 'remote'
        elif 'hybrid' in text:
            return 'hybrid'
        elif 'on-site' in text or 'onsite' in text or 'in-office' in text:
            return 'onsite'
        
        return None
    
    def _parse_salary(self, value: Any) -> Optional[int]:
        """Parse salary value to integer."""
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                return int(value)
            # Remove currency symbols and commas
            cleaned = str(value).replace('$', '').replace(',', '').strip()
            return int(float(cleaned))
        except (ValueError, TypeError):
            return None


class ApplicationWorkflow:
    """
    Workflow: Record a complete application attempt.
    
    Steps:
    1. Check for duplicate applications
    2. Create application record (status: in_progress)
    3. Save resume version used
    4. Save cover letter generated
    5. Save match score analysis
    6. Log form fields filled
    7. Update status on completion
    8. Log any CAPTCHA encounters
    """
    
    def __init__(self, db: SupabaseClient = None):
        self.db = db or get_db()
        self._current_app_id = None
    
    def start_application(
        self,
        job_id: str,
        resume_path: Optional[str] = None,
        cover_letter_text: Optional[str] = None,
        match_score: Optional[float] = None,
        match_reasoning: Optional[str] = None
    ) -> Optional[str]:
        """
        Start tracking an application attempt.
        
        Returns:
            Application ID or None if duplicate
        """
        # Check for duplicate
        if self.db.check_already_applied(job_id):
            print(f"⚠️ Already applied to this job")
            return None
        
        # Save resume if provided
        resume_id = None
        if resume_path and os.path.exists(resume_path):
            job = self.db.get_job(job_id)
            version_name = f"{job['company']}_{job['title']}"[:50] if job else "unknown"
            resume_id = self.db.save_resume(
                version_name=version_name,
                file_path=resume_path,
                tailored_for_job_id=job_id
            )
        
        # Save cover letter if provided
        cover_letter_id = None
        if cover_letter_text:
            cover_letter_id = self.db.save_cover_letter(
                job_id=job_id,
                content_text=cover_letter_text
            )
        
        # Save match score if provided
        match_score_id = None
        if match_score is not None:
            match_score_id = self.db.save_match_score(
                job_id=job_id,
                overall_score=match_score,
                reasoning=match_reasoning
            )
        
        # Create application record
        app = ApplicationData(
            job_id=job_id,
            resume_id=resume_id,
            cover_letter_id=cover_letter_id,
            match_score_id=match_score_id,
            submission_method='auto'
        )
        
        self._current_app_id = self.db.create_application(app)
        return self._current_app_id
    
    def update_form_progress(
        self,
        fields_filled: int,
        fields_total: int,
        fields_failed: Optional[List[str]] = None
    ) -> None:
        """Update form filling progress."""
        if self._current_app_id:
            self.db.update_application(
                self._current_app_id,
                fields_filled=fields_filled,
                fields_failed=fields_failed
            )
    
    def complete_success(
        self,
        confirmation_received: bool = False,
        screenshot_path: Optional[str] = None
    ) -> None:
        """Mark application as successfully submitted."""
        if self._current_app_id:
            self.db.mark_application_submitted(
                self._current_app_id,
                confirmation_received=confirmation_received
            )
            
            if screenshot_path:
                self.db.update_application(
                    self._current_app_id,
                    metadata={'success_screenshot': screenshot_path}
                )
    
    def complete_failure(
        self,
        error: str,
        screenshot_path: Optional[str] = None,
        retry: bool = False
    ) -> None:
        """Mark application as failed."""
        if self._current_app_id:
            if retry:
                # Increment retry count instead of marking failed
                self.db.update_application(
                    self._current_app_id,
                    last_error=error,
                    retry_count=1  # Will be incremented
                )
            else:
                self.db.mark_application_failed(
                    self._current_app_id,
                    error=error,
                    screenshot_path=screenshot_path
                )
    
    def log_captcha_encounter(
        self,
        captcha_type: str,
        solved: bool,
        resolution_method: Optional[str] = None,
        solve_time_ms: Optional[int] = None,
        cost: Optional[float] = None,
        error: Optional[str] = None
    ) -> None:
        """Log a CAPTCHA encounter during this application."""
        if self._current_app_id:
            self.db.log_captcha(
                application_id=self._current_app_id,
                captcha_type=captcha_type,
                solved=solved,
                resolution_method=resolution_method,
                solve_time_ms=solve_time_ms,
                cost_usd=cost,
                error_message=error
            )


class AnalyticsWorkflow:
    """
    Workflow: Generate analytics and reports.
    
    Provides methods for:
    - Daily/weekly/monthly summaries
    - Success rate calculations
    - Source effectiveness analysis
    - CAPTCHA cost tracking
    """
    
    def __init__(self, db: SupabaseClient = None):
        self.db = db or get_db()
    
    def generate_daily_report(self) -> Dict:
        """Generate a daily activity report."""
        stats = self.db.get_daily_stats(days=1)
        today = stats[0] if stats else {}
        
        success_rate = self.db.get_success_rate(days=1)
        
        return {
            'date': datetime.now().date().isoformat(),
            'applications': today.get('total_applications', 0),
            'successful': today.get('successful', 0),
            'failed': today.get('failed', 0),
            'interviews': today.get('interviews', 0),
            'success_rate': success_rate.get('success_rate', 0),
            'avg_form_completion': today.get('avg_form_completion', 0)
        }
    
    def generate_weekly_report(self) -> Dict:
        """Generate a weekly summary report."""
        weekly = self.db.get_weekly_summary(weeks=1)
        week = weekly[0] if weekly else {}
        
        success_rate = self.db.get_success_rate(days=7)
        source_stats = self.db.get_job_source_stats()
        captcha_stats = self.db.get_captcha_performance()
        
        return {
            'week_start': week.get('week_start'),
            'applications': week.get('applications_submitted', 0),
            'interviews': week.get('interviews', 0),
            'offers': week.get('offers', 0),
            'unique_companies': week.get('unique_companies', 0),
            'avg_match_score': week.get('avg_match_score', 0),
            'success_rate': success_rate,
            'top_sources': source_stats[:3] if source_stats else [],
            'captcha_summary': {
                'total': sum(c.get('total_attempts', 0) for c in captcha_stats),
                'solved': sum(c.get('solved', 0) for c in captcha_stats),
                'total_cost': sum(c.get('total_cost', 0) or 0 for c in captcha_stats)
            }
        }
    
    def get_efficiency_metrics(self, days: int = 30) -> Dict:
        """Calculate efficiency metrics."""
        history = self.db.get_application_history(days=days)
        
        if not history:
            return {'efficiency': 0, 'avg_fields_per_app': 0}
        
        total_apps = len(history)
        successful = sum(1 for h in history if h.get('status') == 'submitted')
        total_fields = sum(h.get('fields_filled', 0) for h in history)
        
        return {
            'total_applications': total_apps,
            'successful_applications': successful,
            'efficiency': round(successful / total_apps * 100, 2) if total_apps > 0 else 0,
            'avg_fields_per_app': round(total_fields / total_apps, 1) if total_apps > 0 else 0,
            'period_days': days
        }


class FailureHandlingWorkflow:
    """
    Workflow: Handle and recover from failures.
    
    Patterns:
    - Retry failed applications
    - Detect duplicates before applying
    - Log errors for debugging
    - Cleanup stale records
    """
    
    def __init__(self, db: SupabaseClient = None):
        self.db = db or get_db()
    
    def get_retryable_applications(self, max_retries: int = 3) -> List[Dict]:
        """Get applications that can be retried."""
        result = self.db.client.table('applications')\
            .select('*, jobs(*)')\
            .eq('user_id', self.db.user_id)\
            .eq('status', 'failed')\
            .lt('retry_count', max_retries)\
            .order('created_at', desc=True)\
            .execute()
        
        return result.data
    
    def mark_for_retry(self, application_id: str) -> None:
        """Mark a failed application for retry."""
        self.db.client.table('applications').update({
            'status': 'pending',
            'retry_count': self.db.client.table('applications')
                .select('retry_count')
                .eq('id', application_id)
                .single()
                .execute()
                .data.get('retry_count', 0) + 1
        }).eq('id', application_id).execute()
    
    def cleanup_stale_runs(self, hours: int = 24) -> int:
        """Mark stale automation runs as failed."""
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        result = self.db.client.table('automation_runs').update({
            'status': 'failed',
            'error_message': 'Stale run - marked as failed during cleanup'
        }).eq('status', 'running').lt('started_at', cutoff).execute()
        
        return len(result.data) if result.data else 0
    
    def get_error_summary(self, days: int = 7) -> Dict:
        """Get summary of recent errors."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        result = self.db.client.table('applications')\
            .select('last_error')\
            .eq('status', 'failed')\
            .gte('created_at', cutoff)\
            .not_.is_('last_error', 'null')\
            .execute()
        
        # Count error types
        error_counts = {}
        for app in result.data:
            error = app.get('last_error', 'Unknown')[:50]
            error_counts[error] = error_counts.get(error, 0) + 1
        
        # Sort by count
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'total_failures': len(result.data),
            'top_errors': sorted_errors[:10],
            'period_days': days
        }


# Convenience functions for quick workflow access
def save_job_from_scrape(raw_job: Dict) -> Tuple[str, bool]:
    """Quick function to save a scraped job."""
    workflow = JobDiscoveryWorkflow()
    return workflow.process_job(raw_job)


def track_application(
    job_id: str,
    resume_path: str = None,
    cover_letter: str = None,
    match_score: float = None
) -> Optional[str]:
    """Quick function to start tracking an application."""
    workflow = ApplicationWorkflow()
    return workflow.start_application(
        job_id=job_id,
        resume_path=resume_path,
        cover_letter_text=cover_letter,
        match_score=match_score
    )


def get_daily_report() -> Dict:
    """Quick function to get daily report."""
    workflow = AnalyticsWorkflow()
    return workflow.generate_daily_report()


if __name__ == "__main__":
    print("Testing workflows...")
    
    # Test job discovery
    test_job = {
        'title': 'Graphic Designer',
        'company': 'Test Company',
        'job_url': 'https://example.com/jobs/123',
        'location': 'Remote',
        'description': 'Great opportunity...'
    }
    
    try:
        workflow = JobDiscoveryWorkflow()
        job_id, is_new = workflow.process_job(test_job)
        print(f"Job saved: {job_id} (new: {is_new})")
        
        # Test analytics
        analytics = AnalyticsWorkflow()
        report = analytics.generate_daily_report()
        print(f"Daily report: {report}")
        
        print("\n✅ Workflow tests passed!")
    except Exception as e:
        print(f"❌ Error: {e}")
