"""
Job Approval Workflow - Handles Slack-based job approval, ignore lists, and auto-application
"""
import os
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


def get_ignore_list_path() -> str:
    """Get path to the ignore list file."""
    return os.path.join(os.path.dirname(__file__), '..', 'data', 'ignored_jobs.json')


def get_approved_jobs_path() -> str:
    """Get path to the approved jobs file."""
    return os.path.join(os.path.dirname(__file__), '..', 'data', 'approved_jobs.json')


def get_applied_jobs_path() -> str:
    """Get path to the applied jobs tracking file."""
    return os.path.join(os.path.dirname(__file__), '..', 'data', 'applied_jobs.json')


def load_ignore_list() -> List[Dict]:
    """Load the list of ignored jobs."""
    path = get_ignore_list_path()
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return []


def save_ignore_list(jobs: List[Dict]):
    """Save the ignore list."""
    path = get_ignore_list_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(jobs, f, indent=2)


def load_approved_jobs() -> List[Dict]:
    """Load the list of approved jobs."""
    path = get_approved_jobs_path()
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return []


def save_approved_jobs(jobs: List[Dict]):
    """Save the approved jobs list."""
    path = get_approved_jobs_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(jobs, f, indent=2)


def load_applied_jobs() -> List[Dict]:
    """Load the list of applied jobs."""
    path = get_applied_jobs_path()
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return []


def save_applied_jobs(jobs: List[Dict]):
    """Save the applied jobs list."""
    path = get_applied_jobs_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(jobs, f, indent=2)


def is_job_ignored(job_url: str, company: str = None, title: str = None) -> bool:
    """
    Check if a job is in the ignore list.
    Matches by URL, or by company+title combination.
    """
    ignore_list = load_ignore_list()
    
    for ignored in ignore_list:
        # Match by URL
        if job_url and ignored.get('job_url') == job_url:
            return True
        
        # Match by company+title
        if company and title:
            if (ignored.get('company', '').lower() == company.lower() and 
                ignored.get('title', '').lower() == title.lower()):
                return True
    
    return False


def is_job_already_applied(job_url: str) -> bool:
    """Check if we've already applied to this job."""
    applied = load_applied_jobs()
    return any(j.get('job_url') == job_url for j in applied)


def add_to_ignore_list(
    job_url: str,
    title: str,
    company: str,
    reason: Optional[str] = None
) -> bool:
    """
    Add a job to the ignore list.
    
    Args:
        job_url: URL of the job posting
        title: Job title
        company: Company name
        reason: Optional reason for ignoring
    
    Returns:
        True if added successfully
    """
    ignore_list = load_ignore_list()
    
    # Check if already ignored
    if is_job_ignored(job_url, company, title):
        return False
    
    ignore_list.append({
        "job_url": job_url,
        "title": title,
        "company": company,
        "reason": reason,
        "ignored_at": datetime.now().isoformat(),
    })
    
    save_ignore_list(ignore_list)
    print(f"❌ Added to ignore list: {title} at {company}")
    return True


def remove_from_ignore_list(job_url: str) -> bool:
    """Remove a job from the ignore list."""
    ignore_list = load_ignore_list()
    original_len = len(ignore_list)
    
    ignore_list = [j for j in ignore_list if j.get('job_url') != job_url]
    
    if len(ignore_list) < original_len:
        save_ignore_list(ignore_list)
        return True
    return False


def approve_job(
    job_url: str,
    title: str,
    company: str,
    job_data: Optional[Dict] = None
) -> Dict:
    """
    Approve a job for application.
    
    Args:
        job_url: URL of the job posting
        title: Job title
        company: Company name
        job_data: Full job data dictionary
    
    Returns:
        Approval result with next steps
    """
    # Check if already applied
    if is_job_already_applied(job_url):
        return {
            "success": False,
            "error": "Already applied to this job",
            "status": "already_applied"
        }
    
    # Remove from ignore list if present
    remove_from_ignore_list(job_url)
    
    # Add to approved list
    approved = load_approved_jobs()
    
    approval_entry = {
        "job_url": job_url,
        "title": title,
        "company": company,
        "approved_at": datetime.now().isoformat(),
        "status": "approved",
        "job_data": job_data or {}
    }
    
    approved.append(approval_entry)
    save_approved_jobs(approved)
    
    print(f"✅ Approved: {title} at {company}")
    
    return {
        "success": True,
        "status": "approved",
        "message": f"Job approved! Ready to generate documents and apply.",
        "next_steps": [
            "Generate tailored resume",
            "Generate cover letter",
            "Apply to job"
        ]
    }


def deny_job(
    job_url: str,
    title: str,
    company: str,
    reason: Optional[str] = None
) -> Dict:
    """
    Deny/skip a job and add to ignore list.
    
    Args:
        job_url: URL of the job posting
        title: Job title
        company: Company name
        reason: Reason for denying
    
    Returns:
        Denial result
    """
    add_to_ignore_list(job_url, title, company, reason)
    
    return {
        "success": True,
        "status": "denied",
        "message": f"Job skipped and added to ignore list."
    }


def record_application(
    job_url: str,
    title: str,
    company: str,
    application_method: str,
    documents_generated: Dict,
    success: bool,
    error: Optional[str] = None
) -> Dict:
    """
    Record a job application in the tracking system.
    
    Args:
        job_url: URL of the job posting
        title: Job title
        company: Company name
        application_method: How applied (auto, manual, email)
        documents_generated: Paths to generated documents
        success: Whether application was successful
        error: Error message if failed
    """
    applied = load_applied_jobs()
    
    application_entry = {
        "job_url": job_url,
        "title": title,
        "company": company,
        "applied_at": datetime.now().isoformat(),
        "method": application_method,
        "documents": documents_generated,
        "success": success,
        "error": error,
        "status": "applied" if success else "failed",
        "follow_up_date": None,
        "response_received": False
    }
    
    applied.append(application_entry)
    save_applied_jobs(applied)
    
    # Remove from approved list
    approved = load_approved_jobs()
    approved = [j for j in approved if j.get('job_url') != job_url]
    save_approved_jobs(approved)
    
    if success:
        print(f"✅ Applied: {title} at {company}")
    else:
        print(f"❌ Application failed: {title} at {company} - {error}")
    
    return application_entry


def get_pending_approvals() -> List[Dict]:
    """Get jobs that have been found but not yet approved/denied."""
    approved = load_approved_jobs()
    return [j for j in approved if j.get('status') == 'approved']


def get_application_stats() -> Dict:
    """Get statistics about applications."""
    applied = load_applied_jobs()
    ignored = load_ignore_list()
    approved = load_approved_jobs()
    
    successful = [j for j in applied if j.get('success')]
    failed = [j for j in applied if not j.get('success')]
    
    return {
        "total_applied": len(applied),
        "successful": len(successful),
        "failed": len(failed),
        "pending_approval": len([j for j in approved if j.get('status') == 'approved']),
        "ignored": len(ignored),
        "this_week": len([
            j for j in applied 
            if datetime.fromisoformat(j.get('applied_at', '2000-01-01')).date() >= 
               (datetime.now().date() - __import__('datetime').timedelta(days=7))
        ])
    }


def process_slack_action(action_type: str, job_data: Dict) -> Dict:
    """
    Process a Slack button action (approve/deny).
    
    Args:
        action_type: "approve" or "deny"
        job_data: Dictionary with job_url, title, company
    
    Returns:
        Result of the action
    """
    job_url = job_data.get('job_url', '')
    title = job_data.get('title', '')
    company = job_data.get('company', '')
    
    if action_type == "approve":
        return approve_job(job_url, title, company, job_data)
    elif action_type == "deny" or action_type == "skip":
        return deny_job(job_url, title, company)
    else:
        return {"success": False, "error": f"Unknown action: {action_type}"}


def filter_jobs_against_ignore_list(jobs: List[Dict]) -> List[Dict]:
    """
    Filter out jobs that are in the ignore list or already applied.
    
    Args:
        jobs: List of job dictionaries
    
    Returns:
        Filtered list with ignored/applied jobs removed
    """
    filtered = []
    
    for job in jobs:
        job_url = job.get('job_url', '')
        company = job.get('company', '')
        title = job.get('title', '')
        
        if is_job_ignored(job_url, company, title):
            continue
        
        if is_job_already_applied(job_url):
            continue
        
        filtered.append(job)
    
    return filtered


async def process_approved_job(job_data: Dict) -> Dict:
    """
    Process an approved job - generate documents and apply.
    
    Args:
        job_data: Full job data dictionary
    
    Returns:
        Application result
    """
    from document_generator import generate_application_documents
    from apply_job import apply_to_job
    from gmail_handler import get_email_summary
    
    job_url = job_data.get('job_url', '')
    title = job_data.get('title', '')
    company = job_data.get('company', '')
    description = job_data.get('description', '')
    
    print(f"\n🚀 Processing approved job: {title} at {company}")
    
    # Generate documents
    print("  📝 Generating application documents...")
    docs = generate_application_documents(
        job_title=title,
        company=company,
        job_description=description,
        output_format="all"
    )
    
    # Apply to job
    print("  📤 Applying to job...")
    application_result = await apply_to_job(
        job=job_data,
        tailored_resume={"tailored_summary": docs.get('tailored_summary', '')},
        cover_letter={"cover_letter": docs.get('cover_letter', '')},
        resume_path=docs.get('files', {}).get('resume_pdf')
    )
    
    # Record application
    record_application(
        job_url=job_url,
        title=title,
        company=company,
        application_method=application_result.get('platform', 'manual'),
        documents_generated=docs.get('files', {}),
        success=application_result.get('success', False),
        error=application_result.get('error')
    )
    
    return {
        "job": {"title": title, "company": company, "url": job_url},
        "documents": docs.get('files', {}),
        "application_result": application_result
    }


def send_job_for_approval(job: Dict) -> Dict:
    """
    Send a job to Slack for user approval.
    
    Args:
        job: Job dictionary with title, company, url, description, match_score
    
    Returns:
        Slack message result
    """
    from slack_notify import get_slack_client, create_job_block
    
    # Filter against ignore list first
    if is_job_ignored(job.get('job_url'), job.get('company'), job.get('title')):
        return {"success": False, "reason": "Job is in ignore list"}
    
    if is_job_already_applied(job.get('job_url')):
        return {"success": False, "reason": "Already applied"}
    
    client = get_slack_client()
    config = load_config()
    
    blocks = create_job_block(job, 0)
    
    try:
        # Try to find user's DM channel
        response = client.conversations_list(types="im")
        channels = response.get('channels', [])
        
        if channels:
            channel = channels[0]['id']
        else:
            channel = config['slack'].get('channel', '')
        
        if not channel:
            return {"success": False, "error": "No Slack channel configured"}
        
        result = client.chat_postMessage(
            channel=channel,
            blocks=blocks,
            text=f"New job match: {job.get('title')} at {job.get('company')}"
        )
        
        return {
            "success": True,
            "channel": channel,
            "ts": result.get('ts'),
            "message": "Job sent for approval"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "stats":
            stats = get_application_stats()
            print("\n📊 Application Statistics")
            print("=" * 40)
            print(f"  Total Applied: {stats['total_applied']}")
            print(f"  Successful: {stats['successful']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Pending Approval: {stats['pending_approval']}")
            print(f"  Ignored: {stats['ignored']}")
            print(f"  This Week: {stats['this_week']}")
        
        elif command == "ignore-list":
            ignored = load_ignore_list()
            print(f"\n❌ Ignored Jobs ({len(ignored)})")
            print("=" * 40)
            for job in ignored[-10:]:
                print(f"  • {job.get('title')} at {job.get('company')}")
                if job.get('reason'):
                    print(f"    Reason: {job.get('reason')}")
        
        elif command == "pending":
            pending = get_pending_approvals()
            print(f"\n⏳ Pending Approvals ({len(pending)})")
            print("=" * 40)
            for job in pending:
                print(f"  • {job.get('title')} at {job.get('company')}")
        
        else:
            print(f"Unknown command: {command}")
            print("Commands: stats, ignore-list, pending")
    else:
        print("Job Approval Workflow")
        print("Commands: stats, ignore-list, pending")
