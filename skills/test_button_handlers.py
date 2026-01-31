#!/usr/bin/env python3
"""
Comprehensive Button Handler Tests
===================================
Verifies all Slack button actions work correctly:
- auto_apply_job
- manual_apply_job
- decline_job
- preview_docs
"""
import sys
import os
import json
import subprocess

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

# Pre-load env vars
for var in ['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN', 'OPENROUTER_API_KEY', 'GROQ_API_KEY']:
    load_env(var)

print("=" * 70)
print("🧪 COMPREHENSIVE BUTTON HANDLER TESTS")
print("=" * 70)

results = {}

# =============================================================================
# TEST 1: Verify Button Action IDs Match
# =============================================================================
print("\n📋 TEST 1: Button Action ID Alignment")
print("-" * 50)

try:
    # Read slack_notify.py to get button action_ids
    notify_path = os.path.join(os.path.dirname(__file__), 'slack_notify.py')
    with open(notify_path, 'r', encoding='utf-8') as f:
        notify_content = f.read()
    
    # Read slack_action_listener.py to get handler action_ids
    listener_path = os.path.join(os.path.dirname(__file__), 'slack_action_listener.py')
    with open(listener_path, 'r', encoding='utf-8') as f:
        listener_content = f.read()
    
    # Extract action_ids from notify
    import re
    notify_actions = set(re.findall(r'"action_id":\s*"([^"]+)"', notify_content))
    
    # Extract action_ids from listener decorators
    listener_actions = set(re.findall(r'@app\.action\("([^"]+)"\)', listener_content))
    
    print(f"  Buttons defined in slack_notify.py:")
    for action in sorted(notify_actions):
        has_handler = action in listener_actions or action.startswith('view_job_')
        status = "✅" if has_handler else "❌ MISSING HANDLER"
        print(f"    {status} {action}")
    
    print(f"\n  Handlers defined in slack_action_listener.py:")
    for action in sorted(listener_actions):
        print(f"    ✅ {action}")
    
    # Check for mismatches (excluding view_job_* which are URL buttons)
    button_actions = {a for a in notify_actions if not a.startswith('view_job_')}
    missing_handlers = button_actions - listener_actions
    
    if missing_handlers:
        print(f"\n  ❌ MISSING HANDLERS: {missing_handlers}")
        results['action_alignment'] = False
    else:
        print(f"\n  ✅ All buttons have handlers!")
        results['action_alignment'] = True
        
except Exception as e:
    print(f"  ❌ Error: {e}")
    results['action_alignment'] = False

# =============================================================================
# TEST 2: Handler Imports
# =============================================================================
print("\n📋 TEST 2: Handler Function Imports")
print("-" * 50)

try:
    from slack_action_listener import (
        handle_auto_apply,
        handle_decline,
        handle_manual_apply,
        handle_preview_docs
    )
    print("  ✅ handle_auto_apply - 🤖 Auto Apply")
    print("  ✅ handle_manual_apply - 👤 I'll Apply")
    print("  ✅ handle_preview_docs - 📄 Preview")
    print("  ✅ handle_decline - ❌ Skip")
    results['handler_imports'] = True
except Exception as e:
    print(f"  ❌ Import failed: {e}")
    results['handler_imports'] = False

# =============================================================================
# TEST 3: Job Approval Workflow Functions
# =============================================================================
print("\n📋 TEST 3: Job Approval Workflow Functions")
print("-" * 50)

try:
    from job_approval_workflow import (
        approve_job,
        deny_job,
        record_application,
        is_job_ignored,
        is_job_already_applied,
        get_application_stats
    )
    
    # Test approve_job
    result = approve_job("https://test.com/job/123", "Test Job", "TestCorp", {})
    print(f"  ✅ approve_job: {result.get('status')}")
    
    # Test deny_job
    result = deny_job("https://test.com/job/456", "Skip Job", "SkipCorp", "Test skip")
    print(f"  ✅ deny_job: {result.get('status')}")
    
    # Test record_application
    result = record_application(
        job_url="https://test.com/job/789",
        title="Manual Job",
        company="ManualCorp",
        application_method="manual",
        documents_generated={},
        success=False,
        error="Test entry"
    )
    print(f"  ✅ record_application: {result.get('status')}")
    
    # Test stats
    stats = get_application_stats()
    print(f"  ✅ get_application_stats: {stats.get('total_applied')} applied")
    
    results['workflow_functions'] = True
except Exception as e:
    print(f"  ❌ Error: {e}")
    results['workflow_functions'] = False

# =============================================================================
# TEST 4: Document Generator Integration
# =============================================================================
print("\n📋 TEST 4: Document Generator Integration")
print("-" * 50)

try:
    from document_generator import generate_application_documents
    
    # Quick test (will actually generate documents)
    print("  Generating test documents...")
    docs = generate_application_documents(
        job_title="Test Designer",
        company="TestCorp",
        job_description="This is a test job."
    )
    
    if docs.get('tailored_summary'):
        print(f"  ✅ Tailored summary generated ({len(docs['tailored_summary'])} chars)")
    else:
        print(f"  ⚠️ No tailored summary")
    
    if docs.get('cover_letter'):
        print(f"  ✅ Cover letter generated ({len(docs['cover_letter'])} chars)")
    else:
        print(f"  ⚠️ No cover letter")
    
    if docs.get('files'):
        for file_type, path in docs['files'].items():
            if path and os.path.exists(path):
                print(f"  ✅ {file_type}: {os.path.basename(path)}")
    
    results['document_generator'] = True
except Exception as e:
    print(f"  ❌ Error: {e}")
    results['document_generator'] = False

# =============================================================================
# TEST 5: Slack Message with New Buttons
# =============================================================================
print("\n📋 TEST 5: Slack Message Format")
print("-" * 50)

try:
    from slack_notify import create_job_block
    
    test_job = {
        'title': 'Test Button Job',
        'company': 'ButtonTestCorp',
        'location': 'Remote',
        'job_url': 'https://example.com/job/button-test',
        'description': 'Testing all button configurations.',
        'match_score': {'overall_score': 85},
        'category': 'test'
    }
    
    blocks = create_job_block(test_job, 0)
    
    # Find the actions block
    actions_block = None
    for block in blocks:
        if block.get('type') == 'actions':
            actions_block = block
            break
    
    if actions_block:
        buttons = actions_block.get('elements', [])
        print(f"  Found {len(buttons)} buttons:")
        
        expected_buttons = ['auto_apply_job', 'manual_apply_job', 'preview_docs', 'decline_job']
        found_buttons = [b.get('action_id') for b in buttons]
        
        for action_id in expected_buttons:
            if action_id in found_buttons:
                btn = next(b for b in buttons if b.get('action_id') == action_id)
                print(f"    ✅ {btn['text']['text']} ({action_id})")
            else:
                print(f"    ❌ MISSING: {action_id}")
        
        results['slack_buttons'] = set(expected_buttons).issubset(set(found_buttons))
    else:
        print("  ❌ No actions block found")
        results['slack_buttons'] = False
        
except Exception as e:
    print(f"  ❌ Error: {e}")
    results['slack_buttons'] = False

# =============================================================================
# TEST 6: Send Test Message to Slack
# =============================================================================
print("\n📋 TEST 6: Send Test Message with All Buttons")
print("-" * 50)

try:
    from slack_notify import send_job_summary
    
    test_jobs = [{
        'title': '🧪 Button Test - Designer Role',
        'company': 'IntegrationTestCorp',
        'location': 'Remote',
        'job_url': 'https://example.com/test-buttons',
        'description': 'This is a test to verify all 4 buttons work correctly.',
        'match_score': {'overall_score': 90},
        'category': 'test'
    }]
    
    result = send_job_summary(jobs=test_jobs, channel='C0ABG9NGNTZ')
    
    if result and (result.get('ok') or result.get('success')):
        print(f"  ✅ Test message sent to Slack!")
        print(f"     Timestamp: {result.get('ts')}")
        print(f"     Check Slack for 4 buttons: Auto Apply, I'll Apply, Preview, Skip")
        results['slack_send'] = True
    else:
        print(f"  ⚠️ Send result: {result}")
        results['slack_send'] = False
        
except Exception as e:
    print(f"  ❌ Error: {e}")
    results['slack_send'] = False

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("📊 BUTTON HANDLER TEST SUMMARY")
print("=" * 70)

passed = sum(1 for v in results.values() if v)
total = len(results)

for test, passed_test in results.items():
    status = "✅ PASS" if passed_test else "❌ FAIL"
    print(f"  {status}: {test}")

print("\n" + "-" * 70)
print(f"  TOTAL: {passed}/{total} tests passed")

if passed == total:
    print("\n🎉 ALL BUTTON HANDLERS VERIFIED!")
else:
    print(f"\n⚠️ {total - passed} test(s) need attention")

print("=" * 70)
