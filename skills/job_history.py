"""
Job History Tracking Module

Prevents duplicate job notifications by tracking:
- Jobs we've seen (notified in Slack)
- Jobs we've applied to
- Jobs we've skipped/rejected

This ensures Clawdbot never asks you to review the same job twice.
"""
import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional
from pathlib import Path


# History file path
HISTORY_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'job_history.json')


def _load_history() -> Dict:
    """Load job history from file."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return _create_empty_history()
    return _create_empty_history()


def _save_history(history: Dict):
    """Save job history to file."""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, default=str)


def _create_empty_history() -> Dict:
    """Create empty history structure."""
    return {
        "seen": {},        # job_id -> {first_seen, last_seen, status, title, company}
        "applied": {},     # job_id -> {applied_date, title, company, job_url}
        "skipped": {},     # job_id -> {skipped_date, reason, title, company}
        "stats": {
            "total_seen": 0,
            "total_applied": 0,
            "total_skipped": 0,
            "last_search_date": None
        }
    }


def generate_job_id(job: Dict) -> str:
    """
    Generate a unique ID for a job based on title, company, and URL.
    This ensures the same job from different searches gets the same ID.
    """
    # Normalize the key components
    title = job.get('title', '').lower().strip()
    company = job.get('company', '').lower().strip()
    
    # Use URL if available, otherwise use title+company
    job_url = job.get('job_url', '')
    
    if job_url:
        # Extract unique part of URL (remove tracking params)
        url_key = job_url.split('?')[0].lower()
        key = f"{title}|{company}|{url_key}"
    else:
        key = f"{title}|{company}"
    
    return hashlib.md5(key.encode()).hexdigest()[:16]


def is_job_seen(job: Dict) -> bool:
    """Check if we've already seen/notified about this job."""
    history = _load_history()
    job_id = generate_job_id(job)
    return job_id in history['seen']


def is_job_applied(job: Dict) -> bool:
    """Check if we've already applied to this job."""
    history = _load_history()
    job_id = generate_job_id(job)
    return job_id in history['applied']


def is_job_skipped(job: Dict) -> bool:
    """Check if we've already skipped this job."""
    history = _load_history()
    job_id = generate_job_id(job)
    return job_id in history['skipped']


def get_job_status(job: Dict) -> Optional[str]:
    """
    Get the status of a job.
    Returns: 'applied', 'skipped', 'seen', or None if never seen.
    """
    history = _load_history()
    job_id = generate_job_id(job)
    
    if job_id in history['applied']:
        return 'applied'
    if job_id in history['skipped']:
        return 'skipped'
    if job_id in history['seen']:
        return 'seen'
    return None


def mark_job_seen(job: Dict, status: str = 'pending_review') -> str:
    """
    Mark a job as seen (notified in Slack).
    
    Args:
        job: Job dictionary
        status: Initial status (pending_review, notified)
    
    Returns:
        The job ID
    """
    history = _load_history()
    job_id = generate_job_id(job)
    now = datetime.now().isoformat()
    
    if job_id not in history['seen']:
        history['seen'][job_id] = {
            'first_seen': now,
            'last_seen': now,
            'status': status,
            'title': job.get('title', ''),
            'company': job.get('company', ''),
            'location': job.get('location', ''),
            'job_url': job.get('job_url', ''),
            'notified_count': 1
        }
        history['stats']['total_seen'] += 1
    else:
        history['seen'][job_id]['last_seen'] = now
        history['seen'][job_id]['notified_count'] += 1
    
    history['stats']['last_search_date'] = now
    _save_history(history)
    return job_id


def mark_job_applied(job: Dict, method: str = 'manual', notes: str = '') -> str:
    """
    Mark a job as applied to.
    
    Args:
        job: Job dictionary
        method: Application method (manual, automated, easy_apply)
        notes: Any additional notes
    
    Returns:
        The job ID
    """
    history = _load_history()
    job_id = generate_job_id(job)
    now = datetime.now().isoformat()
    
    history['applied'][job_id] = {
        'applied_date': now,
        'title': job.get('title', ''),
        'company': job.get('company', ''),
        'location': job.get('location', ''),
        'job_url': job.get('job_url', ''),
        'method': method,
        'notes': notes,
        'status': 'applied'
    }
    
    # Update seen status
    if job_id in history['seen']:
        history['seen'][job_id]['status'] = 'applied'
    
    history['stats']['total_applied'] += 1
    _save_history(history)
    return job_id


def mark_job_skipped(job: Dict, reason: str = 'user_declined') -> str:
    """
    Mark a job as skipped/rejected.
    
    Args:
        job: Job dictionary
        reason: Why it was skipped (user_declined, not_relevant, deal_breaker, etc.)
    
    Returns:
        The job ID
    """
    history = _load_history()
    job_id = generate_job_id(job)
    now = datetime.now().isoformat()
    
    history['skipped'][job_id] = {
        'skipped_date': now,
        'title': job.get('title', ''),
        'company': job.get('company', ''),
        'reason': reason
    }
    
    # Update seen status
    if job_id in history['seen']:
        history['seen'][job_id]['status'] = 'skipped'
    
    history['stats']['total_skipped'] += 1
    _save_history(history)
    return job_id


def filter_new_jobs(jobs: List[Dict]) -> List[Dict]:
    """
    Filter out jobs we've already seen, applied to, or skipped.
    
    Args:
        jobs: List of job dictionaries
    
    Returns:
        List of jobs that are NEW (never seen before)
    """
    history = _load_history()
    new_jobs = []
    
    seen_ids = set(history['seen'].keys())
    applied_ids = set(history['applied'].keys())
    skipped_ids = set(history['skipped'].keys())
    
    all_known_ids = seen_ids | applied_ids | skipped_ids
    
    for job in jobs:
        job_id = generate_job_id(job)
        if job_id not in all_known_ids:
            new_jobs.append(job)
    
    return new_jobs


def get_history_stats() -> Dict:
    """Get statistics about job history."""
    history = _load_history()
    
    return {
        'total_jobs_seen': len(history['seen']),
        'total_applied': len(history['applied']),
        'total_skipped': len(history['skipped']),
        'pending_review': sum(
            1 for j in history['seen'].values() 
            if j.get('status') == 'pending_review'
        ),
        'last_search': history['stats'].get('last_search_date'),
    }


def get_applied_jobs() -> List[Dict]:
    """Get list of all applied jobs."""
    history = _load_history()
    return list(history['applied'].values())


def get_pending_jobs() -> List[Dict]:
    """Get jobs that are seen but not yet applied/skipped."""
    history = _load_history()
    
    applied_ids = set(history['applied'].keys())
    skipped_ids = set(history['skipped'].keys())
    
    pending = []
    for job_id, job_data in history['seen'].items():
        if job_id not in applied_ids and job_id not in skipped_ids:
            pending.append({**job_data, 'job_id': job_id})
    
    return pending


def clear_old_history(days: int = 90):
    """
    Clear jobs older than specified days from 'seen' history.
    Applied and skipped jobs are kept permanently.
    """
    history = _load_history()
    cutoff = datetime.now() - timedelta(days=days)
    
    # Only clear from 'seen', not applied or skipped
    jobs_to_remove = []
    for job_id, job_data in history['seen'].items():
        # Don't remove if applied or skipped
        if job_id in history['applied'] or job_id in history['skipped']:
            continue
        
        try:
            first_seen = datetime.fromisoformat(job_data['first_seen'])
            if first_seen < cutoff:
                jobs_to_remove.append(job_id)
        except (ValueError, KeyError):
            continue
    
    for job_id in jobs_to_remove:
        del history['seen'][job_id]
    
    _save_history(history)
    return len(jobs_to_remove)


def export_applied_jobs_csv(output_path: str = None) -> str:
    """Export applied jobs to CSV for backup/review."""
    import csv
    
    if not output_path:
        output_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 
            f'applied_jobs_{datetime.now().strftime("%Y%m%d")}.csv'
        )
    
    history = _load_history()
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        if history['applied']:
            writer = csv.DictWriter(f, fieldnames=list(list(history['applied'].values())[0].keys()))
            writer.writeheader()
            writer.writerows(history['applied'].values())
    
    return output_path


if __name__ == "__main__":
    # Test the module
    print("Job History Module Test")
    print("=" * 50)
    
    # Test with sample jobs
    sample_jobs = [
        {"title": "Graphic Designer", "company": "ACME Corp", "job_url": "https://example.com/1"},
        {"title": "Brand Designer", "company": "Tech Inc", "job_url": "https://example.com/2"},
        {"title": "Graphic Designer", "company": "ACME Corp", "job_url": "https://example.com/1"},  # Duplicate
    ]
    
    print(f"\nFiltering {len(sample_jobs)} jobs...")
    new_jobs = filter_new_jobs(sample_jobs)
    print(f"New jobs: {len(new_jobs)}")
    
    # Mark first job as seen
    if new_jobs:
        job_id = mark_job_seen(new_jobs[0])
        print(f"Marked as seen: {job_id}")
    
    # Get stats
    stats = get_history_stats()
    print(f"\nHistory Stats: {json.dumps(stats, indent=2)}")
