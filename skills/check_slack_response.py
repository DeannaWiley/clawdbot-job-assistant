#!/usr/bin/env python3
"""Check Slack channel for ClawdBot responses"""
import subprocess
import time

# Load Slack token
result = subprocess.run(
    ['powershell', '-NoProfile', '-Command', 
     '[Environment]::GetEnvironmentVariable("SLACK_BOT_TOKEN", "User")'],
    capture_output=True, text=True
)
token = result.stdout.strip()

from slack_sdk import WebClient
client = WebClient(token=token)

print("Checking for ClawdBot responses...\n")

# Get recent messages from channel
response = client.conversations_history(channel='C0ABG9NGNTZ', limit=10)

for msg in reversed(response['messages']):
    user = msg.get('user', '')
    bot_id = msg.get('bot_id', '')
    text = msg.get('text', '')
    ts = msg.get('ts', '')
    
    # Format timestamp
    from datetime import datetime
    dt = datetime.fromtimestamp(float(ts))
    time_str = dt.strftime('%H:%M:%S')
    
    # Determine sender
    if bot_id:
        sender = "🤖 ClawdBot"
    elif user == 'U08AN2CGRTA':  # Deanna's user ID (approximate)
        sender = "👤 Deanna"
    else:
        sender = f"👤 User ({user})"
    
    print(f"[{time_str}] {sender}:")
    print(f"  {text[:300]}{'...' if len(text) > 300 else ''}")
    print("-" * 60)
