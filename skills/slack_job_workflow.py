"""
Enhanced Slack Job Workflow - Sends jobs with previews and handles Approve/Decline/Manual buttons
"""
import os
import sys
import json
import yaml
import subprocess
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def _load_env_from_user_scope(var_name: str) -> str:
    """Load environment variable from Windows User scope if not in current session."""
    value = os.environ.get(var_name)
    if value and not value.startswith('Clawdbot'):
        return value
    
    if sys.platform == 'win32':
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', f'[Environment]::GetEnvironmentVariable("{var_name}", "User")'],
                capture_output=True, text=True
            )
            value = result.stdout.strip()
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


def get_channel_id(channel_name: str) -> str:
    """Get channel ID from channel name."""
    client = get_slack_client()
    
    # Remove # if present
    channel_name = channel_name.lstrip('#')
    
    try:
        # List all channels
        result = client.conversations_list(types="public_channel,private_channel")
        for channel in result.get('channels', []):
            if channel['name'] == channel_name:
                return channel['id']
        
        # If not found, return the name (might be an ID already)
        return channel_name
    except SlackApiError as e:
        print(f"Error getting channel ID: {e}")
        return channel_name


def generate_job_preview(job: Dict) -> Dict:
    """
    Generate tailored resume summary and cover letter preview for a job.
    Returns dict with resume_preview and cover_letter_preview.
    """
    from tailor_resume import tailor_resume
    from write_cover_letter import generate_cover_letter
    
    # Load resume
    resume_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'base_resume.txt')
    try:
        with open(resume_path, 'r') as f:
            resume_text = f.read()
    except:
        resume_text = "Resume not found"
    
    title = job.get('title', 'Position')
    company = job.get('company', 'Company')
    description = job.get('description', '')
    
    try:
        # Generate tailored resume
        tailored = tailor_resume(resume_text, title, company, description)
        resume_preview = tailored.get('tailored_summary', 'Unable to generate preview')
        
        # Generate cover letter
        config = load_config()
        cover_letter = generate_cover_letter(
            resume_text=resume_text,
            job_title=title,
            company=company,
            job_description=description,
            user_name=config['user']['name']
        )
        # Truncate for preview
        cover_letter_preview = cover_letter[:800] + "..." if len(cover_letter) > 800 else cover_letter
        
        return {
            "resume_preview": resume_preview,
            "cover_letter_preview": cover_letter_preview,
            "match_score": tailored.get('match_score', {}).get('overall_score', 50)
        }
    except Exception as e:
        print(f"Error generating preview: {e}")
        return {
            "resume_preview": f"Preview generation failed: {str(e)[:100]}",
            "cover_letter_preview": "Preview generation failed",
            "match_score": 50
        }


def create_job_message_blocks(job: Dict, index: int, include_preview: bool = True) -> List[Dict]:
    """
    Create Slack Block Kit blocks for a job with 3 action buttons:
    - ✅ Auto Apply (Approve)
    - ❌ Decline (Skip and add to ignore list)
    - 👤 Manual Apply (User will apply themselves)
    """
    title = job.get('title', 'Unknown Position')
    company = job.get('company', 'Unknown Company')
    location = job.get('location', 'Unknown Location')
    job_url = job.get('job_url', '#')
    description = job.get('description', '')
    
    # Get or generate preview
    resume_preview = job.get('resume_preview', '')
    cover_letter_preview = job.get('cover_letter_preview', '')
    match_score = job.get('match_score', 50)
    if isinstance(match_score, dict):
        match_score = match_score.get('overall_score', 50)
    
    # Match score emoji
    if match_score >= 80:
        score_emoji = "🟢"
        score_text = "Excellent Match"
    elif match_score >= 60:
        score_emoji = "🟡"
        score_text = "Good Match"
    else:
        score_emoji = "🔴"
        score_text = "Partial Match"
    
    # Create description snippet
    desc_snippet = description[:300] + "..." if len(description) > 300 else description
    
    # Job data for button actions
    job_data = json.dumps({
        "index": index,
        "title": title,
        "company": company,
        "job_url": job_url,
        "location": location
    })
    
    blocks = [
        # Header with job title and company
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📋 {title}",
                "emoji": True
            }
        },
        # Company, location, match score
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*🏢 Company:*\n{company}"},
                {"type": "mrkdwn", "text": f"*📍 Location:*\n{location}"},
                {"type": "mrkdwn", "text": f"*{score_emoji} Match Score:*\n{match_score}% - {score_text}"},
                {"type": "mrkdwn", "text": f"*🔗 Job Link:*\n<{job_url}|View Original Posting>"}
            ]
        },
        # Job description
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📝 Job Description:*\n_{desc_snippet}_"
            }
        },
        {"type": "divider"},
    ]
    
    # Add resume preview if available
    if include_preview and resume_preview:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📄 Tailored Resume Summary:*\n```{resume_preview[:500]}{'...' if len(resume_preview) > 500 else ''}```"
            }
        })
    
    # Add cover letter preview if available
    if include_preview and cover_letter_preview:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*✉️ Cover Letter Preview:*\n```{cover_letter_preview[:500]}{'...' if len(cover_letter_preview) > 500 else ''}```"
            }
        })
    
    # Action buttons - 3 options as requested
    blocks.append({
        "type": "actions",
        "block_id": f"job_actions_{index}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Auto Apply", "emoji": True},
                "style": "primary",
                "action_id": "auto_apply_job",
                "value": job_data,
                "confirm": {
                    "title": {"type": "plain_text", "text": "Confirm Auto Apply"},
                    "text": {"type": "mrkdwn", "text": f"Clawdbot will automatically apply to *{title}* at *{company}* using the tailored resume and cover letter shown above.\n\nProceed?"},
                    "confirm": {"type": "plain_text", "text": "Yes, Apply"},
                    "deny": {"type": "plain_text", "text": "Cancel"}
                }
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "❌ Decline", "emoji": True},
                "style": "danger",
                "action_id": "decline_job",
                "value": job_data
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "👤 Manual Apply", "emoji": True},
                "action_id": "manual_apply_job",
                "value": job_data
            }
        ]
    })
    
    blocks.append({"type": "divider"})
    
    return blocks


def send_job_to_slack(
    job: Dict,
    channel: Optional[str] = None,
    generate_preview: bool = True
) -> Dict:
    """
    Send a single job to Slack with previews and action buttons.
    
    Args:
        job: Job dictionary with title, company, location, job_url, description
        channel: Slack channel (defaults to config)
        generate_preview: Whether to generate resume/cover letter previews
    
    Returns:
        Slack API response dict
    """
    client = get_slack_client()
    config = load_config()
    
    # Get channel
    if not channel:
        channel = config['slack'].get('channel', '#all-job-hunt-ai')
    
    channel_id = get_channel_id(channel)
    
    # Generate previews if requested
    if generate_preview and not job.get('resume_preview'):
        print(f"  Generating preview for: {job.get('title')} at {job.get('company')}")
        preview = generate_job_preview(job)
        job['resume_preview'] = preview['resume_preview']
        job['cover_letter_preview'] = preview['cover_letter_preview']
        job['match_score'] = preview['match_score']
    
    # Create message blocks
    blocks = create_job_message_blocks(job, index=0, include_preview=True)
    
    try:
        response = client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            text=f"New Job: {job.get('title')} at {job.get('company')}"
        )
        
        print(f"✅ Sent to Slack: {job.get('title')} at {job.get('company')}")
        return {
            "success": True,
            "channel": channel_id,
            "ts": response.get('ts'),
            "job": job
        }
        
    except SlackApiError as e:
        print(f"❌ Slack error: {e.response.get('error', str(e))}")
        return {"success": False, "error": str(e)}


def send_jobs_batch_to_slack(
    jobs: List[Dict],
    channel: Optional[str] = None,
    max_jobs: int = 10
) -> List[Dict]:
    """
    Send multiple jobs to Slack channel with previews.
    Each job gets its own message with action buttons.
    
    Args:
        jobs: List of job dictionaries
        channel: Slack channel
        max_jobs: Maximum jobs to send (to avoid spam)
    
    Returns:
        List of results for each job
    """
    client = get_slack_client()
    config = load_config()
    
    if not channel:
        channel = config['slack'].get('channel', '#all-job-hunt-ai')
    
    channel_id = get_channel_id(channel)
    
    # Send header message first
    try:
        header_blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🎯 {len(jobs[:max_jobs])} New Job Matches Found!",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{datetime.now().strftime('%B %d, %Y at %I:%M %p')}*\n\nReview each job below and choose:\n• *✅ Auto Apply* - Clawdbot applies automatically\n• *❌ Decline* - Skip this job\n• *👤 Manual Apply* - You'll apply yourself"
                }
            },
            {"type": "divider"}
        ]
        
        client.chat_postMessage(
            channel=channel_id,
            blocks=header_blocks,
            text=f"🎯 {len(jobs[:max_jobs])} New Job Matches Found!"
        )
    except SlackApiError as e:
        print(f"Error sending header: {e}")
    
    # Send each job as a separate message
    results = []
    for i, job in enumerate(jobs[:max_jobs]):
        print(f"\n📤 Sending job {i+1}/{min(len(jobs), max_jobs)}: {job.get('title')}")
        result = send_job_to_slack(job, channel=channel_id, generate_preview=True)
        results.append(result)
        
        # Small delay to avoid rate limiting
        import time
        time.sleep(1)
    
    return results


def handle_job_action(action_id: str, job_data: Dict, user_id: str) -> Dict:
    """
    Handle a Slack button action for a job.
    
    Args:
        action_id: The action ID (auto_apply_job, decline_job, manual_apply_job)
        job_data: The job data from the button value
        user_id: The Slack user who clicked
    
    Returns:
        Result of the action
    """
    from job_approval_workflow import approve_job, deny_job, record_application
    
    title = job_data.get('title', '')
    company = job_data.get('company', '')
    job_url = job_data.get('job_url', '')
    
    if action_id == "auto_apply_job":
        # Approve and trigger auto-application
        print(f"🤖 Auto-applying to: {title} at {company}")
        
        # Approve the job
        approve_result = approve_job(job_url, title, company, job_data)
        
        # TODO: Trigger actual application process
        # This would call apply_job.py to submit the application
        
        return {
            "action": "auto_apply",
            "status": "approved",
            "message": f"✅ Auto-applying to {title} at {company}. Clawdbot will submit your application shortly.",
            "result": approve_result
        }
    
    elif action_id == "decline_job":
        # Decline and add to ignore list
        print(f"❌ Declining: {title} at {company}")
        
        deny_result = deny_job(job_url, title, company, "User declined via Slack")
        
        return {
            "action": "decline",
            "status": "ignored",
            "message": f"❌ Declined {title} at {company}. Added to ignore list.",
            "result": deny_result
        }
    
    elif action_id == "manual_apply_job":
        # Mark for manual application
        print(f"👤 Marked for manual apply: {title} at {company}")
        
        # Record as manual application pending
        record_application(
            job_url=job_url,
            title=title,
            company=company,
            application_method="manual",
            documents_generated={},
            success=False,  # Not yet applied
            error="Pending manual application by user"
        )
        
        return {
            "action": "manual_apply",
            "status": "pending_manual",
            "message": f"👤 Marked {title} at {company} for manual application. Good luck!",
        }
    
    return {"action": "unknown", "status": "error", "message": "Unknown action"}


def update_job_message_after_action(
    client: WebClient,
    channel: str,
    message_ts: str,
    action_taken: str,
    job_data: Dict
) -> bool:
    """
    Update the Slack message after user takes an action.
    """
    title = job_data.get('title', '')
    company = job_data.get('company', '')
    
    status_blocks = {
        "auto_apply": {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"✅ *AUTO-APPLYING* to {title} at {company}\n_Clawdbot is submitting your application..._"
            }
        },
        "decline": {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"❌ *DECLINED* - {title} at {company}\n_Added to ignore list_"
            }
        },
        "manual_apply": {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"👤 *MANUAL APPLY* - {title} at {company}\n_You've marked this for manual application_"
            }
        }
    }
    
    try:
        # Get original message and replace action buttons with status
        result = client.conversations_history(
            channel=channel,
            latest=message_ts,
            inclusive=True,
            limit=1
        )
        
        if result['messages']:
            original_blocks = result['messages'][0].get('blocks', [])
            
            # Remove action buttons and add status
            new_blocks = []
            for block in original_blocks:
                if block.get('type') != 'actions':
                    new_blocks.append(block)
            
            new_blocks.append(status_blocks.get(action_taken, status_blocks['decline']))
            
            client.chat_update(
                channel=channel,
                ts=message_ts,
                blocks=new_blocks
            )
            return True
            
    except SlackApiError as e:
        print(f"Error updating message: {e}")
    
    return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test":
            # Test sending a sample job
            sample_job = {
                "title": "Senior Graphic Designer",
                "company": "Test Company",
                "location": "San Francisco, CA",
                "job_url": "https://example.com/job/123",
                "description": "We're looking for a talented graphic designer with experience in Adobe Creative Suite, Figma, and brand design. The ideal candidate has 3+ years of experience and a strong portfolio."
            }
            
            print("Testing job send to Slack...")
            result = send_job_to_slack(sample_job, generate_preview=True)
            print(json.dumps(result, indent=2, default=str))
        
        elif command == "batch":
            # Test batch send
            sample_jobs = [
                {
                    "title": "Graphic Designer",
                    "company": "ACME Corp",
                    "location": "Oakland, CA",
                    "job_url": "https://example.com/job/1",
                    "description": "Design marketing materials and brand assets."
                },
                {
                    "title": "Visual Designer",
                    "company": "Tech Startup",
                    "location": "Remote",
                    "job_url": "https://example.com/job/2",
                    "description": "Create stunning visuals for web and mobile apps."
                }
            ]
            
            results = send_jobs_batch_to_slack(sample_jobs, max_jobs=2)
            print(f"Sent {len(results)} jobs")
    else:
        print("Slack Job Workflow")
        print("Commands: test, batch")
