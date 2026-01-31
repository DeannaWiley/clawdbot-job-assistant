#!/usr/bin/env python3
"""Check available Groq models."""
import os
import subprocess
import requests

# Load Groq key
result = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     '[Environment]::GetEnvironmentVariable("GROQ_API_KEY", "User")'],
    capture_output=True, text=True, timeout=5
)
groq_key = result.stdout.strip()

# Get models
resp = requests.get(
    'https://api.groq.com/openai/v1/models',
    headers={'Authorization': f'Bearer {groq_key}'}
)

if resp.status_code == 200:
    models = resp.json().get('data', [])
    print("Available Groq models:")
    for m in models:
        print(f"  - {m['id']}")
else:
    print(f"Error: {resp.status_code} - {resp.text}")
