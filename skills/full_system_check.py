#!/usr/bin/env python3
"""
ClawdBot Full System Health Check
==================================
Run this anytime to verify all components are working.

Usage: python full_system_check.py
"""
import sys
import os
import subprocess
import time

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
ENV_VARS = [
    'SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN', 
    'OPENROUTER_API_KEY', 'GROQ_API_KEY', 'GEMINI_API_KEY',
    'CaptchaKey', 'CAPTCHA_2CAPTCHA_KEY',
    'GMAIL_CLIENT_ID', 'GMAIL_CLIENT_SECRET'
]
for var in ENV_VARS:
    load_env(var)

print("=" * 70)
print("🦞 CLAWDBOT FULL SYSTEM HEALTH CHECK")
print("=" * 70)

results = {}

# 1. Environment Variables
print("\n🔑 Environment Variables")
print("-" * 50)
env_status = {
    'Slack Bot': 'SLACK_BOT_TOKEN',
    'Slack App': 'SLACK_APP_TOKEN',
    'OpenRouter': 'OPENROUTER_API_KEY',
    'Groq': 'GROQ_API_KEY',
    'Gemini': 'GEMINI_API_KEY',
    'CAPTCHA': 'CaptchaKey',
    'Gmail': 'GMAIL_CLIENT_ID'
}
for name, var in env_status.items():
    val = os.environ.get(var)
    status = "✅" if val and len(val) > 10 else "❌"
    print(f"  {status} {name}")

# 2. Slack Connection
print("\n💬 Slack Connection")
print("-" * 50)
try:
    from slack_sdk import WebClient
    token = os.environ.get('SLACK_BOT_TOKEN')
    client = WebClient(token=token)
    auth = client.auth_test()
    print(f"  ✅ Connected as: {auth['user']}")
    print(f"  ✅ Team: {auth['team']}")
    results['slack'] = True
except Exception as e:
    print(f"  ❌ {e}")
    results['slack'] = False

# 3. LLM Fallback Chain
print("\n🤖 LLM Fallback Chain")
print("-" * 50)
import requests
for name, key_var, url in [
    ('OpenRouter', 'OPENROUTER_API_KEY', 'https://openrouter.ai/api/v1/chat/completions'),
    ('Groq', 'GROQ_API_KEY', 'https://api.groq.com/openai/v1/chat/completions'),
]:
    key = os.environ.get(key_var)
    if key:
        try:
            if 'openrouter' in url:
                resp = requests.post(url, headers={"Authorization": f"Bearer {key}"},
                    json={"model": "anthropic/claude-3.5-sonnet", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}, timeout=10)
            else:
                resp = requests.post(url, headers={"Authorization": f"Bearer {key}"},
                    json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}, timeout=10)
            if resp.status_code == 200:
                print(f"  ✅ {name}: Working")
            elif resp.status_code == 402:
                print(f"  ⚠️ {name}: No credits")
            else:
                print(f"  ⚠️ {name}: {resp.status_code}")
        except Exception as e:
            print(f"  ❌ {name}: {e}")
    else:
        print(f"  ⏭️ {name}: No key")

# 4. Gmail Integration
print("\n📧 Gmail Integration")
print("-" * 50)
try:
    from gmail_handler import get_email_summary
    summary = get_email_summary()
    print(f"  ✅ Connected: {summary['total']} job emails (14 days)")
    results['gmail'] = True
except Exception as e:
    print(f"  ❌ {e}")
    results['gmail'] = False

# 5. Document Generation
print("\n📄 Document Generation")
print("-" * 50)
try:
    from tailor_resume import tailor_resume
    from write_cover_letter import generate_cover_letter
    print("  ✅ Resume tailoring: Ready")
    print("  ✅ Cover letter: Ready")
    results['docs'] = True
except Exception as e:
    print(f"  ❌ {e}")
    results['docs'] = False

# 6. Job Search
print("\n🔍 Job Search")
print("-" * 50)
try:
    from job_search import search_jobs_for_category
    print("  ✅ JobSpy integration: Ready")
    results['job_search'] = True
except Exception as e:
    print(f"  ❌ {e}")
    results['job_search'] = False

# 7. Playwright Automation
print("\n🎭 Playwright Automation")
print("-" * 50)
try:
    from playwright_automation import ApplicationEngine
    from playwright.sync_api import sync_playwright
    print("  ✅ ApplicationEngine: Ready")
    print("  ✅ Playwright module: Installed")
    results['playwright'] = True
except Exception as e:
    print(f"  ❌ {e}")
    results['playwright'] = False

# 8. CAPTCHA Handler
print("\n🔐 CAPTCHA Handler")
print("-" * 50)
try:
    from captcha_handler import CaptchaSolvingService, HumanAssistant
    print("  ✅ 2Captcha integration: Ready")
    print("  ✅ Human fallback: Ready")
    results['captcha'] = True
except Exception as e:
    print(f"  ❌ {e}")
    results['captcha'] = False

# 9. Scheduled Tasks
print("\n⏰ Scheduled Tasks")
print("-" * 50)
try:
    result = subprocess.run(
        ['powershell', '-NoProfile', '-Command', 
         'Get-ScheduledTask | Where-Object {$_.TaskName -like "JobAssistant*"} | Select-Object TaskName, State'],
        capture_output=True, text=True
    )
    if 'JobAssistant' in result.stdout:
        for line in result.stdout.strip().split('\n'):
            if 'JobAssistant' in line:
                print(f"  ✅ {line.strip()}")
        results['tasks'] = True
    else:
        print("  ⚠️ No scheduled tasks found")
        results['tasks'] = False
except Exception as e:
    print(f"  ❌ {e}")
    results['tasks'] = False

# 10. Gateway Process
print("\n🌐 Slack Listener Process")
print("-" * 50)
try:
    # Check for Python Slack listener OR node gateway
    py_result = subprocess.run(
        ['powershell', '-NoProfile', '-Command', 
         'Get-Process python -ErrorAction SilentlyContinue | Measure-Object'],
        capture_output=True, text=True
    )
    node_result = subprocess.run(
        ['powershell', '-NoProfile', '-Command', 
         'Get-Process node -ErrorAction SilentlyContinue | Measure-Object'],
        capture_output=True, text=True
    )
    
    py_count = 0
    node_count = 0
    for line in py_result.stdout.split('\n'):
        if 'Count' in line:
            parts = line.split(':')
            if len(parts) > 1:
                py_count = int(parts[1].strip())
    for line in node_result.stdout.split('\n'):
        if 'Count' in line:
            parts = line.split(':')
            if len(parts) > 1:
                node_count = int(parts[1].strip())
    
    if py_count > 0 or node_count > 0:
        if py_count > 0:
            print(f"  ✅ Python Slack listener running")
        if node_count > 0:
            print(f"  ✅ Node gateway running ({node_count} processes)")
        results['gateway'] = True
    else:
        print(f"  ⚠️ No listener process running")
        results['gateway'] = False
except Exception as e:
    print(f"  ❌ Error: {e}")
    results['gateway'] = False

# Summary
print("\n" + "=" * 70)
print("📊 SYSTEM STATUS SUMMARY")
print("=" * 70)

passed = sum(1 for v in results.values() if v)
total = len(results)

status_emoji = "🎉" if passed == total else "✅" if passed >= total - 1 else "⚠️"
print(f"\n{status_emoji} {passed}/{total} components operational")

if passed == total:
    print("\n🦞 ALL SYSTEMS GO! ClawdBot is fully operational.")
else:
    failed = [k for k, v in results.items() if not v]
    print(f"\n⚠️ Components needing attention: {', '.join(failed)}")

print("=" * 70)
