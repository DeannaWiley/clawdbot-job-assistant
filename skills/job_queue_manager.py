#!/usr/bin/env python3
"""
Job Queue Manager - Manages job applications through Supabase
=============================================================
Provides functions for ClawdBot to:
- Add jobs to queue
- Get next job to apply
- Mark jobs as applied/failed/expired
- Search for new jobs
- Check job queue status
"""
import os
import sys
import subprocess
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_env(var_name):
    value = os.environ.get(var_name)
    if value:
        return value
    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             f'[Environment]::GetEnvironmentVariable("{var_name}", "User")'],
            capture_output=True, text=True, timeout=5
        )
        value = result.stdout.strip()
        if value and value != 'None':
            os.environ[var_name] = value
            return value
    except:
        pass
    return None


# Load env
for var in ['SUPABASE_URL', 'SUPABASE_ANON_KEY', 'GROQ_API_KEY', 'CaptchaKey']:
    load_env(var)

# Initialize Supabase
import importlib
sb = importlib.import_module('supabase._sync.client')
supabase = sb.create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_ANON_KEY'])


class JobQueueManager:
    """Manages the job application queue in Supabase."""
    
    def __init__(self):
        self.client = supabase
    
    def add_job(self, url: str, title: str, company: str, 
                source: str = 'other', description: str = '', 
                priority: int = 5) -> Optional[str]:
        """Add a job to the queue."""
        try:
            # Determine source from URL
            if 'greenhouse' in url.lower():
                source = 'greenhouse'
            elif 'lever' in url.lower():
                source = 'lever'
            elif 'linkedin' in url.lower():
                source = 'linkedin'
            elif 'indeed' in url.lower():
                source = 'indeed'
            elif 'workday' in url.lower():
                source = 'workday'
            
            # Use only existing columns (is_active for queue status)
            result = self.client.table('jobs').insert({
                'source_url': url,
                'title': title,
                'company': company,
                'source': source,
                'description': description,
                'is_active': True  # True = in queue, False = processed
            }).execute()
            
            if result.data:
                return result.data[0]['id']
            return None
        except Exception as e:
            # If duplicate, try to get existing
            if 'duplicate' in str(e).lower():
                existing = self.client.table('jobs').select('id').eq('source_url', url).execute()
                if existing.data:
                    return existing.data[0]['id']
            print(f"Error adding job: {e}")
            return None
    
    def get_queue(self, limit: int = 10) -> List[Dict]:
        """Get jobs in the queue (is_active=True means not yet applied)."""
        try:
            result = self.client.table('jobs').select(
                'id, title, company, source, source_url, created_at'
            ).eq('is_active', True).order('created_at', desc=True).limit(limit).execute()
            return result.data
        except Exception as e:
            print(f"Error getting queue: {e}")
            return []
    
    def get_next_job(self) -> Optional[Dict]:
        """Get the next job to apply to (is_active=True)."""
        try:
            result = self.client.table('jobs').select(
                'id, title, company, source, source_url, description'
            ).eq('is_active', True).order('created_at', desc=True).limit(1).execute()
            
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            print(f"Error getting next job: {e}")
            return None
    
    def mark_applied(self, job_id: str) -> bool:
        """Mark a job as applied (set is_active=False)."""
        try:
            self.client.table('jobs').update({
                'is_active': False
            }).eq('id', job_id).execute()
            return True
        except Exception as e:
            print(f"Error marking applied: {e}")
            return False
    
    def mark_failed(self, job_id: str, reason: str = '') -> bool:
        """Mark a job as failed."""
        try:
            self.client.table('jobs').update({
                'is_active': False
            }).eq('id', job_id).execute()
            return True
        except Exception as e:
            print(f"Error marking failed: {e}")
            return False
    
    def mark_expired(self, job_id: str) -> bool:
        """Mark a job as expired."""
        try:
            self.client.table('jobs').update({
                'is_active': False
            }).eq('id', job_id).execute()
            return True
        except Exception as e:
            print(f"Error marking expired: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get queue statistics."""
        try:
            active = self.client.table('jobs').select('id').eq('is_active', True).execute()
            inactive = self.client.table('jobs').select('id').eq('is_active', False).execute()
            apps = self.client.table('applications').select('id, status').execute()
            
            applied = sum(1 for a in apps.data if a.get('status') == 'submitted')
            failed = sum(1 for a in apps.data if a.get('status') == 'failed')
            
            return {
                'total': len(active.data) + len(inactive.data),
                'queued': len(active.data),
                'processed': len(inactive.data),
                'applied': applied,
                'failed': failed
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
    
    def import_jobs_from_search(self, jobs: List[Dict]) -> int:
        """Import multiple jobs from a search result."""
        added = 0
        for job in jobs:
            job_id = self.add_job(
                url=job.get('url', ''),
                title=job.get('title', ''),
                company=job.get('company', ''),
                source=job.get('source', 'other'),
                description=job.get('description', ''),
                priority=job.get('priority', 5)
            )
            if job_id:
                added += 1
        return added


# ClawdBot integration functions
def clawdbot_add_job(url: str, title: str, company: str, priority: int = 5) -> str:
    """ClawdBot: Add a job to the application queue."""
    manager = JobQueueManager()
    job_id = manager.add_job(url, title, company, priority=priority)
    if job_id:
        return f"✅ Job added to queue: {title} at {company} (ID: {job_id[:8]}...)"
    return f"❌ Failed to add job: {title} at {company}"


def clawdbot_get_queue() -> str:
    """ClawdBot: Get the current job queue."""
    manager = JobQueueManager()
    jobs = manager.get_queue()
    
    if not jobs:
        return "📋 Job queue is empty. Add jobs with clawdbot_add_job()."
    
    output = f"📋 Job Queue ({len(jobs)} jobs):\n"
    for i, job in enumerate(jobs, 1):
        output += f"  {i}. {job['title']} at {job['company']} [{job['source']}]\n"
    return output


def clawdbot_get_stats() -> str:
    """ClawdBot: Get job queue statistics."""
    manager = JobQueueManager()
    stats = manager.get_stats()
    
    return f"""📊 Job Queue Stats:
   Total Jobs:  {stats.get('total', 0)}
   In Queue:    {stats.get('queued', 0)}
   Processed:   {stats.get('processed', 0)}
   Applied:     {stats.get('applied', 0)}
   Failed:      {stats.get('failed', 0)}"""


async def clawdbot_apply_next() -> str:
    """ClawdBot: Apply to the next job in the queue."""
    manager = JobQueueManager()
    job = manager.get_next_job()
    
    if not job:
        return "📋 No jobs in queue to apply to."
    
    print(f"\n🎯 Applying to: {job['title']} at {job['company']}")
    print(f"   URL: {job['source_url']}")
    
    try:
        from real_auto_apply import auto_apply_to_job
        result = await auto_apply_to_job(
            job['source_url'],
            job['title'],
            job['company'],
            job.get('description', '')
        )
        
        if result.get('success'):
            manager.mark_applied(job['id'])
            return f"✅ Successfully applied to {job['title']} at {job['company']}"
        else:
            error = result.get('error', 'Unknown error')
            if 'closed' in error.lower() or 'no longer' in error.lower():
                manager.mark_expired(job['id'])
                return f"⚠️ Job expired: {job['title']} at {job['company']}"
            else:
                manager.mark_failed(job['id'], error)
                return f"❌ Failed to apply: {error}"
    except Exception as e:
        manager.mark_failed(job['id'], str(e))
        return f"❌ Exception applying to {job['title']}: {e}"


async def clawdbot_apply_all(max_applications: int = 5) -> str:
    """ClawdBot: Apply to all jobs in the queue (up to max)."""
    results = []
    for i in range(max_applications):
        result = await clawdbot_apply_next()
        results.append(result)
        if "No jobs in queue" in result:
            break
        await asyncio.sleep(2)  # Brief pause between applications
    
    return "\n".join(results)


def clawdbot_clear_expired() -> str:
    """ClawdBot: Clear expired jobs from the queue."""
    manager = JobQueueManager()
    try:
        result = manager.client.table('jobs').update({
            'application_status': 'expired',
            'is_active': False
        }).eq('application_status', 'failed').execute()
        
        count = len(result.data) if result.data else 0
        return f"🧹 Cleared {count} failed jobs as expired"
    except Exception as e:
        return f"❌ Error clearing expired: {e}"


# Main test
if __name__ == "__main__":
    print("=" * 60)
    print("JOB QUEUE MANAGER TEST")
    print("=" * 60)
    
    # Test adding a job
    print("\n1. Adding test job...")
    result = clawdbot_add_job(
        url="https://www.linkedin.com/jobs/view/brand-designer-at-vumedi-4335836027/",
        title="Brand Designer",
        company="VuMedi",
        priority=8
    )
    print(result)
    
    # Get queue
    print("\n2. Current queue:")
    print(clawdbot_get_queue())
    
    # Get stats
    print("\n3. Stats:")
    print(clawdbot_get_stats())
    
    print("\n" + "=" * 60)
    print("✅ Job Queue Manager Ready")
    print("=" * 60)
