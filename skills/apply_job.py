"""
Job Application Module - Handles automated application submission
"""
import os
import yaml
import json
import time
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse


def load_config() -> dict:
    """Load configuration from config.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def detect_application_platform(job_url: str) -> Tuple[str, bool]:
    """
    Detect which platform/ATS the job is on and if auto-apply is supported.
    
    Returns:
        Tuple of (platform_name, is_auto_apply_supported)
    """
    url_lower = job_url.lower()
    parsed = urlparse(job_url)
    domain = parsed.netloc.lower()
    
    # LinkedIn Easy Apply
    if 'linkedin.com' in domain:
        return ('linkedin', True)
    
    # Greenhouse ATS
    if 'greenhouse.io' in domain or 'boards.greenhouse.io' in url_lower:
        return ('greenhouse', True)
    
    # Lever ATS
    if 'lever.co' in domain or 'jobs.lever.co' in url_lower:
        return ('lever', True)
    
    # Indeed
    if 'indeed.com' in domain:
        return ('indeed', True)
    
    # Glassdoor
    if 'glassdoor.com' in domain:
        return ('glassdoor', False)  # Usually redirects
    
    # Workday (complex, often not automatable)
    if 'workday.com' in domain or 'myworkdayjobs.com' in domain:
        return ('workday', False)
    
    # Unknown
    return ('unknown', False)


async def apply_linkedin_easy_apply(
    job_url: str,
    resume_path: str,
    cover_letter_text: str,
    user_info: Dict
) -> Dict:
    """
    Apply to a LinkedIn Easy Apply job using Playwright.
    
    NOTE: This requires LinkedIn credentials and is for demonstration.
    In production, you'd need proper authentication handling.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {
            "success": False,
            "error": "Playwright not installed. Run: pip install playwright && playwright install"
        }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to job
            await page.goto(job_url, wait_until='networkidle')
            
            # Check if Easy Apply is available
            easy_apply_btn = await page.query_selector('button[data-control-name="jobdetails_topcard_inapply"]')
            
            if not easy_apply_btn:
                await browser.close()
                return {
                    "success": False,
                    "error": "Easy Apply not available for this job",
                    "manual_url": job_url
                }
            
            # NOTE: Full implementation would:
            # 1. Click Easy Apply
            # 2. Fill in required fields
            # 3. Upload resume
            # 4. Add cover letter
            # 5. Submit
            
            # For safety, we return a "requires manual action" response
            await browser.close()
            return {
                "success": False,
                "error": "LinkedIn Easy Apply automation disabled for safety",
                "manual_url": job_url,
                "message": "Please apply manually - your documents are ready!"
            }
            
        except Exception as e:
            await browser.close()
            return {"success": False, "error": str(e)}


async def apply_greenhouse(
    job_url: str,
    resume_path: str,
    cover_letter_text: str,
    user_info: Dict
) -> Dict:
    """
    Apply to a Greenhouse job posting.
    
    Greenhouse forms are relatively consistent and can be automated.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {
            "success": False,
            "error": "Playwright not installed"
        }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(job_url, wait_until='networkidle')
            
            # Find the application form
            form = await page.query_selector('form#application-form, form[data-provides="application"]')
            
            if not form:
                await browser.close()
                return {
                    "success": False,
                    "error": "Application form not found",
                    "manual_url": job_url
                }
            
            # NOTE: Full implementation would fill:
            # - First name, Last name
            # - Email, Phone
            # - Resume upload
            # - Cover letter
            # - Any custom questions
            
            await browser.close()
            return {
                "success": False,
                "error": "Greenhouse automation in demo mode",
                "manual_url": job_url,
                "message": "Please apply manually - your documents are ready!"
            }
            
        except Exception as e:
            await browser.close()
            return {"success": False, "error": str(e)}


def prepare_application_package(
    job: Dict,
    tailored_resume: Dict,
    cover_letter: Dict
) -> Dict:
    """
    Prepare all materials needed for an application.
    """
    config = load_config()
    user_info = config['user']
    
    return {
        "job": {
            "title": job.get('title'),
            "company": job.get('company'),
            "location": job.get('location'),
            "url": job.get('job_url'),
        },
        "user": {
            "name": user_info['name'],
            "email": user_info.get('email', ''),
            "phone": user_info.get('phone', ''),
            "linkedin": user_info.get('linkedin_url', ''),
        },
        "documents": {
            "resume_summary": tailored_resume.get('tailored_summary', ''),
            "resume_suggestions": tailored_resume.get('bullet_suggestions', ''),
            "cover_letter": cover_letter.get('cover_letter', ''),
            "email_body": cover_letter.get('email_body', ''),
        },
        "match_score": tailored_resume.get('match_score', {}).get('overall_score', 0),
    }


async def apply_to_job(
    job: Dict,
    tailored_resume: Dict,
    cover_letter: Dict,
    resume_path: Optional[str] = None
) -> Dict:
    """
    Main function to apply to a job.
    
    Args:
        job: Job dictionary with URL and details
        tailored_resume: Output from tailor_resume()
        cover_letter: Output from write_cover_letter()
        resume_path: Path to PDF resume file
    
    Returns:
        Application result dictionary
    """
    config = load_config()
    
    # Check if auto-apply is enabled
    if not config['application'].get('auto_apply_enabled', False):
        return {
            "success": False,
            "error": "Auto-apply is disabled in config",
            "manual_url": job.get('job_url'),
            "message": "Auto-apply disabled for safety. Please apply manually with the prepared documents."
        }
    
    job_url = job.get('job_url', '')
    platform, is_supported = detect_application_platform(job_url)
    
    print(f"Applying to: {job.get('title')} at {job.get('company')}")
    print(f"  Platform: {platform}, Auto-apply supported: {is_supported}")
    
    if not is_supported:
        return {
            "success": False,
            "error": f"Auto-apply not supported for {platform}",
            "manual_url": job_url,
            "platform": platform,
            "message": f"Please apply manually at {platform}. Your documents are ready!"
        }
    
    # Prepare application package
    package = prepare_application_package(job, tailored_resume, cover_letter)
    user_info = package['user']
    cover_letter_text = package['documents']['cover_letter']
    
    # Route to appropriate handler
    if platform == 'linkedin':
        result = await apply_linkedin_easy_apply(
            job_url, resume_path, cover_letter_text, user_info
        )
    elif platform == 'greenhouse':
        result = await apply_greenhouse(
            job_url, resume_path, cover_letter_text, user_info
        )
    elif platform == 'lever':
        # Similar to Greenhouse
        result = {
            "success": False,
            "error": "Lever automation in demo mode",
            "manual_url": job_url
        }
    else:
        result = {
            "success": False,
            "error": f"No handler for platform: {platform}",
            "manual_url": job_url
        }
    
    result['platform'] = platform
    result['job_title'] = job.get('title')
    result['company'] = job.get('company')
    
    return result


def generate_manual_application_guide(
    job: Dict,
    cover_letter: Dict,
    tailored_resume: Dict
) -> str:
    """
    Generate a guide for manual application when auto-apply isn't available.
    """
    guide = f"""
# Manual Application Guide

## Job Details
- **Position**: {job.get('title')}
- **Company**: {job.get('company')}
- **Location**: {job.get('location')}
- **URL**: {job.get('job_url')}

## Your Match Score: {tailored_resume.get('match_score', {}).get('overall_score', 'N/A')}%

## Steps to Apply:
1. Open the job URL above
2. Click "Apply" or "Apply Now"
3. Fill in your contact information
4. Upload your resume (use the tailored version below)
5. Paste the cover letter in the appropriate field
6. Review and submit

## Tailored Summary for This Role:
{tailored_resume.get('tailored_summary', 'N/A')}

## Cover Letter:
{cover_letter.get('cover_letter', 'N/A')}

## Email Body (if sending via email):
{cover_letter.get('email_body', 'N/A')}
"""
    return guide


if __name__ == "__main__":
    # Test platform detection
    test_urls = [
        "https://www.linkedin.com/jobs/view/123456",
        "https://boards.greenhouse.io/company/jobs/789",
        "https://jobs.lever.co/company/abc123",
        "https://company.myworkdayjobs.com/careers/job/123",
        "https://www.indeed.com/viewjob?jk=abc123",
    ]
    
    for url in test_urls:
        platform, supported = detect_application_platform(url)
        print(f"{url[:50]}... -> {platform} (auto: {supported})")
