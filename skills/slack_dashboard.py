"""
Slack Dashboard Module for Job Application Assistant

Provides:
- Interactive Slack commands for job tracking
- Visual dashboard with application statistics
- Quick actions for reviewing and managing applications
- Configurable job frequency settings

Commands:
- /jobs status - Show application dashboard
- /jobs pending - Show jobs awaiting review
- /jobs stats - Show weekly/monthly statistics
- /jobs settings - View/update job search settings
"""
import os
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def save_config(config: dict):
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def get_slack_client() -> Optional[WebClient]:
    token = os.environ.get('SLACK_BOT_TOKEN')
    if not token:
        return None
    return WebClient(token=token)


def format_status_emoji(status: str) -> str:
    """Get emoji for application status."""
    status_emojis = {
        'pending': '⏳',
        'applied': '📤',
        'screening': '📞',
        'interview': '🎤',
        'offer': '🎉',
        'rejected': '❌',
        'withdrawn': '🚫',
        'accepted': '✅',
    }
    return status_emojis.get(status.lower(), '❓')


def build_dashboard_blocks(stats: Dict, pending_jobs: List, settings: Dict) -> List[Dict]:
    """
    Build Slack Block Kit blocks for the job dashboard.
    """
    blocks = []
    
    # Header
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": "📊 Job Application Dashboard",
            "emoji": True
        }
    })
    
    blocks.append({"type": "divider"})
    
    # Statistics Section
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*📈 This Week's Stats*"
        }
    })
    
    stats_text = f"""
• *Applications Sent:* {stats.get('applied_this_week', 0)}
• *Interviews Scheduled:* {stats.get('interviews_this_week', 0)}
• *Responses Received:* {stats.get('responses_this_week', 0)}
• *Pending Review:* {stats.get('pending_review', 0)}
"""
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": stats_text
        },
        "accessory": {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "View All Stats",
                "emoji": True
            },
            "action_id": "view_all_stats"
        }
    })
    
    blocks.append({"type": "divider"})
    
    # Pipeline Overview
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*🔄 Application Pipeline*"
        }
    })
    
    pipeline_text = f"""
{format_status_emoji('applied')} Applied: {stats.get('total_applied', 0)}
{format_status_emoji('screening')} Screening: {stats.get('in_screening', 0)}
{format_status_emoji('interview')} Interview: {stats.get('in_interview', 0)}
{format_status_emoji('offer')} Offers: {stats.get('offers', 0)}
"""
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": pipeline_text
        }
    })
    
    blocks.append({"type": "divider"})
    
    # Jobs Pending Review
    if pending_jobs:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*⏳ Jobs Pending Review ({len(pending_jobs)})*"
            }
        })
        
        for job in pending_jobs[:5]:  # Show top 5
            job_text = f"*{job.get('title', 'Unknown')}* at {job.get('company', 'Unknown')}\n"
            job_text += f"📍 {job.get('location', 'Unknown')} • Match: {job.get('match_score', 'N/A')}%"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": job_text
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Review",
                        "emoji": True
                    },
                    "style": "primary",
                    "action_id": f"review_job_{job.get('id', 'unknown')}"
                }
            })
        
        if len(pending_jobs) > 5:
            blocks.append({
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": f"_+ {len(pending_jobs) - 5} more jobs pending review_"
                }]
            })
    else:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "✨ *No jobs pending review!* All caught up."
            }
        })
    
    blocks.append({"type": "divider"})
    
    # Current Settings
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*⚙️ Current Settings*"
        }
    })
    
    settings_text = f"""
• *Daily Job Target:* {settings.get('daily_target', 3)} applications
• *Auto-Search:* {'Enabled' if settings.get('auto_search', True) else 'Disabled'}
• *Email Notifications:* {'Enabled' if settings.get('email_notifications', True) else 'Disabled'}
• *Search Locations:* {', '.join(settings.get('locations', ['Not set'])[:3])}
"""
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": settings_text
        },
        "accessory": {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "⚙️ Settings",
                "emoji": True
            },
            "action_id": "open_settings"
        }
    })
    
    # Quick Actions
    blocks.append({"type": "divider"})
    
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🔍 Search Now",
                    "emoji": True
                },
                "style": "primary",
                "action_id": "run_job_search"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📧 Check Emails",
                    "emoji": True
                },
                "action_id": "check_emails"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📊 Full Report",
                    "emoji": True
                },
                "action_id": "full_report"
            }
        ]
    })
    
    # Footer with timestamp
    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        }]
    })
    
    return blocks


def build_settings_modal() -> Dict:
    """
    Build a Slack modal for editing job search settings.
    """
    config = load_config()
    
    return {
        "type": "modal",
        "callback_id": "settings_modal",
        "title": {
            "type": "plain_text",
            "text": "Job Search Settings"
        },
        "submit": {
            "type": "plain_text",
            "text": "Save"
        },
        "blocks": [
            {
                "type": "input",
                "block_id": "daily_target",
                "element": {
                    "type": "static_select",
                    "action_id": "daily_target_select",
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "3 jobs/day (Recommended)"},
                        "value": "3"
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "1-2 jobs/day (Quality focus)"}, "value": "2"},
                        {"text": {"type": "plain_text", "text": "3 jobs/day (Recommended)"}, "value": "3"},
                        {"text": {"type": "plain_text", "text": "4-5 jobs/day (Active search)"}, "value": "5"},
                        {"text": {"type": "plain_text", "text": "6-10 jobs/day (Intensive)"}, "value": "10"},
                    ]
                },
                "label": {
                    "type": "plain_text",
                    "text": "Daily Application Target"
                },
                "hint": {
                    "type": "plain_text",
                    "text": "Research shows 2-5 tailored applications per day is optimal"
                }
            },
            {
                "type": "input",
                "block_id": "min_salary",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "min_salary_input",
                    "placeholder": {"type": "plain_text", "text": "e.g., 70000"}
                },
                "label": {"type": "plain_text", "text": "Minimum Salary ($)"},
                "optional": True
            },
            {
                "type": "input",
                "block_id": "locations",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "locations_input",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Oakland, CA\nSan Francisco, CA\nRemote"}
                },
                "label": {"type": "plain_text", "text": "Preferred Locations (one per line)"}
            },
            {
                "type": "input",
                "block_id": "deal_breakers",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "deal_breakers_input",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Commission only\nUnpaid internship\nNo remote option"}
                },
                "label": {"type": "plain_text", "text": "Deal Breakers (one per line)"},
                "optional": True
            },
            {
                "type": "input",
                "block_id": "auto_search",
                "element": {
                    "type": "checkboxes",
                    "action_id": "auto_search_check",
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "Enable daily automatic job search"},
                            "value": "enabled"
                        }
                    ]
                },
                "label": {"type": "plain_text", "text": "Automation"},
                "optional": True
            }
        ]
    }


def send_dashboard(channel: str, user_id: str = None) -> bool:
    """
    Send the job dashboard to a Slack channel or DM.
    """
    client = get_slack_client()
    if not client:
        return False
    
    # Load stats from tracking module
    try:
        from track_status import get_stats
        stats = get_stats()
    except:
        stats = {
            'applied_this_week': 0,
            'interviews_this_week': 0,
            'responses_this_week': 0,
            'pending_review': 0,
            'total_applied': 0,
            'in_screening': 0,
            'in_interview': 0,
            'offers': 0,
        }
    
    # Get pending jobs (placeholder - would come from actual data)
    pending_jobs = []
    
    # Get current settings
    config = load_config()
    settings = {
        'daily_target': config.get('automation', {}).get('daily_target', 3),
        'auto_search': config.get('automation', {}).get('auto_search', True),
        'email_notifications': config.get('automation', {}).get('email_notifications', True),
        'locations': config.get('search', {}).get('locations', []),
    }
    
    blocks = build_dashboard_blocks(stats, pending_jobs, settings)
    
    try:
        if user_id:
            # Send as DM
            result = client.conversations_open(users=[user_id])
            channel = result['channel']['id']
        
        client.chat_postMessage(
            channel=channel,
            blocks=blocks,
            text="Job Application Dashboard"
        )
        return True
        
    except SlackApiError as e:
        print(f"Error sending dashboard: {e}")
        return False


def update_job_frequency(daily_target: int) -> bool:
    """
    Update the daily job application target.
    """
    config = load_config()
    
    if 'automation' not in config:
        config['automation'] = {}
    
    config['automation']['daily_target'] = daily_target
    save_config(config)
    
    return True


def get_quick_stats() -> str:
    """
    Get a quick text summary of job stats for simple messages.
    """
    try:
        from track_status import get_stats
        stats = get_stats()
    except:
        return "No tracking data available yet."
    
    return f"""📊 *Quick Stats*
• Applied: {stats.get('total_applied', 0)}
• Interviews: {stats.get('in_interview', 0)}
• Pending: {stats.get('pending_review', 0)}
• This week: {stats.get('applied_this_week', 0)} applications"""


if __name__ == "__main__":
    print("Slack Dashboard Module")
    print("="*50)
    print("\nQuick Stats:")
    print(get_quick_stats())
