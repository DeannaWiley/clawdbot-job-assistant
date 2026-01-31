#!/usr/bin/env python3
"""Test LLM fallback chain - OpenRouter -> Groq -> Gemini"""
import os
import sys
import subprocess

# Load env vars from Windows User scope
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

# Load all keys
print("=" * 50)
print("🔑 Loading API Keys...")
print("=" * 50)

openrouter_key = load_env('OPENROUTER_API_KEY')
groq_key = load_env('GROQ_API_KEY')
gemini_key = load_env('GEMINI_API_KEY')

print(f"OpenRouter: {'✅ SET' if openrouter_key else '❌ NOT SET'}")
print(f"Groq:       {'✅ SET' if groq_key else '❌ NOT SET'}")
print(f"Gemini:     {'✅ SET' if gemini_key else '❌ NOT SET'}")

# Test each provider
import requests

print("\n" + "=" * 50)
print("🧪 Testing Each Provider...")
print("=" * 50)

test_prompt = "Say 'Hello from [provider name]' in exactly 5 words."

# Test OpenRouter
print("\n1️⃣ OpenRouter:")
if openrouter_key:
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {openrouter_key}"},
            json={
                "model": "anthropic/claude-3.5-sonnet",
                "messages": [{"role": "user", "content": test_prompt}],
                "max_tokens": 50
            },
            timeout=30
        )
        if resp.status_code == 200:
            result = resp.json()['choices'][0]['message']['content']
            print(f"   ✅ Working: {result[:50]}")
        elif resp.status_code == 402:
            print(f"   ⚠️ Insufficient credits (402)")
        else:
            print(f"   ❌ Error {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
else:
    print("   ⏭️ Skipped (no key)")

# Test Groq
print("\n2️⃣ Groq:")
if groq_key:
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": test_prompt}],
                "max_tokens": 50
            },
            timeout=30
        )
        if resp.status_code == 200:
            result = resp.json()['choices'][0]['message']['content']
            print(f"   ✅ Working: {result[:50]}")
        else:
            print(f"   ❌ Error {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
else:
    print("   ⏭️ Skipped (no key)")

# Test Gemini
print("\n3️⃣ Gemini:")
if gemini_key:
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
            json={"contents": [{"parts": [{"text": test_prompt}]}]},
            timeout=30
        )
        if resp.status_code == 200:
            result = resp.json()['candidates'][0]['content']['parts'][0]['text']
            print(f"   ✅ Working: {result[:50]}")
        else:
            print(f"   ❌ Error {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
else:
    print("   ⏭️ Skipped (no key)")

print("\n" + "=" * 50)
print("📊 Summary")
print("=" * 50)
working = []
if openrouter_key: working.append("OpenRouter")
if groq_key: working.append("Groq")
if gemini_key: working.append("Gemini")
print(f"Fallback chain: {' -> '.join(working) if working else 'NONE CONFIGURED!'}")
