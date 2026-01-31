#!/usr/bin/env python3
"""
Full End-to-End Auto-Apply Test
Applies to a real job without user input.
"""
import asyncio
import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(__file__))

def load_env(var_name):
    value = os.environ.get(var_name)
    if value and len(value) > 10:
        return value
    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command', 
             f'[Environment]::GetEnvironmentVariable("{var_name}", "User")'],
            capture_output=True, text=True
        )
        value = result.stdout.strip()
        if value and len(value) > 10:
            os.environ[var_name] = value
            return value
    except:
        pass
    return None

# Load all required env vars
for var in ['OPENROUTER_API_KEY', 'GROQ_API_KEY', 'GEMINI_API_KEY', 'CaptchaKey', 'CAPTCHA_2CAPTCHA_KEY']:
    load_env(var)

# Also set CaptchaKey as CAPTCHA_2CAPTCHA_KEY if needed
if os.environ.get('CaptchaKey') and not os.environ.get('CAPTCHA_2CAPTCHA_KEY'):
    os.environ['CAPTCHA_2CAPTCHA_KEY'] = os.environ['CaptchaKey']

from real_auto_apply import auto_apply_to_job

# List of jobs to try - test with GoFasti first to verify form filling fixes
JOBS_TO_TRY = [
    {
        'url': 'https://boards.greenhouse.io/gofasti/jobs/5709006004',
        'title': 'Graphic Designer (Remote)',
        'company': 'GoFasti',
        'description': 'English-fluent Graphic Designer for remote work. Test for dropdown and radio button fixes.'
    },
]

async def run_auto_apply_test():
    print("=" * 70)
    print("🚀 FULL END-TO-END AUTO-APPLY TEST")
    print("=" * 70)
    print(f"Testing {len(JOBS_TO_TRY)} jobs until one succeeds...")
    print("=" * 70)
    
    for i, job in enumerate(JOBS_TO_TRY, 1):
        print(f"\n{'='*70}")
        print(f"ATTEMPT {i}/{len(JOBS_TO_TRY)}: {job['title']} at {job['company']}")
        print(f"URL: {job['url']}")
        print("=" * 70)
        
        try:
            result = await auto_apply_to_job(
                job_url=job['url'],
                job_title=job['title'],
                company=job['company'],
                job_description=job['description']
            )
            
            print(f"\n{'='*70}")
            print(f"📊 RESULT FOR {job['company']}")
            print("=" * 70)
            print(f"Success: {result.get('success')}")
            print(f"Error: {result.get('error', 'None')}")
            print(f"Screenshot: {result.get('screenshot', 'N/A')}")
            print(f"Email Verified: {result.get('email_verified', 'N/A')}")
            
            if result.get('success'):
                print("\n🎉 APPLICATION SUBMITTED SUCCESSFULLY!")
                print("=" * 70)
                return result
            else:
                print(f"\n❌ Failed: {result.get('error', 'Unknown error')}")
                print("Trying next job...")
                
        except Exception as e:
            print(f"\n❌ Exception: {e}")
            print("Trying next job...")
            continue
    
    print("\n" + "=" * 70)
    print("❌ ALL JOBS FAILED")
    print("=" * 70)
    return {"success": False, "error": "All jobs failed"}

if __name__ == "__main__":
    result = asyncio.run(run_auto_apply_test())
    
    # Final summary
    print("\n" + "=" * 70)
    print("📋 FINAL SUMMARY")
    print("=" * 70)
    if result.get('success'):
        print("✅ Successfully auto-applied to a job!")
        print(f"   Screenshot: {result.get('screenshot', 'N/A')}")
    else:
        print(f"❌ Failed to auto-apply: {result.get('error', 'Unknown')}")
