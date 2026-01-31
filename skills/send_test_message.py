#!/usr/bin/env python3
"""Send test message to ClawdBot via Slack"""
import subprocess
import os

# Load Slack token
result = subprocess.run(
    ['powershell', '-NoProfile', '-Command', 
     '[Environment]::GetEnvironmentVariable("SLACK_BOT_TOKEN", "User")'],
    capture_output=True, text=True
)
token = result.stdout.strip()

from slack_sdk import WebClient
client = WebClient(token=token)

# Send test message to ClawdBot channel
message = """Hey ClawdBot! Quick check:

1. Can you verify if my application to the Figma job went through? Check my email for any confirmation.
2. What are your current capabilities? I want to make sure you know about all the tools I've set up for you.
3. Can you generate a test cover letter for a "Senior Product Designer" role at "Spotify" to verify document generation works?

Thanks!"""

response = client.chat_postMessage(
    channel='C0ABG9NGNTZ',
    text=message
)

if response['ok']:
    print(f"✅ Message sent to #{response['channel']}")
    print(f"   Timestamp: {response['ts']}")
else:
    print("❌ Failed to send message")
