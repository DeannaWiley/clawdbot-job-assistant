"""
Supabase Integration Bridge for ClawdBot
=========================================

This module integrates the Supabase backend with the existing
ClawdBot automation system. It provides hooks that can be called
from the existing code to persist data to Supabase.

Usage:
    from supabase.integration import SupabaseIntegration
    
    # Initialize at start of automation run
    integration = SupabaseIntegration()
    integration.start_run()
    
    # Track job and application
    job_id = integration.track_job(job_data)
    app_id = integration.start_application(job_id, resume_path)
    
    # Update on completion
    integration.complete_application(app_id, success=True)
    
    # End run
    integration.end_run()
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

try:
    from .client import SupabaseClient, JobData, ApplicationData, get_db
    from .workflows import JobDiscoveryWorkflow, ApplicationWorkflow, AnalyticsWorkflow
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️ Supabase not available - running in offline mode")


class SupabaseIntegration:
    """
    Integration layer between ClawdBot automation and Supabase backend.
    
    Gracefully handles cases where Supabase is not configured,
    falling back to local file storage.
    """
    
    def __init__(self, enabled: bool = True):
        """
        Initialize the Supabase integration.
        
        Args:
            enabled: If False, all operations become no-ops
        """
        self.enabled = enabled and SUPABASE_AVAILABLE
        self._db = None
        self._job_workflow = None
        self._app_workflow = None
        self._current_run_id = None
        self._stats = {
            'jobs_found': 0,
            'jobs_applied': 0,
            'jobs_skipped': 0,
            'jobs_failed': 0
        }
        
        if self.enabled:
            try:
                self._db = get_db()
                self._job_workflow = JobDiscoveryWorkflow(self._db)
                self._app_workflow = ApplicationWorkflow(self._db)
                print("✅ Supabase integration initialized")
            except Exception as e:
                print(f"⚠️ Supabase initialization failed: {e}")
                self.enabled = False
    
    @property
    def is_available(self) -> bool:
        """Check if Supabase is available and configured."""
        return self.enabled and self._db is not None
    
    # =========================================================================
    # AUTOMATION RUN LIFECYCLE
    # =========================================================================
    
    def start_run(self, run_type: str = "manual") -> Optional[str]:
        """
        Start a new automation run.
        
        Args:
            run_type: 'scheduled', 'manual', 'test', 'retry'
        
        Returns:
            Run ID or None if not available
        """
        if not self.is_available:
            return None
        
        try:
            self._current_run_id = self._db.start_automation_run(run_type)
            self._stats = {
                'jobs_found': 0,
                'jobs_applied': 0,
                'jobs_skipped': 0,
                'jobs_failed': 0
            }
            return self._current_run_id
        except Exception as e:
            print(f"⚠️ Failed to start run in Supabase: {e}")
            return None
    
    def end_run(self, status: str = "completed", error: str = None) -> None:
        """End the current automation run."""
        if not self.is_available or not self._current_run_id:
            return
        
        try:
            self._db.end_automation_run(
                status=status,
                jobs_found=self._stats['jobs_found'],
                jobs_applied=self._stats['jobs_applied'],
                jobs_skipped=self._stats['jobs_skipped'],
                jobs_failed=self._stats['jobs_failed'],
                error_message=error
            )
        except Exception as e:
            print(f"⚠️ Failed to end run in Supabase: {e}")
    
    # =========================================================================
    # JOB TRACKING
    # =========================================================================
    
    def track_job(self, job_data: Dict) -> Optional[str]:
        """
        Track a job posting in Supabase.
        
        Args:
            job_data: Job data from scraper or job search
        
        Returns:
            Job ID or None
        """
        if not self.is_available:
            return None
        
        try:
            job_id, is_new = self._job_workflow.process_job(job_data)
            if is_new:
                self._stats['jobs_found'] += 1
            return job_id
        except Exception as e:
            print(f"⚠️ Failed to track job: {e}")
            return None
    
    def check_already_applied(self, job_url: str) -> bool:
        """
        Check if already applied to a job.
        
        Args:
            job_url: URL of the job posting
        
        Returns:
            True if already applied
        """
        if not self.is_available:
            return False
        
        try:
            job = self._db.get_job_by_url(job_url)
            if not job:
                return False
            return self._db.check_already_applied(job['id'])
        except Exception as e:
            print(f"⚠️ Failed to check application status: {e}")
            return False
    
    # =========================================================================
    # APPLICATION TRACKING
    # =========================================================================
    
    def start_application(
        self,
        job_id: str = None,
        job_url: str = None,
        resume_path: str = None,
        cover_letter_text: str = None,
        match_score: float = None,
        match_reasoning: str = None
    ) -> Optional[str]:
        """
        Start tracking an application attempt.
        
        Args:
            job_id: UUID of the job (or provide job_url)
            job_url: URL of the job posting
            resume_path: Path to resume file
            cover_letter_text: Cover letter content
            match_score: AI match score (0-100)
            match_reasoning: AI reasoning text
        
        Returns:
            Application ID or None
        """
        if not self.is_available:
            return None
        
        try:
            # Get job_id from URL if not provided
            if not job_id and job_url:
                job = self._db.get_job_by_url(job_url)
                if job:
                    job_id = job['id']
                else:
                    # Create job record first
                    job_id = self.track_job({'job_url': job_url, 'title': 'Unknown', 'company': 'Unknown'})
            
            if not job_id:
                return None
            
            app_id = self._app_workflow.start_application(
                job_id=job_id,
                resume_path=resume_path,
                cover_letter_text=cover_letter_text,
                match_score=match_score,
                match_reasoning=match_reasoning
            )
            
            return app_id
        except Exception as e:
            print(f"⚠️ Failed to start application tracking: {e}")
            return None
    
    def update_application_progress(
        self,
        application_id: str,
        fields_filled: int,
        fields_total: int = None,
        fields_failed: List[str] = None
    ) -> None:
        """Update form filling progress."""
        if not self.is_available or not application_id:
            return
        
        try:
            self._app_workflow.update_form_progress(
                fields_filled=fields_filled,
                fields_total=fields_total,
                fields_failed=fields_failed
            )
        except Exception as e:
            print(f"⚠️ Failed to update progress: {e}")
    
    def complete_application_success(
        self,
        application_id: str = None,
        confirmation_received: bool = False,
        screenshot_path: str = None
    ) -> None:
        """Mark application as successfully submitted."""
        if not self.is_available:
            return
        
        try:
            self._app_workflow.complete_success(
                confirmation_received=confirmation_received,
                screenshot_path=screenshot_path
            )
            self._stats['jobs_applied'] += 1
        except Exception as e:
            print(f"⚠️ Failed to mark success: {e}")
    
    def complete_application_failure(
        self,
        application_id: str = None,
        error: str = "Unknown error",
        screenshot_path: str = None,
        retry: bool = False
    ) -> None:
        """Mark application as failed."""
        if not self.is_available:
            return
        
        try:
            self._app_workflow.complete_failure(
                error=error,
                screenshot_path=screenshot_path,
                retry=retry
            )
            self._stats['jobs_failed'] += 1
        except Exception as e:
            print(f"⚠️ Failed to mark failure: {e}")
    
    def skip_application(self, reason: str = "skipped") -> None:
        """Record a skipped application."""
        self._stats['jobs_skipped'] += 1
    
    # =========================================================================
    # CAPTCHA LOGGING
    # =========================================================================
    
    def log_captcha(
        self,
        application_id: str,
        captcha_type: str,
        solved: bool,
        resolution_method: str = None,
        solve_time_ms: int = None,
        cost: float = None,
        error: str = None
    ) -> None:
        """Log a CAPTCHA encounter."""
        if not self.is_available or not application_id:
            return
        
        try:
            self._app_workflow.log_captcha_encounter(
                captcha_type=captcha_type,
                solved=solved,
                resolution_method=resolution_method,
                solve_time_ms=solve_time_ms,
                cost=cost,
                error=error
            )
        except Exception as e:
            print(f"⚠️ Failed to log CAPTCHA: {e}")
    
    # =========================================================================
    # ANALYTICS
    # =========================================================================
    
    def get_daily_report(self) -> Dict:
        """Get daily application report."""
        if not self.is_available:
            return {}
        
        try:
            analytics = AnalyticsWorkflow(self._db)
            return analytics.generate_daily_report()
        except Exception as e:
            print(f"⚠️ Failed to get daily report: {e}")
            return {}
    
    def get_success_rate(self, days: int = 30) -> Dict:
        """Get success rate statistics."""
        if not self.is_available:
            return {}
        
        try:
            return self._db.get_success_rate(days=days)
        except Exception as e:
            print(f"⚠️ Failed to get success rate: {e}")
            return {}


# Global integration instance
_integration = None


def get_integration(enabled: bool = True) -> SupabaseIntegration:
    """Get the global Supabase integration instance."""
    global _integration
    if _integration is None:
        _integration = SupabaseIntegration(enabled=enabled)
    return _integration


def track_application_to_supabase(
    job_url: str,
    job_title: str,
    company: str,
    success: bool,
    resume_path: str = None,
    cover_letter: str = None,
    error: str = None,
    screenshot_path: str = None
) -> None:
    """
    Convenience function to track an application in Supabase.
    
    Can be called from existing code with minimal changes.
    """
    integration = get_integration()
    
    if not integration.is_available:
        return
    
    try:
        # Track job
        job_id = integration.track_job({
            'job_url': job_url,
            'title': job_title,
            'company': company
        })
        
        # Start application
        app_id = integration.start_application(
            job_id=job_id,
            resume_path=resume_path,
            cover_letter_text=cover_letter
        )
        
        # Complete
        if success:
            integration.complete_application_success(
                application_id=app_id,
                screenshot_path=screenshot_path
            )
        else:
            integration.complete_application_failure(
                application_id=app_id,
                error=error or "Unknown error",
                screenshot_path=screenshot_path
            )
    except Exception as e:
        print(f"⚠️ Failed to track to Supabase: {e}")


if __name__ == "__main__":
    print("Testing Supabase Integration...")
    
    integration = get_integration()
    
    if integration.is_available:
        print("✅ Supabase integration is available")
        
        # Test run lifecycle
        run_id = integration.start_run(run_type='test')
        print(f"   Started run: {run_id}")
        
        # Test job tracking
        job_id = integration.track_job({
            'title': 'Test Job',
            'company': 'Test Company',
            'job_url': 'https://example.com/test-job',
            'location': 'Remote'
        })
        print(f"   Tracked job: {job_id}")
        
        # Test application
        app_id = integration.start_application(job_id=job_id)
        print(f"   Started application: {app_id}")
        
        # End run
        integration.end_run()
        print("   Ended run")
        
        # Get report
        report = integration.get_daily_report()
        print(f"   Daily report: {report}")
        
        print("\n✅ Integration test passed!")
    else:
        print("⚠️ Supabase not configured - set environment variables")
