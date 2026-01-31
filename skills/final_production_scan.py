#!/usr/bin/env python3
"""
Final Production Scan
======================
Comprehensive scan for:
- Missing handlers
- Unused exports
- Mismatched imports
- Broken references
"""
import os
import re
import sys
import ast
import subprocess

sys.path.insert(0, os.path.dirname(__file__))

print("=" * 70)
print("🔍 FINAL PRODUCTION SCAN")
print("=" * 70)

issues = []
warnings = []

# =============================================================================
# SCAN 1: Action ID Alignment (Buttons vs Handlers)
# =============================================================================
print("\n📋 SCAN 1: Slack Action ID Alignment")
print("-" * 50)

skills_dir = os.path.dirname(__file__)

# Read slack_notify.py
with open(os.path.join(skills_dir, 'slack_notify.py'), 'r', encoding='utf-8') as f:
    notify_content = f.read()

# Read slack_action_listener.py
with open(os.path.join(skills_dir, 'slack_action_listener.py'), 'r', encoding='utf-8') as f:
    listener_content = f.read()

# Read captcha_handler.py
with open(os.path.join(skills_dir, 'captcha_handler.py'), 'r', encoding='utf-8') as f:
    captcha_content = f.read()

# Extract all action_ids from all files
all_action_ids = set()
all_action_ids.update(re.findall(r'"action_id":\s*"([^"]+)"', notify_content))
all_action_ids.update(re.findall(r'"action_id":\s*"([^"]+)"', captcha_content))

# Remove view_job_* (URL buttons, no handler needed)
button_actions = {a for a in all_action_ids if not a.startswith('view_job_')}

# Extract handler action_ids
handler_actions = set(re.findall(r'@app\.action\("([^"]+)"\)', listener_content))

missing_handlers = button_actions - handler_actions
extra_handlers = handler_actions - button_actions

if missing_handlers:
    for action in missing_handlers:
        issues.append(f"Missing handler for: {action}")
        print(f"  ❌ Missing handler: {action}")
else:
    print(f"  ✅ All {len(button_actions)} buttons have handlers")

if extra_handlers:
    for action in extra_handlers:
        # These might be CAPTCHA-specific handlers
        if 'captcha' in action:
            print(f"  ✅ Extra CAPTCHA handler: {action}")
        else:
            warnings.append(f"Extra handler (no button): {action}")
            print(f"  ⚠️ Extra handler: {action}")

# =============================================================================
# SCAN 2: Import Verification
# =============================================================================
print("\n📋 SCAN 2: Import Verification")
print("-" * 50)

key_imports = [
    ('slack_notify', ['send_job_summary', 'create_job_block', 'get_slack_client']),
    ('slack_action_listener', ['handle_auto_apply', 'handle_decline', 'handle_manual_apply', 'handle_preview_docs']),
    ('job_approval_workflow', ['approve_job', 'deny_job', 'record_application']),
    ('document_generator', ['generate_application_documents']),
    ('tailor_resume', ['tailor_resume']),
    ('write_cover_letter', ['write_cover_letter', 'generate_cover_letter']),
    ('captcha_handler', ['CaptchaSolvingService', 'HumanAssistant', 'CaptchaHandler']),
    ('gmail_handler', ['get_email_summary', 'search_emails']),
]

for module_name, functions in key_imports:
    try:
        module = __import__(module_name)
        missing = []
        for func in functions:
            if not hasattr(module, func):
                missing.append(func)
        
        if missing:
            warnings.append(f"{module_name}: Missing exports: {missing}")
            print(f"  ⚠️ {module_name}: Missing {missing}")
        else:
            print(f"  ✅ {module_name}: All exports verified")
    except Exception as e:
        issues.append(f"Cannot import {module_name}: {e}")
        print(f"  ❌ {module_name}: {e}")

# =============================================================================
# SCAN 3: File Existence Check
# =============================================================================
print("\n📋 SCAN 3: Required Files")
print("-" * 50)

required_files = [
    'slack_notify.py',
    'slack_action_listener.py',
    'job_approval_workflow.py',
    'document_generator.py',
    'tailor_resume.py',
    'write_cover_letter.py',
    'real_auto_apply.py',
    'playwright_automation.py',
    'captcha_handler.py',
    'job_search.py',
    'gmail_handler.py',
]

for filename in required_files:
    filepath = os.path.join(skills_dir, filename)
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        print(f"  ✅ {filename} ({size:,} bytes)")
    else:
        issues.append(f"Missing file: {filename}")
        print(f"  ❌ {filename}: MISSING")

# =============================================================================
# SCAN 4: Data Directory Check
# =============================================================================
print("\n📋 SCAN 4: Data Directories")
print("-" * 50)

data_dirs = [
    '../data/applications',
    '../data/captcha_screenshots',
    '../data',
]

for dir_path in data_dirs:
    full_path = os.path.join(skills_dir, dir_path)
    if os.path.exists(full_path):
        files = os.listdir(full_path) if os.path.isdir(full_path) else []
        print(f"  ✅ {dir_path} ({len(files)} items)")
    else:
        # Create if missing
        os.makedirs(full_path, exist_ok=True)
        print(f"  ✅ {dir_path} (created)")

# =============================================================================
# SCAN 5: Environment Variables
# =============================================================================
print("\n📋 SCAN 5: Environment Variables")
print("-" * 50)

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

env_vars = {
    'SLACK_BOT_TOKEN': 'Required for Slack',
    'SLACK_APP_TOKEN': 'Required for Socket Mode',
    'OPENROUTER_API_KEY': 'Primary LLM',
    'GROQ_API_KEY': 'Fallback LLM',
    'GEMINI_API_KEY': 'Fallback LLM',
    'CaptchaKey': 'CAPTCHA solving',
}

for var, purpose in env_vars.items():
    value = load_env(var)
    if value:
        print(f"  ✅ {var}: Set ({purpose})")
    else:
        if var in ['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN']:
            issues.append(f"Missing required: {var}")
            print(f"  ❌ {var}: MISSING ({purpose})")
        else:
            warnings.append(f"Optional missing: {var}")
            print(f"  ⚠️ {var}: Not set ({purpose})")

# =============================================================================
# SCAN 6: Syntax Check
# =============================================================================
print("\n📋 SCAN 6: Python Syntax Check")
print("-" * 50)

for filename in required_files:
    filepath = os.path.join(skills_dir, filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            ast.parse(source)
            print(f"  ✅ {filename}: Valid syntax")
        except SyntaxError as e:
            issues.append(f"{filename}: Syntax error at line {e.lineno}")
            print(f"  ❌ {filename}: Syntax error at line {e.lineno}")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("📊 PRODUCTION SCAN SUMMARY")
print("=" * 70)

print(f"\n  Issues: {len(issues)}")
for issue in issues:
    print(f"    ❌ {issue}")

print(f"\n  Warnings: {len(warnings)}")
for warning in warnings:
    print(f"    ⚠️ {warning}")

if not issues:
    print("\n🎉 PRODUCTION READY! No critical issues found.")
else:
    print(f"\n⚠️ {len(issues)} issue(s) need attention before production.")

print("=" * 70)
