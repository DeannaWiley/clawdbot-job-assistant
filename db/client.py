"""
Supabase Client Module for ClawdBot
====================================
High-level API for interacting with the Supabase backend.

This module provides workflow functions for:
- Job posting management
- Application tracking
- Resume/cover letter storage
- CAPTCHA logging
- Analytics queries

Usage:
    from supabase.client import SupabaseClient
    
    db = SupabaseClient()
    
    # Save a new job
    job_id = await db.save_job(job_data)
    
    # Record an application
    app_id = await db.create_application(job_id, resume_id)
"""

import os
import sys
import json
import hashlib
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from .config import get_supabase_client, get_service_client, get_config


# Default user ID for single-user mode (Deanna)
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


@dataclass
class JobData:
    """Job posting data structure."""
    source: str
    source_url: str
    title: str
    company: str
    location: Optional[str] = None
    job_type: Optional[str] = None
    remote_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    posted_date: Optional[date] = None
    raw_data: Optional[Dict] = None


@dataclass
class ApplicationData:
    """Application attempt data structure."""
    job_id: str
    resume_id: Optional[str] = None
    cover_letter_id: Optional[str] = None
    match_score_id: Optional[str] = None
    automation_run_id: Optional[str] = None
    submission_method: str = "auto"
    fields_filled: int = 0
    fields_total: Optional[int] = None
    fields_failed: Optional[List[str]] = None
    notes: Optional[str] = None
    metadata: Optional[Dict] = None


class SupabaseClient:
    """
    High-level Supabase client for ClawdBot.
    
    Provides workflow-oriented methods for job application tracking.
    """
    
    def __init__(self, user_id: str = DEFAULT_USER_ID, use_service_key: bool = False):
        """
        Initialize the Supabase client.
        
        Args:
            user_id: UUID of the current user
            use_service_key: If True, use service role key (bypasses RLS)
        """
        self.user_id = user_id
        self._use_service_key = use_service_key
        self._client = None
        self._current_run_id = None
    
    @property
    def client(self):
        """Get the Supabase client instance."""
        if self._client is None:
            if self._use_service_key:
                self._client = get_service_client()
            else:
                self._client = get_supabase_client()
        return self._client
    
    # =========================================================================
    # AUTOMATION RUN MANAGEMENT
    # =========================================================================
    
    def start_automation_run(self, run_type: str = "manual") -> str:
        """
        Start a new automation run session.
        
        Args:
            run_type: One of 'scheduled', 'manual', 'test', 'retry'
        
        Returns:
            UUID of the new run
        """
        result = self.client.table('automation_runs').insert({
            'user_id': self.user_id,
            'run_type': run_type,
            'status': 'running',
            'metadata': {
                'started_by': 'clawdbot',
                'version': '1.0.0'
            }
        }).execute()
        
        self._current_run_id = result.data[0]['id']
        print(f"📊 Started automation run: {self._current_run_id[:8]}...")
        return self._current_run_id
    
    def end_automation_run(
        self,
        status: str = "completed",
        jobs_found: int = 0,
        jobs_applied: int = 0,
        jobs_skipped: int = 0,
        jobs_failed: int = 0,
        error_message: Optional[str] = None
    ) -> None:
        """End the current automation run with statistics."""
        if not self._current_run_id:
            return
        
        self.client.table('automation_runs').update({
            'status': status,
            'ended_at': datetime.utcnow().isoformat(),
            'jobs_found': jobs_found,
            'jobs_applied': jobs_applied,
            'jobs_skipped': jobs_skipped,
            'jobs_failed': jobs_failed,
            'error_message': error_message
        }).eq('id', self._current_run_id).execute()
        
        print(f"📊 Ended automation run: {status} ({jobs_applied} applied, {jobs_failed} failed)")
        self._current_run_id = None
    
    # =========================================================================
    # JOB MANAGEMENT
    # =========================================================================
    
    def save_job(self, job: JobData) -> str:
        """
        Save or update a job posting.
        
        Uses upsert logic: if job URL exists, updates last_seen_at.
        
        Args:
            job: JobData object with job details
        
        Returns:
            UUID of the job (existing or new)
        """
        # Check if job exists
        existing = self.client.table('jobs')\
            .select('id')\
            .eq('source_url', job.source_url)\
            .execute()
        
        if existing.data:
            # Update last_seen_at
            job_id = existing.data[0]['id']
            self.client.table('jobs').update({
                'last_seen_at': datetime.utcnow().isoformat()
            }).eq('id', job_id).execute()
            return job_id
        
        # Insert new job
        insert_data = {
            'source': job.source,
            'source_url': job.source_url,
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'job_type': job.job_type,
            'remote_type': job.remote_type,
            'salary_min': job.salary_min,
            'salary_max': job.salary_max,
            'description': job.description,
            'requirements': job.requirements,
            'raw_data': job.raw_data
        }
        
        if job.posted_date:
            insert_data['posted_date'] = job.posted_date.isoformat()
        
        result = self.client.table('jobs').insert(insert_data).execute()
        job_id = result.data[0]['id']
        print(f"📌 Saved job: {job.title} at {job.company}")
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job details by ID."""
        result = self.client.table('jobs')\
            .select('*')\
            .eq('id', job_id)\
            .execute()
        return result.data[0] if result.data else None
    
    def get_job_by_url(self, url: str) -> Optional[Dict]:
        """Get job by source URL."""
        result = self.client.table('jobs')\
            .select('*')\
            .eq('source_url', url)\
            .execute()
        return result.data[0] if result.data else None
    
    def search_jobs(
        self,
        title: Optional[str] = None,
        company: Optional[str] = None,
        source: Optional[str] = None,
        active_only: bool = True,
        limit: int = 50
    ) -> List[Dict]:
        """Search jobs with filters."""
        query = self.client.table('jobs').select('*')
        
        if title:
            query = query.ilike('title', f'%{title}%')
        if company:
            query = query.ilike('company', f'%{company}%')
        if source:
            query = query.eq('source', source)
        if active_only:
            query = query.eq('is_active', True)
        
        result = query.order('first_seen_at', desc=True).limit(limit).execute()
        return result.data
    
    # =========================================================================
    # APPLICATION MANAGEMENT
    # =========================================================================
    
    def check_already_applied(self, job_id: str) -> bool:
        """Check if already applied to this job."""
        result = self.client.table('applications')\
            .select('id, status')\
            .eq('user_id', self.user_id)\
            .eq('job_id', job_id)\
            .not_.in_('status', ['failed', 'withdrawn'])\
            .execute()
        return len(result.data) > 0
    
    def create_application(self, app: ApplicationData) -> str:
        """
        Create a new application record.
        
        Args:
            app: ApplicationData with application details
        
        Returns:
            UUID of the new application
        """
        insert_data = {
            'user_id': self.user_id,
            'job_id': app.job_id,
            'automation_run_id': app.automation_run_id or self._current_run_id,
            'resume_id': app.resume_id,
            'cover_letter_id': app.cover_letter_id,
            'match_score_id': app.match_score_id,
            'submission_method': app.submission_method,
            'status': 'in_progress',
            'fields_filled': app.fields_filled,
            'fields_total': app.fields_total,
            'fields_failed': app.fields_failed,
            'notes': app.notes,
            'metadata': app.metadata or {}
        }
        
        result = self.client.table('applications').insert(insert_data).execute()
        app_id = result.data[0]['id']
        print(f"📝 Created application: {app_id[:8]}...")
        return app_id
    
    def update_application(
        self,
        application_id: str,
        status: Optional[str] = None,
        fields_filled: Optional[int] = None,
        fields_failed: Optional[List[str]] = None,
        submitted_at: Optional[datetime] = None,
        confirmation_received: Optional[bool] = None,
        last_error: Optional[str] = None,
        retry_count: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """Update an existing application record."""
        update_data = {}
        
        if status:
            update_data['status'] = status
        if fields_filled is not None:
            update_data['fields_filled'] = fields_filled
        if fields_failed is not None:
            update_data['fields_failed'] = fields_failed
        if submitted_at:
            update_data['submitted_at'] = submitted_at.isoformat()
        if confirmation_received is not None:
            update_data['confirmation_received'] = confirmation_received
        if last_error:
            update_data['last_error'] = last_error
        if retry_count is not None:
            update_data['retry_count'] = retry_count
        if metadata:
            update_data['metadata'] = metadata
        
        if update_data:
            self.client.table('applications')\
                .update(update_data)\
                .eq('id', application_id)\
                .execute()
    
    def mark_application_submitted(
        self,
        application_id: str,
        confirmation_received: bool = False
    ) -> None:
        """Mark an application as successfully submitted."""
        self.update_application(
            application_id,
            status='submitted',
            submitted_at=datetime.utcnow(),
            confirmation_received=confirmation_received
        )
        print(f"✅ Application submitted: {application_id[:8]}...")
    
    def mark_application_failed(
        self,
        application_id: str,
        error: str,
        screenshot_path: Optional[str] = None
    ) -> None:
        """Mark an application as failed."""
        update_data = {
            'status': 'failed',
            'last_error': error
        }
        if screenshot_path:
            update_data['error_screenshot_path'] = screenshot_path
        
        self.client.table('applications')\
            .update(update_data)\
            .eq('id', application_id)\
            .execute()
        print(f"❌ Application failed: {error[:50]}...")
    
    def get_application_history(
        self,
        status: Optional[str] = None,
        days: int = 30,
        limit: int = 100
    ) -> List[Dict]:
        """Get application history with job details."""
        query = self.client.table('applications')\
            .select('*, jobs(*), resumes(version_name), match_scores(overall_score)')\
            .eq('user_id', self.user_id)
        
        if status:
            query = query.eq('status', status)
        
        result = query\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
        
        return result.data
    
    # =========================================================================
    # RESUME & COVER LETTER MANAGEMENT
    # =========================================================================
    
    def save_resume(
        self,
        version_name: str,
        file_path: str,
        content_text: Optional[str] = None,
        is_base: bool = False,
        tailored_for_job_id: Optional[str] = None,
        ai_modifications: Optional[Dict] = None
    ) -> str:
        """Save a resume version."""
        # Calculate content hash for deduplication
        content_hash = None
        file_size = None
        
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                content = f.read()
                content_hash = hashlib.sha256(content).hexdigest()
                file_size = len(content)
        
        # Get file type from extension
        file_type = Path(file_path).suffix.lower().lstrip('.')
        if file_type not in ['pdf', 'docx', 'html', 'txt']:
            file_type = 'pdf'
        
        insert_data = {
            'user_id': self.user_id,
            'version_name': version_name,
            'is_base': is_base,
            'file_path': file_path,
            'file_type': file_type,
            'file_size_bytes': file_size,
            'content_text': content_text,
            'content_hash': content_hash,
            'tailored_for_job_id': tailored_for_job_id,
            'ai_modifications': ai_modifications
        }
        
        result = self.client.table('resumes').insert(insert_data).execute()
        return result.data[0]['id']
    
    def save_cover_letter(
        self,
        job_id: str,
        content_text: str,
        file_path: Optional[str] = None,
        version_name: Optional[str] = None,
        ai_model_used: Optional[str] = None,
        generation_prompt: Optional[str] = None
    ) -> str:
        """Save a cover letter."""
        content_hash = hashlib.sha256(content_text.encode()).hexdigest()
        
        insert_data = {
            'user_id': self.user_id,
            'job_id': job_id,
            'version_name': version_name,
            'file_path': file_path,
            'content_text': content_text,
            'content_hash': content_hash,
            'ai_generated': True,
            'ai_model_used': ai_model_used,
            'generation_prompt': generation_prompt
        }
        
        result = self.client.table('cover_letters').insert(insert_data).execute()
        return result.data[0]['id']
    
    # =========================================================================
    # MATCH SCORE MANAGEMENT
    # =========================================================================
    
    def save_match_score(
        self,
        job_id: str,
        overall_score: float,
        skills_match: Optional[float] = None,
        experience_match: Optional[float] = None,
        location_match: Optional[float] = None,
        matched_keywords: Optional[List[str]] = None,
        missing_keywords: Optional[List[str]] = None,
        reasoning: Optional[str] = None,
        recommendation: str = "apply",
        ai_model_used: Optional[str] = None
    ) -> str:
        """Save job match score analysis."""
        insert_data = {
            'user_id': self.user_id,
            'job_id': job_id,
            'overall_score': overall_score,
            'skills_match': skills_match,
            'experience_match': experience_match,
            'location_match': location_match,
            'matched_keywords': matched_keywords,
            'missing_keywords': missing_keywords,
            'reasoning': reasoning,
            'recommendation': recommendation,
            'ai_model_used': ai_model_used
        }
        
        # Upsert to handle re-scoring
        result = self.client.table('match_scores')\
            .upsert(insert_data, on_conflict='user_id,job_id')\
            .execute()
        
        return result.data[0]['id']
    
    # =========================================================================
    # CAPTCHA LOGGING
    # =========================================================================
    
    def log_captcha(
        self,
        application_id: str,
        captcha_type: str,
        site_key: Optional[str] = None,
        page_url: Optional[str] = None,
        resolution_method: Optional[str] = None,
        solved: bool = False,
        solve_time_ms: Optional[int] = None,
        cost_usd: Optional[float] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        screenshot_path: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """Log a CAPTCHA encounter and resolution attempt."""
        insert_data = {
            'application_id': application_id,
            'automation_run_id': self._current_run_id,
            'captcha_type': captcha_type,
            'site_key': site_key,
            'page_url': page_url,
            'resolution_method': resolution_method,
            'solved': solved,
            'solve_time_ms': solve_time_ms,
            'cost_usd': cost_usd,
            'error_code': error_code,
            'error_message': error_message,
            'screenshot_path': screenshot_path,
            'metadata': metadata or {}
        }
        
        result = self.client.table('captcha_logs').insert(insert_data).execute()
        return result.data[0]['id']
    
    # =========================================================================
    # FORM FIELD LOGGING
    # =========================================================================
    
    def log_form_fields(
        self,
        application_id: str,
        fields: List[Dict]
    ) -> None:
        """
        Log form field filling results.
        
        Args:
            application_id: UUID of the application
            fields: List of dicts with field_name, field_type, value_used, success, etc.
        """
        if not fields:
            return
        
        insert_data = [
            {
                'application_id': application_id,
                'field_name': f.get('field_name'),
                'field_type': f.get('field_type'),
                'field_label': f.get('field_label'),
                'value_used': f.get('value_used'),
                'value_source': f.get('value_source', 'profile'),
                'success': f.get('success', True),
                'error_message': f.get('error_message')
            }
            for f in fields
        ]
        
        self.client.table('form_field_logs').insert(insert_data).execute()
    
    # =========================================================================
    # ANALYTICS & REPORTING
    # =========================================================================
    
    def get_daily_stats(self, days: int = 30) -> List[Dict]:
        """Get daily application statistics."""
        result = self.client.table('daily_application_stats')\
            .select('*')\
            .eq('user_id', self.user_id)\
            .order('date', desc=True)\
            .limit(days)\
            .execute()
        return result.data
    
    def get_weekly_summary(self, weeks: int = 12) -> List[Dict]:
        """Get weekly summary statistics."""
        result = self.client.table('weekly_summary')\
            .select('*')\
            .eq('user_id', self.user_id)\
            .order('week_start', desc=True)\
            .limit(weeks)\
            .execute()
        return result.data
    
    def get_captcha_performance(self) -> List[Dict]:
        """Get CAPTCHA performance metrics."""
        result = self.client.table('captcha_performance')\
            .select('*')\
            .execute()
        return result.data
    
    def get_job_source_stats(self) -> List[Dict]:
        """Get job source effectiveness metrics."""
        result = self.client.table('job_source_stats')\
            .select('*')\
            .execute()
        return result.data
    
    def get_success_rate(self, days: int = 30) -> Dict:
        """Calculate overall success rate."""
        from datetime import timedelta
        
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        result = self.client.table('applications')\
            .select('status')\
            .eq('user_id', self.user_id)\
            .gte('created_at', cutoff)\
            .execute()
        
        total = len(result.data)
        if total == 0:
            return {'total': 0, 'success_rate': 0, 'interview_rate': 0}
        
        submitted = sum(1 for r in result.data if r['status'] == 'submitted')
        interviews = sum(1 for r in result.data if r['status'] == 'interview')
        failed = sum(1 for r in result.data if r['status'] == 'failed')
        
        return {
            'total': total,
            'submitted': submitted,
            'interviews': interviews,
            'failed': failed,
            'success_rate': round(submitted / total * 100, 2),
            'interview_rate': round(interviews / total * 100, 2) if submitted > 0 else 0
        }


# Convenience function for quick access
def get_db(user_id: str = DEFAULT_USER_ID) -> SupabaseClient:
    """Get a SupabaseClient instance."""
    return SupabaseClient(user_id=user_id)


if __name__ == "__main__":
    # Test the client
    print("Testing SupabaseClient...")
    try:
        db = SupabaseClient()
        
        # Test job search
        print("\nSearching for jobs...")
        jobs = db.search_jobs(limit=5)
        print(f"Found {len(jobs)} jobs")
        
        # Test stats
        print("\nGetting success rate...")
        stats = db.get_success_rate()
        print(f"Stats: {stats}")
        
        print("\n✅ SupabaseClient test passed!")
    except Exception as e:
        print(f"❌ Error: {e}")
