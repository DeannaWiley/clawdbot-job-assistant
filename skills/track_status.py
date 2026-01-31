"""
Application Tracking Module - Logs and tracks job application status
"""
import os
import csv
import json
import yaml
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


def load_config() -> dict:
    """Load configuration from config.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_log_path() -> str:
    """Get the path to the application log file."""
    config = load_config()
    log_file = config['tracking']['log_file']
    
    # Handle relative paths
    if not os.path.isabs(log_file):
        log_file = os.path.join(os.path.dirname(__file__), '..', log_file)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    return log_file


def init_log_file():
    """Initialize the log file with headers if it doesn't exist."""
    log_path = get_log_path()
    
    if not os.path.exists(log_path):
        headers = [
            'id',
            'job_title',
            'company',
            'location',
            'job_url',
            'category',
            'match_score',
            'status',
            'applied_date',
            'last_updated',
            'application_method',
            'notes',
            'response_date',
            'interview_date',
        ]
        
        with open(log_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        
        print(f"Created new application log: {log_path}")


def generate_job_id(job: Dict) -> str:
    """Generate a unique ID for a job based on title, company, and URL."""
    import hashlib
    
    key = f"{job.get('title', '')}|{job.get('company', '')}|{job.get('job_url', '')}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def log_application(
    job: Dict,
    status: str = 'applied',
    method: str = 'manual',
    notes: str = ''
) -> Dict:
    """
    Log a new job application.
    
    Args:
        job: Job dictionary with title, company, location, etc.
        status: Application status (applied, pending, interview, rejected, offer)
        method: How the application was submitted
        notes: Any additional notes
    
    Returns:
        Dictionary with the logged entry
    """
    init_log_file()
    log_path = get_log_path()
    
    job_id = generate_job_id(job)
    now = datetime.now().isoformat()
    
    entry = {
        'id': job_id,
        'job_title': job.get('title', ''),
        'company': job.get('company', ''),
        'location': job.get('location', ''),
        'job_url': job.get('job_url', ''),
        'category': job.get('category', ''),
        'match_score': job.get('match_score', {}).get('overall_score', ''),
        'status': status,
        'applied_date': now,
        'last_updated': now,
        'application_method': method,
        'notes': notes,
        'response_date': '',
        'interview_date': '',
    }
    
    with open(log_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=entry.keys())
        writer.writerow(entry)
    
    print(f"Logged application: {entry['job_title']} at {entry['company']}")
    return entry


def update_status(
    job_id: str,
    new_status: str,
    notes: str = '',
    response_date: str = '',
    interview_date: str = ''
) -> Optional[Dict]:
    """
    Update the status of an existing application.
    
    Args:
        job_id: The job ID to update
        new_status: New status value
        notes: Optional notes to append
        response_date: Date of response from employer
        interview_date: Scheduled interview date
    
    Returns:
        Updated entry or None if not found
    """
    log_path = get_log_path()
    
    if not os.path.exists(log_path):
        return None
    
    # Read all entries
    entries = []
    updated_entry = None
    
    with open(log_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        for row in reader:
            if row['id'] == job_id:
                row['status'] = new_status
                row['last_updated'] = datetime.now().isoformat()
                
                if notes:
                    existing_notes = row.get('notes', '')
                    row['notes'] = f"{existing_notes}; {notes}" if existing_notes else notes
                
                if response_date:
                    row['response_date'] = response_date
                
                if interview_date:
                    row['interview_date'] = interview_date
                
                updated_entry = row
            
            entries.append(row)
    
    # Write back
    if updated_entry:
        with open(log_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(entries)
        
        print(f"Updated status for {updated_entry['job_title']}: {new_status}")
    
    return updated_entry


def get_all_applications() -> List[Dict]:
    """Get all logged applications."""
    log_path = get_log_path()
    
    if not os.path.exists(log_path):
        return []
    
    with open(log_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_applications_by_status(status: str) -> List[Dict]:
    """Get applications filtered by status."""
    all_apps = get_all_applications()
    return [app for app in all_apps if app['status'].lower() == status.lower()]


def get_application_by_id(job_id: str) -> Optional[Dict]:
    """Get a specific application by ID."""
    all_apps = get_all_applications()
    for app in all_apps:
        if app['id'] == job_id:
            return app
    return None


def search_applications(query: str) -> List[Dict]:
    """Search applications by title or company name."""
    all_apps = get_all_applications()
    query_lower = query.lower()
    
    return [
        app for app in all_apps
        if query_lower in app.get('job_title', '').lower()
        or query_lower in app.get('company', '').lower()
    ]


def get_stats() -> Dict:
    """Get application statistics."""
    all_apps = get_all_applications()
    
    status_counts = {}
    for app in all_apps:
        status = app.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    category_counts = {}
    for app in all_apps:
        category = app.get('category', 'unknown')
        category_counts[category] = category_counts.get(category, 0) + 1
    
    # Calculate average match score
    scores = [
        int(app['match_score']) 
        for app in all_apps 
        if app.get('match_score') and app['match_score'].isdigit()
    ]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    return {
        "total_applications": len(all_apps),
        "by_status": status_counts,
        "by_category": category_counts,
        "average_match_score": round(avg_score, 1),
    }


def get_pending_followups(days_threshold: int = 14) -> List[Dict]:
    """
    Get applications that may need follow-up.
    
    Returns applications in 'applied' status older than the threshold.
    """
    from datetime import timedelta
    
    all_apps = get_all_applications()
    threshold_date = datetime.now() - timedelta(days=days_threshold)
    
    pending = []
    for app in all_apps:
        if app.get('status', '').lower() != 'applied':
            continue
        
        applied_date = app.get('applied_date', '')
        if not applied_date:
            continue
        
        try:
            applied_dt = datetime.fromisoformat(applied_date)
            if applied_dt < threshold_date:
                app['days_since_applied'] = (datetime.now() - applied_dt).days
                pending.append(app)
        except ValueError:
            continue
    
    return sorted(pending, key=lambda x: x.get('days_since_applied', 0), reverse=True)


def format_status_report() -> str:
    """Generate a formatted status report for Slack or display."""
    stats = get_stats()
    
    report = f"""
📊 **Application Status Report**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Total Applications:** {stats['total_applications']}
**Average Match Score:** {stats['average_match_score']}%

**By Status:**
"""
    
    status_emoji = {
        'applied': '🔵',
        'interview': '🟢',
        'offer': '🎉',
        'rejected': '🔴',
        'pending': '⏳',
    }
    
    for status, count in stats['by_status'].items():
        emoji = status_emoji.get(status.lower(), '📋')
        report += f"  {emoji} {status.title()}: {count}\n"
    
    report += "\n**By Category:**\n"
    for category, count in stats['by_category'].items():
        report += f"  • {category.replace('_', ' ').title()}: {count}\n"
    
    # Add pending follow-ups
    followups = get_pending_followups()
    if followups:
        report += f"\n⚠️ **Need Follow-up ({len(followups)}):**\n"
        for app in followups[:5]:  # Show top 5
            report += f"  • {app['job_title']} at {app['company']} ({app['days_since_applied']} days)\n"
    
    return report


if __name__ == "__main__":
    # Test the tracking system
    init_log_file()
    
    # Log a test application
    test_job = {
        'title': 'Graphic Designer',
        'company': 'Test Corp',
        'location': 'San Francisco, CA',
        'job_url': 'https://example.com/job/123',
        'category': 'graphic_design',
        'match_score': {'overall_score': 85}
    }
    
    entry = log_application(test_job, status='applied', method='manual')
    print(f"\nLogged entry: {entry['id']}")
    
    # Get stats
    stats = get_stats()
    print(f"\nStats: {json.dumps(stats, indent=2)}")
    
    # Print report
    print(format_status_report())
