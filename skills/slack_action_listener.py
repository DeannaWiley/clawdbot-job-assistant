"""
Slack Action Listener - Handles button clicks for job approval workflow
Uses Socket Mode to receive interactive events from Slack
"""
import os
import sys
import json
import subprocess
from datetime import datetime
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler


def _load_env_from_user_scope(var_name: str) -> str:
    """Load environment variable from Windows User scope."""
    value = os.environ.get(var_name)
    if value and len(value) > 10:
        return value
    
    if sys.platform == 'win32':
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', f'[Environment]::GetEnvironmentVariable("{var_name}", "User")'],
                capture_output=True, text=True
            )
            value = result.stdout.strip()
            if value and len(value) > 10:
                os.environ[var_name] = value
                return value
        except:
            pass
    return None


# Load tokens
BOT_TOKEN = _load_env_from_user_scope('SLACK_BOT_TOKEN')
APP_TOKEN = _load_env_from_user_scope('SLACK_APP_TOKEN')

# Load CAPTCHA keys (support both naming conventions)
_load_env_from_user_scope('CaptchaKey')
_load_env_from_user_scope('CaptchaBudget')
_load_env_from_user_scope('CAPTCHA_2CAPTCHA_KEY')
_load_env_from_user_scope('CAPTCHA_DAILY_BUDGET')
_load_env_from_user_scope('OPENROUTER_API_KEY')

if not BOT_TOKEN or not APP_TOKEN:
    print("ERROR: SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set")
    sys.exit(1)

# Initialize the Bolt app
app = App(token=BOT_TOKEN)


@app.action("auto_apply_job")
def handle_auto_apply(ack, body, client, logger):
    """Handle Auto Apply button click - Clawdbot applies automatically."""
    ack()
    
    try:
        action = body['actions'][0]
        job_data = json.loads(action['value'])
        user_id = body['user']['id']
        channel_id = body['channel']['id']
        message_ts = body['message']['ts']
        
        title = job_data.get('title', 'Unknown')
        company = job_data.get('company', 'Unknown')
        job_url = job_data.get('job_url', '')
        
        print(f"🤖 AUTO APPLY: {title} at {company}")
        
        # Update the message to show processing
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=f"🤖 Auto-applying to {title} at {company}...",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *AUTO-APPLYING*\n*{title}* at *{company}*\n\n_Clawdbot is generating documents and submitting application..._"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"Approved by <@{user_id}> at {datetime.now().strftime('%I:%M %p')}"}
                    ]
                }
            ]
        )
        
        # Trigger the application process with elite document generator
        from job_approval_workflow import approve_job, record_application
        from document_generator import generate_application_documents
        
        # Try to use elite generator for better ATS optimization
        try:
            from elite_document_generator import generate_elite_application
            elite_result = generate_elite_application(title, company, job_data.get('description', ''))
            docs = {
                "tailored_summary": elite_result.get("tailored_summary", ""),
                "cover_letter": elite_result.get("cover_letter", ""),
                "match_score": elite_result.get("final_match", {}).get("overall_match_rate", 0),
                "files": {}
            }
            # Generate PDF files
            docs.update(generate_application_documents(title, company, job_data.get('description', '')))
        except Exception as elite_err:
            print(f"Elite generator failed, using standard: {elite_err}")
            docs = generate_application_documents(title, company, job_data.get('description', ''))
        
        # Record the approval
        approve_job(job_url, title, company, job_data)
        
        # Get match score for display
        match_score = docs.get('match_score', 0)
        match_emoji = "🟢" if match_score >= 75 else "🟡" if match_score >= 50 else "🔴"
        
        # Update message with success and match score
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=f"✅ Applied to {title} at {company}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *APPLICATION SUBMITTED*\n*{title}* at *{company}*\n\n📄 Documents generated and application submitted!\n{match_emoji} ATS Match Score: *{match_score}%*"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"Applied by Clawdbot • Approved by <@{user_id}>"}
                    ]
                }
            ]
        )
        
    except Exception as e:
        logger.error(f"Error handling auto_apply: {e}")
        print(f"❌ Error: {e}")
        
        # Notify user of failure with actionable info
        try:
            client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=f"❌ Auto-apply failed for {title} at {company}",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"❌ *AUTO-APPLY FAILED*\n*{title}* at *{company}*\n\nError: {str(e)[:200]}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"🔗 <{job_url}|Apply Manually Here>"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {"type": "mrkdwn", "text": f"Failed at {datetime.now().strftime('%I:%M %p')} • Please apply manually"}
                        ]
                    }
                ]
            )
        except:
            pass


@app.action("decline_job")
def handle_decline(ack, body, client, logger):
    """Handle Decline button click - Skip job and add to ignore list."""
    ack()
    
    try:
        action = body['actions'][0]
        job_data = json.loads(action['value'])
        user_id = body['user']['id']
        channel_id = body['channel']['id']
        message_ts = body['message']['ts']
        
        title = job_data.get('title', 'Unknown')
        company = job_data.get('company', 'Unknown')
        job_url = job_data.get('job_url', '')
        
        print(f"❌ DECLINED: {title} at {company}")
        
        # Add to ignore list
        from job_approval_workflow import deny_job
        deny_job(job_url, title, company, "Declined via Slack")
        
        # Update the message
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=f"❌ Declined {title} at {company}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ *DECLINED*\n~{title}~ at ~{company}~\n\n_Added to ignore list_"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"Declined by <@{user_id}> at {datetime.now().strftime('%I:%M %p')}"}
                    ]
                }
            ]
        )
        
    except Exception as e:
        logger.error(f"Error handling decline: {e}")
        print(f"❌ Error: {e}")


@app.action("manual_apply_job")
def handle_manual_apply(ack, body, client, logger):
    """Handle Manual Apply button click - User will apply themselves."""
    ack()
    
    try:
        action = body['actions'][0]
        job_data = json.loads(action['value'])
        user_id = body['user']['id']
        channel_id = body['channel']['id']
        message_ts = body['message']['ts']
        
        title = job_data.get('title', 'Unknown')
        company = job_data.get('company', 'Unknown')
        job_url = job_data.get('job_url', '')
        
        print(f"👤 MANUAL APPLY: {title} at {company}")
        
        # Record as pending manual
        from job_approval_workflow import record_application
        record_application(
            job_url=job_url,
            title=title,
            company=company,
            application_method="manual",
            documents_generated={},
            success=False,
            error="Pending manual application"
        )
        
        # Update the message
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=f"👤 Manual apply marked for {title} at {company}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"👤 *MANUAL APPLY*\n*{title}* at *{company}*\n\n_You've marked this for manual application_"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🔗 <{job_url}|Apply Here>"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"Marked by <@{user_id}> at {datetime.now().strftime('%I:%M %p')} • Good luck! 🍀"}
                    ]
                }
            ]
        )
        
    except Exception as e:
        logger.error(f"Error handling manual_apply: {e}")
        print(f"❌ Error: {e}")


@app.action("status_indicator")
def handle_status_indicator(ack, body, client, logger):
    """Handle click on status indicator button (no-op, just acknowledges)."""
    ack()
    # This is just a visual indicator, no action needed


@app.action("captcha_solved")
def handle_captcha_solved(ack, body, client, logger):
    """Handle CAPTCHA solved button - user confirms they solved the CAPTCHA."""
    ack()
    
    try:
        action = body['actions'][0]
        challenge_id = action.get('value', 'unknown')
        user_id = body['user']['id']
        channel_id = body['channel']['id']
        message_ts = body['message']['ts']
        
        print(f"✅ CAPTCHA SOLVED: Challenge {challenge_id} by <@{user_id}>")
        
        # Update the message to show solved status
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text="✅ CAPTCHA Solved!",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *CAPTCHA Solved!*\n\n_Solved by <@{user_id}> at {datetime.now().strftime('%I:%M %p')}_\n\nClawdBot will continue with the application."
                    }
                }
            ]
        )
        
    except Exception as e:
        logger.error(f"Error handling captcha_solved: {e}")
        print(f"❌ Error: {e}")


@app.action("captcha_skip")
def handle_captcha_skip(ack, body, client, logger):
    """Handle CAPTCHA skip button - user wants to skip this job."""
    ack()
    
    try:
        action = body['actions'][0]
        challenge_id = action.get('value', 'unknown')
        user_id = body['user']['id']
        channel_id = body['channel']['id']
        message_ts = body['message']['ts']
        
        print(f"⏭️ CAPTCHA SKIPPED: Challenge {challenge_id} by <@{user_id}>")
        
        # Update the message to show skipped status
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text="⏭️ Job Skipped",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"⏭️ *Job Skipped*\n\n_Skipped by <@{user_id}> at {datetime.now().strftime('%I:%M %p')}_\n\nClawdBot will move on to the next job."
                    }
                }
            ]
        )
        
    except Exception as e:
        logger.error(f"Error handling captcha_skip: {e}")
        print(f"❌ Error: {e}")


@app.action("preview_docs")
def handle_preview_docs(ack, body, client, logger):
    """Handle Preview Docs button click - Generate and show document preview."""
    ack()
    
    try:
        action = body['actions'][0]
        job_data = json.loads(action['value'])
        user_id = body['user']['id']
        channel_id = body['channel']['id']
        
        title = job_data.get('title', 'Unknown')
        company = job_data.get('company', 'Unknown')
        description = job_data.get('description', '')
        
        print(f"📄 PREVIEW DOCS: {title} at {company}")
        
        # Generate preview documents
        from document_generator import generate_application_documents
        docs = generate_application_documents(title, company, description)
        
        # Send document preview as a new message
        preview_blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"📄 Document Preview: {title}", "emoji": True}
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Company:* {company}\n*Match Score:* {docs.get('match_score', 'N/A')}%"
                }
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📝 Tailored Summary:*\n_{docs.get('tailored_summary', 'N/A')[:500]}..._"
                }
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*✉️ Cover Letter Preview:*\n_{docs.get('cover_letter', 'N/A')[:800]}..._"
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Generated for <@{user_id}> • Full documents saved to applications folder"}
                ]
            }
        ]
        
        # Add file links if available
        files = docs.get('files', {})
        if files:
            file_links = []
            for file_type, path in files.items():
                if path:
                    file_links.append(f"• {file_type}: `{os.path.basename(path)}`")
            if file_links:
                preview_blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*📁 Generated Files:*\n" + "\n".join(file_links)
                    }
                })
        
        client.chat_postMessage(
            channel=channel_id,
            text=f"Document preview for {title} at {company}",
            blocks=preview_blocks
        )
        
    except Exception as e:
        logger.error(f"Error handling preview_docs: {e}")
        print(f"❌ Error: {e}")
        
        # Notify user of failure
        try:
            client.chat_postMessage(
                channel=channel_id,
                text=f"❌ Failed to generate document preview: {str(e)[:100]}"
            )
        except:
            pass


def start_listener():
    """Start the Slack Socket Mode listener."""
    print("🚀 Starting Slack Action Listener...")
    print("   Listening for: auto_apply_job, decline_job, manual_apply_job, preview_docs, captcha_solved, captcha_skip")
    print("   Press Ctrl+C to stop")
    
    handler = SocketModeHandler(app, APP_TOKEN)
    handler.start()


if __name__ == "__main__":
    start_listener()
