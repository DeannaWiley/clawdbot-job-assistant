#!/usr/bin/env python3
"""
System Health Check for ClawdBot Job Assistant
Run this to verify all components are working correctly.
"""
import os
import sys

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def check_env_vars():
    """Check required environment variables"""
    print("\n📋 Environment Variables:")
    required = {
        'OPENROUTER_API_KEY': 'OpenRouter LLM',
        'GROQ_API_KEY': 'Groq Free Fallback',
        'GEMINI_API_KEY': 'Gemini Free Fallback',
        'SLACK_BOT_TOKEN': 'Slack Bot',
        'SLACK_APP_TOKEN': 'Slack App',
    }
    optional = {
        'CAPTCHA_2CAPTCHA_KEY': '2Captcha Service',
        'CaptchaKey': '2Captcha (alt)',
    }
    
    all_ok = True
    for var, desc in required.items():
        val = os.environ.get(var)
        if val:
            print(f"   ✅ {desc}: Set")
        else:
            print(f"   ❌ {desc}: NOT SET")
            all_ok = False
    
    for var, desc in optional.items():
        val = os.environ.get(var)
        if val:
            print(f"   ✅ {desc}: Set (optional)")
        else:
            print(f"   ⚪ {desc}: Not set (optional)")
    
    return all_ok


def check_llm_fallback():
    """Test LLM fallback chain"""
    print("\n🤖 LLM Fallback Chain:")
    
    # Test Groq (our primary free fallback)
    try:
        import requests
        api_key = os.environ.get('GROQ_API_KEY')
        if api_key:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": "Say OK"}], "max_tokens": 5},
                timeout=10
            )
            if response.status_code == 200:
                print("   ✅ Groq: Working")
            else:
                print(f"   ❌ Groq: Error {response.status_code}")
        else:
            print("   ⚪ Groq: No API key")
    except Exception as e:
        print(f"   ❌ Groq: {e}")
    
    return True


def check_slack():
    """Test Slack connection"""
    print("\n💬 Slack Integration:")
    try:
        from slack_sdk import WebClient
        token = os.environ.get('SLACK_BOT_TOKEN')
        if token:
            client = WebClient(token=token)
            auth = client.auth_test()
            if auth['ok']:
                print(f"   ✅ Connected as: {auth['user']}")
                print(f"   ✅ Team: {auth['team']}")
                return True
            else:
                print("   ❌ Auth failed")
        else:
            print("   ❌ No SLACK_BOT_TOKEN")
    except Exception as e:
        print(f"   ❌ Slack error: {e}")
    return False


def check_files():
    """Check required files exist"""
    print("\n📁 Required Files:")
    base_path = r"C:\Users\deann\clawd"
    files = {
        "MEMORY.md": "Long-term memory",
        "SOUL.md": "Bot identity",
        "USER.md": "User info",
        "TOOLS.md": "Tool notes",
        "AGENTS.md": "Bot instructions",
        "job-assistant/data/base_resume.txt": "Base resume",
        "job-assistant/config.yaml": "Config",
    }
    
    all_ok = True
    for path, desc in files.items():
        full_path = os.path.join(base_path, path)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"   ✅ {desc}: {size} bytes")
        else:
            print(f"   ❌ {desc}: MISSING")
            all_ok = False
    
    return all_ok


def check_scheduled_tasks():
    """Check Windows scheduled tasks"""
    print("\n⏰ Scheduled Tasks:")
    import subprocess
    tasks = ['JobAssistant-Search', 'JobAssistant-MorningRollup']
    
    for task in tasks:
        try:
            result = subprocess.run(
                ['schtasks', '/query', '/tn', task, '/fo', 'LIST'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"   ✅ {task}: Configured")
            else:
                print(f"   ❌ {task}: Not found")
        except Exception as e:
            print(f"   ❌ {task}: Error - {e}")


def main():
    print("=" * 50)
    print("🦞 CLAWDBOT SYSTEM HEALTH CHECK")
    print("=" * 50)
    
    # Load env vars from User scope (use -NoProfile to avoid helper script output)
    import subprocess
    env_vars = ['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN', 'OPENROUTER_API_KEY', 
                'GROQ_API_KEY', 'GEMINI_API_KEY', 'CAPTCHA_2CAPTCHA_KEY', 'CaptchaKey']
    for var in env_vars:
        if not os.environ.get(var):
            try:
                result = subprocess.run(
                    ['powershell', '-NoProfile', '-Command', f'[Environment]::GetEnvironmentVariable("{var}", "User")'],
                    capture_output=True, text=True
                )
                value = result.stdout.strip()
                if value and not value.startswith('Clawdbot'):  # Filter out helper output
                    os.environ[var] = value
            except:
                pass
    
    env_ok = check_env_vars()
    files_ok = check_files()
    check_scheduled_tasks()
    slack_ok = check_slack()
    check_llm_fallback()
    
    print("\n" + "=" * 50)
    if env_ok and files_ok and slack_ok:
        print("✅ ALL SYSTEMS OPERATIONAL")
    else:
        print("⚠️  SOME ISSUES DETECTED - Review above")
    print("=" * 50)


if __name__ == "__main__":
    main()
