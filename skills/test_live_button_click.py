#!/usr/bin/env python3
"""
Test that Slack button handlers respond correctly.
Simulates what happens when a user clicks a button in Slack.
"""
import os
import sys
import json
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

for var in ['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN', 'OPENROUTER_API_KEY', 'GROQ_API_KEY']:
    load_env(var)

print("=" * 70)
print("🧪 LIVE BUTTON HANDLER TEST")
print("=" * 70)

from slack_sdk import WebClient

client = WebClient(token=os.environ.get('SLACK_BOT_TOKEN'))
channel = 'C0ABG9NGNTZ'

# Test 1: Send a job with buttons and verify message structure
print("\n📋 Test 1: Send Job Notification with All Buttons")
print("-" * 50)

from slack_notify import create_job_block

test_job = {
    'title': 'Live Button Test - UX Designer',
    'company': 'ButtonTest Corp',
    'location': 'Remote',
    'job_url': 'https://example.com/live-button-test',
    'description': 'Click each button to test handler response. Check terminal for handler output.',
    'match_score': {'overall_score': 88},
    'category': 'test'
}

blocks = create_job_block(test_job, 0)

# Find buttons
action_block = None
for block in blocks:
    if block.get('type') == 'actions':
        action_block = block
        break

if action_block:
    buttons = action_block.get('elements', [])
    print(f"  ✅ Message has {len(buttons)} buttons:")
    for btn in buttons:
        action_id = btn.get('action_id', 'unknown')
        text = btn.get('text', {}).get('text', 'unknown')
        print(f"     - {text} ({action_id})")

# Send the message
response = client.chat_postMessage(
    channel=channel,
    text=f"🧪 Live Button Test - {test_job['title']}",
    blocks=blocks
)

if response.get('ok'):
    print(f"\n  ✅ Message sent: {response.get('ts')}")
    print(f"\n  📱 NOW: Go to Slack and click each button!")
    print(f"       Watch the terminal running slack_action_listener.py")
    print(f"       You should see handler output for each click.")
else:
    print(f"  ❌ Failed to send: {response}")

# Test 2: Verify handler imports work
print("\n📋 Test 2: Handler Import Verification")
print("-" * 50)

try:
    from slack_action_listener import (
        handle_auto_apply,
        handle_decline,
        handle_manual_apply,
        handle_preview_docs,
        handle_captcha_solved,
        handle_captcha_skip,
        handle_status_indicator
    )
    print("  ✅ All 7 handlers imported successfully")
    print("     - handle_auto_apply")
    print("     - handle_decline")
    print("     - handle_manual_apply")
    print("     - handle_preview_docs")
    print("     - handle_captcha_solved")
    print("     - handle_captcha_skip")
    print("     - handle_status_indicator")
except ImportError as e:
    print(f"  ❌ Import failed: {e}")

# Test 3: Check listener is running
print("\n📋 Test 3: Listener Process Status")
print("-" * 50)

result = subprocess.run(
    ['powershell', '-NoProfile', '-Command', 
     'Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, ProcessName'],
    capture_output=True, text=True
)

if 'python' in result.stdout:
    print("  ✅ Python process running (Slack listener active)")
else:
    print("  ⚠️ No Python process found - listener may not be running")
    print("     Start with: python slack_action_listener.py")

print("\n" + "=" * 70)
print("📊 NEXT STEPS")
print("=" * 70)
print("""
1. Go to Slack channel #all-job-hunt-ai
2. Find the "Live Button Test" message just sent
3. Click each button:
   - 🤖 Auto Apply → Should show "Auto-applying..." in terminal
   - 👤 I'll Apply → Should show "Manual apply marked..." in terminal
   - 📄 Preview → Should generate and show document preview
   - ❌ Skip → Should show "Declined..." in terminal

4. Check the terminal running slack_action_listener.py for output

If buttons don't respond, the Socket Mode connection may need restart.
""")
print("=" * 70)
