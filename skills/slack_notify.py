"""
Slack Notification Module - Sends job summaries and handles approval workflow
"""
import os
import sys
import json
import yaml
import subprocess
from typing import List, Dict, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def _load_env_from_user_scope(var_name: str) -> str:
    """Load environment variable from Windows User scope if not in current session."""
    value = os.environ.get(var_name)
    if value and not value.startswith('Clawdbot'):  # Ensure not corrupted
        return value
    
    if sys.platform == 'win32':
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', f'[Environment]::GetEnvironmentVariable("{var_name}", "User")'],
                capture_output=True, text=True
            )
            value = result.stdout.strip()
            # Only use if it looks like a valid token
            if value and (value.startswith('xoxb') or value.startswith('xapp') or value.startswith('sk-')):
                os.environ[var_name] = value
                return value
        except:
            pass
    return None


def load_config() -> dict:
    """Load configuration from config.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_slack_client() -> WebClient:
    """Initialize Slack client with bot token."""
    token = _load_env_from_user_scope('SLACK_BOT_TOKEN')
    if not token:
        raise ValueError("SLACK_BOT_TOKEN environment variable not set")
    return WebClient(token=token)


def create_job_block(job: Dict, index: int) -> List[Dict]:
    """
    Create Slack Block Kit blocks for a single job listing.
    """
    title = job.get('title', 'Unknown Position')
    company = job.get('company', 'Unknown Company')
    location = job.get('location', 'Unknown Location')
    match_score = job.get('match_score', {}).get('overall_score', 50)
    job_url = job.get('job_url', '#')
    category = job.get('category', 'general')
    
    # Match score emoji
    if match_score >= 80:
        score_emoji = "🟢"
    elif match_score >= 60:
        score_emoji = "🟡"
    else:
        score_emoji = "🔴"
    
    # Create description snippet
    description = job.get('description', '')
    snippet = description[:200] + "..." if len(description) > 200 else description
    
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{title}* – {company}\n📍 {location} | {score_emoji} Match: {match_score}%"
            },
            "accessory": {
                "type": "button",
                "text": {"type": "plain_text", "text": "View Job"},
                "url": job_url,
                "action_id": f"view_job_{index}"
            }
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"_{snippet}_"}
            ]
        },
        {
            "type": "actions",
            "block_id": f"job_actions_{index}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🤖 Auto Apply"},
                    "style": "primary",
                    "action_id": "auto_apply_job",
                    "value": json.dumps({
                        "index": index,
                        "title": title,
                        "company": company,
                        "job_url": job_url,
                        "description": description
                    })
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "👤 I'll Apply"},
                    "action_id": "manual_apply_job",
                    "value": json.dumps({
                        "index": index,
                        "title": title,
                        "company": company,
                        "job_url": job_url
                    })
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📄 Preview"},
                    "action_id": "preview_docs",
                    "value": json.dumps({
                        "index": index,
                        "title": title,
                        "company": company,
                        "description": description
                    })
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ Skip"},
                    "style": "danger",
                    "action_id": "decline_job",
                    "value": json.dumps({
                        "index": index,
                        "title": title,
                        "company": company,
                        "job_url": job_url
                    })
                }
            ]
        },
        {"type": "divider"}
    ]
    
    return blocks


def create_summary_message(jobs: List[Dict], date_str: str) -> List[Dict]:
    """
    Create the full Slack message with all job listings.
    """
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🎯 Job Matches for {date_str}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Found *{len(jobs)}* new job opportunities matching your profile!\n"
                        f"Review each listing and click *Approve* to apply or *Skip* to dismiss."
            }
        },
        {"type": "divider"}
    ]
    
    # Add each job
    for i, job in enumerate(jobs):
        blocks.extend(create_job_block(job, i))
    
    # Footer
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "💡 _Tip: I'll only apply to jobs you approve. Your materials are already tailored for each role!_"
            }
        ]
    })
    
    return blocks


def send_job_summary(
    jobs: List[Dict],
    user_id: Optional[str] = None,
    channel: Optional[str] = None
) -> Dict:
    """
    Send the daily job summary to Slack.
    
    Args:
        jobs: List of job dictionaries with match scores
        user_id: Slack user ID to DM (if no channel specified)
        channel: Slack channel ID to post to
    
    Returns:
        Slack API response
    """
    from datetime import datetime
    
    client = get_slack_client()
    config = load_config()
    
    date_str = datetime.now().strftime("%B %d, %Y")
    blocks = create_summary_message(jobs, date_str)
    
    try:
        # If no channel specified, try to open DM with user
        if not channel and user_id:
            dm_response = client.conversations_open(users=[user_id])
            channel = dm_response['channel']['id']
        
        if not channel:
            channel = config['slack'].get('channel')
        
        if not channel:
            raise ValueError("No channel or user_id specified for Slack notification")
        
        response = client.chat_postMessage(
            channel=channel,
            blocks=blocks,
            text=f"🎯 {len(jobs)} new job matches for {date_str}"  # Fallback text
        )
        
        print(f"Sent job summary to Slack: {len(jobs)} jobs")
        return {"success": True, "ts": response['ts'], "channel": channel}
        
    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}")
        return {"success": False, "error": str(e)}


def send_application_status(
    job_title: str,
    company: str,
    status: str,
    channel: str,
    thread_ts: Optional[str] = None
) -> Dict:
    """
    Send an application status update.
    """
    client = get_slack_client()
    
    status_emoji = {
        "applied": "✅",
        "failed": "❌",
        "pending": "⏳",
        "interview": "📞",
        "rejected": "🔴",
        "offer": "🎉"
    }
    
    emoji = status_emoji.get(status, "📋")
    
    try:
        response = client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"{emoji} *{status.title()}*: {job_title} at {company}"
        )
        return {"success": True, "ts": response['ts']}
        
    except SlackApiError as e:
        return {"success": False, "error": str(e)}


def send_preview_docs(
    channel: str,
    thread_ts: str,
    job_title: str,
    company: str,
    cover_letter: str,
    resume_summary: str
) -> Dict:
    """
    Send document previews in a thread.
    """
    client = get_slack_client()
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📄 Documents for {job_title} at {company}"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Tailored Summary:*\n{resume_summary}"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Cover Letter:*\n{cover_letter[:2000]}..."
                        if len(cover_letter) > 2000 else f"*Cover Letter:*\n{cover_letter}"
            }
        }
    ]
    
    try:
        response = client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            blocks=blocks,
            text=f"Documents for {job_title} at {company}"
        )
        return {"success": True, "ts": response['ts']}
        
    except SlackApiError as e:
        return {"success": False, "error": str(e)}


def update_job_status_in_message(
    channel: str,
    message_ts: str,
    job_index: int,
    new_status: str
) -> Dict:
    """
    Update a job's status in the original summary message.
    """
    client = get_slack_client()
    
    try:
        # Get the original message
        result = client.conversations_history(
            channel=channel,
            latest=message_ts,
            inclusive=True,
            limit=1
        )
        
        if not result['messages']:
            return {"success": False, "error": "Message not found"}
        
        original_blocks = result['messages'][0].get('blocks', [])
        
        # Find and update the relevant action block
        for block in original_blocks:
            if block.get('block_id') == f"job_actions_{job_index}":
                # Replace with status indicator
                block['elements'] = [{
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": f"{'✅ Approved' if new_status == 'approved' else '⏭️ Skipped'}"
                    },
                    "style": "primary" if new_status == 'approved' else None,
                    "action_id": "status_indicator",
                    "value": new_status
                }]
                break
        
        # Update the message
        response = client.chat_update(
            channel=channel,
            ts=message_ts,
            blocks=original_blocks
        )
        
        return {"success": True}
        
    except SlackApiError as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Test with sample data
    sample_jobs = [
        {
            "title": "Graphic Designer",
            "company": "ACME Corp",
            "location": "San Francisco, CA",
            "description": "Looking for a skilled graphic designer...",
            "job_url": "https://linkedin.com/jobs/123",
            "category": "graphic_design",
            "match_score": {"overall_score": 85}
        },
        {
            "title": "Brand Designer",
            "company": "Tech Startup",
            "location": "Remote",
            "description": "Join our creative team...",
            "job_url": "https://indeed.com/jobs/456",
            "category": "graphic_design",
            "match_score": {"overall_score": 72}
        }
    ]
    
    # Print the blocks for preview
    from datetime import datetime
    blocks = create_summary_message(sample_jobs, datetime.now().strftime("%B %d, %Y"))
    print(json.dumps(blocks, indent=2))
