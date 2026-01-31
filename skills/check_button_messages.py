#!/usr/bin/env python3
"""Check recent Slack messages for button availability."""
import os
import subprocess

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

load_env('SLACK_BOT_TOKEN')

from slack_sdk import WebClient
client = WebClient(token=os.environ.get('SLACK_BOT_TOKEN'))

print("=" * 70)
print("📋 RECENT SLACK MESSAGES WITH BUTTONS")
print("=" * 70)

result = client.conversations_history(channel='C0ABG9NGNTZ', limit=10)
messages = result.get('messages', [])

button_count = 0
for msg in messages:
    blocks = msg.get('blocks', [])
    for block in blocks:
        if block.get('type') == 'actions':
            elements = block.get('elements', [])
            ts = msg.get('ts', 'unknown')
            text = msg.get('text', '')[:60]
            print(f"\n[{ts}] {text}...")
            for el in elements:
                btn_text = el.get('text', {}).get('text', '?')
                action_id = el.get('action_id', '?')
                print(f"  • {btn_text} ({action_id})")
                button_count += 1

print(f"\n" + "=" * 70)
print(f"Found {button_count} buttons in recent messages")
print("=" * 70)
