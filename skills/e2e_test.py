#!/usr/bin/env python3
"""
End-to-End Test Suite for ClawdBot
Tests all major flows: Job Search -> Slack -> Actions -> Email
"""
import sys
import os
import subprocess
import time
import json

sys.path.insert(0, os.path.dirname(__file__))

def load_env(var_name):
    """Load env var from Windows User scope"""
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

# Pre-load all required env vars
for var in ['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN', 'OPENROUTER_API_KEY', 'GROQ_API_KEY', 'GEMINI_API_KEY']:
    load_env(var)

print("=" * 70)
print("🦞 CLAWDBOT END-TO-END TEST SUITE")
print("=" * 70)

results = {}

# =============================================================================
# TEST 1: Slack Connection
# =============================================================================
print("\n" + "=" * 70)
print("TEST 1: Slack Connection")
print("=" * 70)

try:
    from slack_sdk import WebClient
    token = os.environ.get('SLACK_BOT_TOKEN')
    client = WebClient(token=token)
    
    # Test auth
    auth = client.auth_test()
    print(f"  ✅ Connected as: {auth['user']}")
    print(f"  ✅ Team: {auth['team']}")
    
    # Test channel access
    channel_id = 'C0ABG9NGNTZ'
    info = client.conversations_info(channel=channel_id)
    print(f"  ✅ Channel access: #{info['channel']['name']}")
    
    results['slack_connection'] = True
except Exception as e:
    print(f"  ❌ Slack Connection: {e}")
    results['slack_connection'] = False

# =============================================================================
# TEST 2: Job Search Module
# =============================================================================
print("\n" + "=" * 70)
print("TEST 2: Job Search Module")
print("=" * 70)

try:
    from job_search import search_jobs_for_category, load_config
    
    config = load_config()
    job_config = config.get('job_search', {})
    print(f"  Config loaded: {len(job_config.get('keywords', []))} keywords")
    
    # Quick search test - use the actual function
    print("  Running quick search (this may take a moment)...")
    test_df = search_jobs_for_category(
        category_name='test',
        keywords=['product designer'],
        locations=['Remote'],
        sources=['linkedin'],
        hours_old=72,
        results_wanted=3
    )
    print(f"  ✅ Found {len(test_df)} jobs in quick search")
    
    if len(test_df) > 0:
        job = test_df.iloc[0]
        print(f"     Sample: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
    
    results['job_search'] = True
except Exception as e:
    print(f"  ❌ Job Search: {e}")
    results['job_search'] = False

# =============================================================================
# TEST 3: Slack Notification (Send Job Summary)
# =============================================================================
print("\n" + "=" * 70)
print("TEST 3: Slack Notification - Job Summary")
print("=" * 70)

try:
    from slack_notify import send_job_summary
    
    # Create test jobs (function expects a list)
    test_jobs = [{
        'title': 'E2E Test - Senior Designer',
        'company': 'TestCorp',
        'location': 'Remote',
        'job_url': 'https://example.com/job/test',
        'description': 'This is an automated end-to-end test job posting.',
        'match_score': {'overall_score': 85},
        'source': 'e2e_test',
        'category': 'test'
    }]
    
    result = send_job_summary(
        jobs=test_jobs,
        channel='C0ABG9NGNTZ'
    )
    
    if result and (result.get('ok') or result.get('success')):
        print(f"  ✅ Job summary sent to Slack")
        print(f"     Message ts: {result.get('ts')}")
        results['slack_notify'] = True
    else:
        print(f"  ⚠️ Slack notify returned: {result}")
        results['slack_notify'] = False
        
except Exception as e:
    print(f"  ❌ Slack Notification: {e}")
    results['slack_notify'] = False

# =============================================================================
# TEST 4: Document Generation
# =============================================================================
print("\n" + "=" * 70)
print("TEST 4: Document Generation")
print("=" * 70)

try:
    from tailor_resume import tailor_resume
    from write_cover_letter import generate_cover_letter
    
    # Load base resume
    resume_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'base_resume.txt')
    with open(resume_path, 'r') as f:
        base_resume = f.read()
    
    test_job = {
        'title': 'Product Designer',
        'company': 'Spotify',
        'description': 'Design user experiences for music streaming platform.'
    }
    
    # Test resume tailoring
    print("  Testing resume tailoring...")
    resume_result = tailor_resume(base_resume, test_job['title'], test_job['company'], test_job['description'])
    
    if resume_result and resume_result.get('tailored_summary'):
        print(f"  ✅ Resume tailored: {resume_result['tailored_summary'][:50]}...")
        results['resume_tailor'] = True
    else:
        print(f"  ⚠️ Resume tailor partial: {resume_result}")
        results['resume_tailor'] = False
    
    # Test cover letter
    print("  Testing cover letter generation...")
    cover_result = generate_cover_letter(base_resume, test_job['title'], test_job['company'], test_job['description'])
    
    if cover_result and len(cover_result) > 100:
        print(f"  ✅ Cover letter generated: {len(cover_result)} chars")
        results['cover_letter'] = True
    else:
        print(f"  ⚠️ Cover letter issue: {len(cover_result) if cover_result else 0} chars")
        results['cover_letter'] = False
        
except Exception as e:
    print(f"  ❌ Document Generation: {e}")
    results['resume_tailor'] = False
    results['cover_letter'] = False

# =============================================================================
# TEST 5: Email Integration
# =============================================================================
print("\n" + "=" * 70)
print("TEST 5: Email Integration")
print("=" * 70)

try:
    from gmail_handler import get_email_summary, search_emails, get_credentials
    
    # Test credentials
    creds = get_credentials()
    if creds:
        print(f"  ✅ Gmail credentials valid")
    
    # Test email summary
    summary = get_email_summary()
    print(f"  ✅ Email summary: {summary['total']} emails in last 14 days")
    print(f"     Interviews: {summary['interview_requests']}")
    print(f"     Confirmations: {summary['applications_confirmed']}")
    
    # Test search
    emails = search_emails('newer_than:7d', max_results=5)
    print(f"  ✅ Email search works: {len(emails)} recent emails")
    
    results['email'] = True
except Exception as e:
    print(f"  ❌ Email Integration: {e}")
    results['email'] = False

# =============================================================================
# TEST 6: Scheduled Tasks
# =============================================================================
print("\n" + "=" * 70)
print("TEST 6: Scheduled Tasks")
print("=" * 70)

try:
    result = subprocess.run(
        ['powershell', '-NoProfile', '-Command', 
         'Get-ScheduledTask | Where-Object {$_.TaskName -like "JobAssistant*"} | Select-Object TaskName, State | Format-Table -AutoSize'],
        capture_output=True, text=True
    )
    
    if 'JobAssistant' in result.stdout:
        print(f"  ✅ Scheduled tasks found:")
        for line in result.stdout.strip().split('\n'):
            if 'JobAssistant' in line:
                print(f"     {line.strip()}")
        results['scheduled_tasks'] = True
    else:
        print(f"  ⚠️ No scheduled tasks found")
        results['scheduled_tasks'] = False
        
except Exception as e:
    print(f"  ❌ Scheduled Tasks: {e}")
    results['scheduled_tasks'] = False

# =============================================================================
# TEST 7: Gateway Process
# =============================================================================
print("\n" + "=" * 70)
print("TEST 7: Slack Action Listener Process")
print("=" * 70)

try:
    # Check for Python Slack listener OR node gateway
    result = subprocess.run(
        ['powershell', '-NoProfile', '-Command', 
         'Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, Name | Format-Table -AutoSize'],
        capture_output=True, text=True
    )
    node_result = subprocess.run(
        ['powershell', '-NoProfile', '-Command', 
         'Get-Process node -ErrorAction SilentlyContinue | Select-Object Id, Name | Format-Table -AutoSize'],
        capture_output=True, text=True
    )
    
    if 'python' in result.stdout or 'node' in node_result.stdout:
        print(f"  ✅ Listener process running")
        if 'python' in result.stdout:
            print(f"     Python Slack listener active")
        if 'node' in node_result.stdout:
            print(f"     Node gateway active")
        results['gateway'] = True
    else:
        print(f"  ⚠️ No listener process running")
        results['gateway'] = False
except Exception as e:
    print(f"  ❌ Process check failed: {e}")
    results['gateway'] = False

# =============================================================================
# TEST 8: Slack Action Listener Module
# =============================================================================
print("\n" + "=" * 70)
print("TEST 8: Slack Action Listener (import test)")
print("=" * 70)

try:
    from slack_action_listener import handle_auto_apply, handle_decline, handle_manual_apply, handle_preview_docs
    print(f"  ✅ Action handlers imported successfully")
    print(f"     - handle_auto_apply (🤖 Auto Apply)")
    print(f"     - handle_manual_apply (👤 I'll Apply)")
    print(f"     - handle_preview_docs (📄 Preview)")
    print(f"     - handle_decline (❌ Skip)")
    results['action_listener'] = True
except Exception as e:
    print(f"  ❌ Action Listener: {e}")
    results['action_listener'] = False

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("📊 END-TO-END TEST SUMMARY")
print("=" * 70)

passed = sum(1 for v in results.values() if v)
total = len(results)

for test, passed_test in results.items():
    status = "✅ PASS" if passed_test else "❌ FAIL"
    print(f"  {status}: {test}")

print("\n" + "-" * 70)
print(f"  TOTAL: {passed}/{total} tests passed")

if passed == total:
    print("\n🎉 ALL SYSTEMS OPERATIONAL!")
else:
    print(f"\n⚠️ {total - passed} test(s) need attention")

print("=" * 70)
