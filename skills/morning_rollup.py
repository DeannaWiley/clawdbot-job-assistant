"""
Morning Rollup Module - Daily summary of job search progress + emails

Windows-compatible version that integrates with:
- Gmail (via gmail_handler.py)
- Job tracking (via track_status.py and job_history.py)
- Slack notifications

Run manually or schedule with Windows Task Scheduler.
"""
import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(__file__))

from gmail_handler import get_email_summary, get_job_emails, get_actionable_emails
from track_status import get_stats, get_pending_followups, get_applications_by_status
from job_history import get_history_stats, get_applied_jobs
from slack_notify import get_slack_client, load_config


def get_job_application_stats() -> Dict:
    """Get job application statistics for the rollup."""
    try:
        # From track_status
        stats = get_stats()
        followups = get_pending_followups(days_threshold=7)
        
        # From job_history
        history = get_history_stats()
        
        return {
            'total_applications': stats.get('total_applications', 0),
            'by_status': stats.get('by_status', {}),
            'average_match_score': stats.get('average_match_score', 0),
            'jobs_seen': history.get('total_jobs_seen', 0),
            'jobs_applied': history.get('total_applied', 0),
            'jobs_skipped': history.get('total_skipped', 0),
            'pending_followups': len(followups),
            'followup_list': followups[:5],  # Top 5 needing followup
        }
    except Exception as e:
        print(f"Error getting job stats: {e}")
        return {}


def get_recent_activity(days: int = 1) -> Dict:
    """Get recent job search activity."""
    try:
        from job_history import _load_history
        history = _load_history()
        
        cutoff = datetime.now() - timedelta(days=days)
        
        recent_seen = 0
        recent_applied = 0
        recent_skipped = 0
        
        for job_id, data in history.get('seen', {}).items():
            try:
                seen_date = datetime.fromisoformat(data.get('first_seen', ''))
                if seen_date > cutoff:
                    recent_seen += 1
            except:
                pass
        
        for job_id, data in history.get('applied', {}).items():
            try:
                applied_date = datetime.fromisoformat(data.get('applied_date', ''))
                if applied_date > cutoff:
                    recent_applied += 1
            except:
                pass
        
        for job_id, data in history.get('skipped', {}).items():
            try:
                skipped_date = datetime.fromisoformat(data.get('skipped_date', ''))
                if skipped_date > cutoff:
                    recent_skipped += 1
            except:
                pass
        
        return {
            'jobs_found_today': recent_seen,
            'applications_today': recent_applied,
            'skipped_today': recent_skipped,
        }
    except Exception as e:
        print(f"Error getting recent activity: {e}")
        return {}


def build_rollup_message() -> List[Dict]:
    """Build the morning rollup Slack message blocks."""
    now = datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    
    # Gather all data
    job_stats = get_job_application_stats()
    recent = get_recent_activity(days=1)
    email_summary = get_email_summary()
    actionable_emails = get_actionable_emails()
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"☀️ Good Morning! {date_str}",
                "emoji": True
            }
        },
        {"type": "divider"},
        
        # Job Search Progress Section
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📊 Job Search Progress*"
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Total Applications:*\n{job_stats.get('total_applications', 0)}"},
                {"type": "mrkdwn", "text": f"*Jobs Reviewed:*\n{job_stats.get('jobs_seen', 0)}"},
                {"type": "mrkdwn", "text": f"*Applied:*\n{job_stats.get('jobs_applied', 0)}"},
                {"type": "mrkdwn", "text": f"*Skipped:*\n{job_stats.get('jobs_skipped', 0)}"},
            ]
        },
    ]
    
    # Yesterday's Activity
    if recent:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📈 Last 24 Hours:* Found {recent.get('jobs_found_today', 0)} new jobs, "
                        f"Applied to {recent.get('applications_today', 0)}, "
                        f"Skipped {recent.get('skipped_today', 0)}"
            }
        })
    
    # Status Breakdown
    by_status = job_stats.get('by_status', {})
    if by_status:
        status_text = []
        status_emoji = {'applied': '🔵', 'interview': '🟢', 'offer': '🎉', 'rejected': '🔴', 'pending': '⏳'}
        for status, count in by_status.items():
            emoji = status_emoji.get(status.lower(), '📋')
            status_text.append(f"{emoji} {status.title()}: {count}")
        
        if status_text:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Application Status:*\n" + " | ".join(status_text)
                }
            })
    
    blocks.append({"type": "divider"})
    
    # Email Section
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*📧 Email Summary (Last 14 Days)*"
        }
    })
    
    blocks.append({
        "type": "section",
        "fields": [
            {"type": "mrkdwn", "text": f"*Interview Requests:*\n{email_summary.get('interview_requests', 0)}"},
            {"type": "mrkdwn", "text": f"*Application Confirmations:*\n{email_summary.get('applications_confirmed', 0)}"},
            {"type": "mrkdwn", "text": f"*Rejections:*\n{email_summary.get('rejections', 0)}"},
            {"type": "mrkdwn", "text": f"*Offers:*\n{email_summary.get('offers', 0)} 🎉"},
        ]
    })
    
    # Actionable Emails
    if actionable_emails:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*⚠️ {len(actionable_emails)} Emails Requiring Action:*"
            }
        })
        
        for email in actionable_emails[:5]:
            action = email['classification'].get('action_type', 'review')
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• *{email['subject'][:50]}*\n  From: {email['from'][:40]} | Action: {action}"
                }
            })
    
    # Follow-ups Needed
    followups = job_stats.get('followup_list', [])
    if followups:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📞 Follow-ups Needed ({job_stats.get('pending_followups', 0)} total):*"
            }
        })
        
        for app in followups[:3]:
            days = app.get('days_since_applied', 0)
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• {app.get('job_title', 'Unknown')} at {app.get('company', 'Unknown')} ({days} days)"
                }
            })
    
    # Footer
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"💡 _Next job search scheduled for 7 AM, 12 PM, and 5 PM today. "
                        f"Reply 'search now' to run immediately._"
            }
        ]
    })
    
    return blocks


def send_morning_rollup(channel: Optional[str] = None, user_id: Optional[str] = None) -> Dict:
    """Send the morning rollup to Slack."""
    try:
        client = get_slack_client()
        config = load_config()
        
        blocks = build_rollup_message()
        
        # Determine channel
        if not channel and user_id:
            dm_response = client.conversations_open(users=[user_id])
            channel = dm_response['channel']['id']
        
        if not channel:
            channel = config.get('slack', {}).get('channel')
        
        if not channel:
            return {"success": False, "error": "No channel specified"}
        
        response = client.chat_postMessage(
            channel=channel,
            blocks=blocks,
            text="☀️ Good Morning! Here's your daily job search rollup."
        )
        
        print(f"✅ Morning rollup sent to Slack")
        return {"success": True, "ts": response['ts'], "channel": channel}
        
    except Exception as e:
        print(f"❌ Error sending rollup: {e}")
        return {"success": False, "error": str(e)}


def run_rollup():
    """Run the morning rollup (for CLI/scheduled use)."""
    print("\n" + "="*50)
    print("☀️ MORNING ROLLUP")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    # Print summary to console
    job_stats = get_job_application_stats()
    email_summary = get_email_summary()
    recent = get_recent_activity(days=1)
    
    print("\n📊 Job Search Progress:")
    print(f"   Total Applications: {job_stats.get('total_applications', 0)}")
    print(f"   Jobs Reviewed: {job_stats.get('jobs_seen', 0)}")
    print(f"   Applied: {job_stats.get('jobs_applied', 0)}")
    print(f"   Skipped: {job_stats.get('jobs_skipped', 0)}")
    
    print(f"\n📈 Last 24 Hours:")
    print(f"   New Jobs Found: {recent.get('jobs_found_today', 0)}")
    print(f"   Applications: {recent.get('applications_today', 0)}")
    
    print(f"\n📧 Email Summary:")
    print(f"   Interview Requests: {email_summary.get('interview_requests', 0)}")
    print(f"   Rejections: {email_summary.get('rejections', 0)}")
    print(f"   Offers: {email_summary.get('offers', 0)}")
    
    # Send to Slack
    result = send_morning_rollup()
    
    return result


if __name__ == "__main__":
    run_rollup()
