"""
Slack Commands for Job Assistant

Handles direct Slack requests like:
- "Generate resume for [job URL]"
- "Preview resume for [job URL]"
- "Apply to [job URL]"
- "Scrape [job URL]"

This module processes natural language requests from Slack and returns results.
"""
import os
import sys
import re
import json
import asyncio
from datetime import datetime
from typing import Dict, Optional, Tuple

sys.path.insert(0, os.path.dirname(__file__))

from tailor_resume import tailor_resume
from write_cover_letter import write_cover_letter
from smart_scraper import scrape_job_details, SmartScraper
from slack_notify import get_slack_client, load_config
from review_content import review_generated_content


def extract_url(text: str) -> Optional[str]:
    """Extract URL from text."""
    # Match URLs in Slack format <url|text> or plain URLs
    slack_url = re.search(r'<(https?://[^|>]+)', text)
    if slack_url:
        return slack_url.group(1)
    
    plain_url = re.search(r'https?://[^\s<>"]+', text)
    if plain_url:
        return plain_url.group(0)
    
    return None


async def generate_resume_preview(job_url: str) -> Dict:
    """
    Generate a tailored resume for a job URL and return preview.
    """
    result = {
        "job_url": job_url,
        "status": "started",
        "job_details": None,
        "tailored_resume": None,
        "cover_letter": None,
        "match_score": None,
        "errors": [],
    }
    
    try:
        # Step 1: Scrape job details
        print(f"[RESUME PREVIEW] Scraping job: {job_url}")
        job_data = await scrape_job_details(job_url)
        result["job_details"] = {
            "title": job_data.get("job_title", job_data.get("title", "Unknown")),
            "company": job_data.get("company", "Unknown"),
            "location": job_data.get("location", "Unknown"),
        }
        
        # Get job description
        description = job_data.get("description", "")
        if not description:
            description = job_data.get("title", "") + " position"
        
        job_title = result["job_details"]["title"]
        
        # Step 2: Tailor resume
        print(f"[RESUME PREVIEW] Tailoring resume for: {job_title}")
        resume_result = tailor_resume(description, job_title)
        
        result["tailored_resume"] = resume_result.get("tailored_summary", "")
        result["match_score"] = resume_result.get("match_score", {})
        result["keywords"] = resume_result.get("keywords", [])
        result["suggestions"] = resume_result.get("bullet_suggestions", [])
        
        # Step 3: Generate cover letter
        print(f"[RESUME PREVIEW] Generating cover letter")
        cover_result = write_cover_letter(description, job_title)
        result["cover_letter"] = cover_result.get("cover_letter", "")
        
        # Step 4: Review content (optional validation)
        try:
            review = review_generated_content(
                result["tailored_resume"],
                description,
                "resume"
            )
            result["review_score"] = review.get("overall_score", 0)
        except:
            pass
        
        result["status"] = "success"
        
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(str(e))
    
    return result


def format_resume_preview_slack(result: Dict) -> list:
    """Format resume preview result as Slack blocks."""
    blocks = []
    
    # Header
    job_title = result.get("job_details", {}).get("title", "Unknown Position")
    company = result.get("job_details", {}).get("company", "Unknown Company")
    
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"Resume Preview: {job_title}",
            "emoji": True
        }
    })
    
    blocks.append({
        "type": "section",
        "fields": [
            {"type": "mrkdwn", "text": f"*Company:*\n{company}"},
            {"type": "mrkdwn", "text": f"*Match Score:*\n{result.get('match_score', {}).get('overall_score', 'N/A')}%"},
        ]
    })
    
    blocks.append({"type": "divider"})
    
    # Tailored Summary
    if result.get("tailored_resume"):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Tailored Resume Summary:*\n```{result['tailored_resume'][:1500]}```"
            }
        })
    
    # Keywords matched
    if result.get("keywords"):
        keywords_text = ", ".join(result["keywords"][:15])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Keywords Matched:*\n{keywords_text}"
            }
        })
    
    # Bullet suggestions
    if result.get("suggestions"):
        suggestions_text = "\n".join([f"- {s}" for s in result["suggestions"][:5]])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Suggested Bullets:*\n{suggestions_text}"
            }
        })
    
    blocks.append({"type": "divider"})
    
    # Cover Letter Preview (first 500 chars)
    if result.get("cover_letter"):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Cover Letter Preview:*\n```{result['cover_letter'][:800]}...```"
            }
        })
    
    # Action buttons
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Approve & Apply"},
                "style": "primary",
                "value": result.get("job_url", ""),
                "action_id": "approve_resume"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Regenerate"},
                "value": result.get("job_url", ""),
                "action_id": "regenerate_resume"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "View Full"},
                "value": result.get("job_url", ""),
                "action_id": "view_full_resume"
            }
        ]
    })
    
    # Errors
    if result.get("errors"):
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"*Errors:* {', '.join(result['errors'])}"}
            ]
        })
    
    return blocks


def send_resume_preview(job_url: str, channel: str = None) -> Dict:
    """
    Generate and send resume preview to Slack.
    """
    try:
        # Generate preview
        result = asyncio.run(generate_resume_preview(job_url))
        
        # Format as Slack blocks
        blocks = format_resume_preview_slack(result)
        
        # Send to Slack
        client = get_slack_client()
        config = load_config()
        
        if not channel:
            channel = config.get('slack', {}).get('channel')
        
        response = client.chat_postMessage(
            channel=channel,
            blocks=blocks,
            text=f"Resume preview for {result.get('job_details', {}).get('title', 'job')}"
        )
        
        print(f"[SLACK] Resume preview sent to {channel}")
        return {"success": True, "result": result, "ts": response.get("ts")}
        
    except Exception as e:
        print(f"[SLACK ERROR] {e}")
        return {"success": False, "error": str(e)}


def process_slack_command(text: str, channel: str = None, user_id: str = None) -> Dict:
    """
    Process a natural language command from Slack.
    
    Supported commands:
    - "generate resume for [URL]"
    - "preview resume for [URL]"
    - "tailor resume for [URL]"
    - "scrape [URL]"
    - "apply to [URL]"
    """
    text_lower = text.lower()
    url = extract_url(text)
    
    if not url:
        return {
            "success": False,
            "error": "No URL found in message. Please include a job URL."
        }
    
    # Determine action
    if any(word in text_lower for word in ['resume', 'preview', 'tailor', 'generate']):
        return send_resume_preview(url, channel)
    
    elif 'scrape' in text_lower:
        job_data = asyncio.run(scrape_job_details(url))
        return {"success": True, "job_data": job_data}
    
    elif 'apply' in text_lower:
        from smart_scraper import apply_to_job_full
        result = asyncio.run(apply_to_job_full(url))
        return {"success": True, "application": result}
    
    else:
        # Default to resume preview
        return send_resume_preview(url, channel)


# CLI for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Slack Commands for Job Assistant')
    parser.add_argument('command', choices=['preview', 'scrape', 'apply'])
    parser.add_argument('--url', '-u', required=True, help='Job URL')
    parser.add_argument('--channel', '-c', help='Slack channel')
    
    args = parser.parse_args()
    
    if args.command == 'preview':
        result = send_resume_preview(args.url, args.channel)
        print(json.dumps(result, indent=2, default=str))
    
    elif args.command == 'scrape':
        result = asyncio.run(scrape_job_details(args.url))
        print(json.dumps(result, indent=2))
    
    elif args.command == 'apply':
        from smart_scraper import apply_to_job_full
        result = asyncio.run(apply_to_job_full(args.url))
        print(json.dumps(result, indent=2))
