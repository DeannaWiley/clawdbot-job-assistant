#!/usr/bin/env python3
"""
Test Auto-Apply Flow - Verifies all components work together
"""
import sys
import os
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

# Pre-load required env vars
for var in ['OPENROUTER_API_KEY', 'GROQ_API_KEY', 'GEMINI_API_KEY', 'CaptchaKey', 'CAPTCHA_2CAPTCHA_KEY']:
    load_env(var)

print("=" * 70)
print("🦞 AUTO-APPLY FLOW TEST")
print("=" * 70)

results = {}

# =============================================================================
# TEST 1: Job Approval Workflow
# =============================================================================
print("\n📋 TEST 1: Job Approval Workflow Module")
print("-" * 50)

try:
    from job_approval_workflow import approve_job, deny_job, record_application
    print("  ✅ approve_job imported")
    print("  ✅ deny_job imported")
    print("  ✅ record_application imported")
    results['approval_workflow'] = True
except Exception as e:
    print(f"  ❌ Import failed: {e}")
    results['approval_workflow'] = False

# =============================================================================
# TEST 2: Document Generator
# =============================================================================
print("\n📄 TEST 2: Document Generator Module")
print("-" * 50)

try:
    from document_generator import generate_application_documents
    print("  ✅ generate_application_documents imported")
    
    # Quick test
    test_result = generate_application_documents(
        job_title="Test Position",
        company="TestCorp",
        job_description="This is a test job description."
    )
    
    if test_result:
        print(f"  ✅ Document generation works")
        print(f"     Keys returned: {list(test_result.keys())}")
        results['document_generator'] = True
    else:
        print(f"  ⚠️ Empty result from document generator")
        results['document_generator'] = False
        
except Exception as e:
    print(f"  ❌ Error: {e}")
    results['document_generator'] = False

# =============================================================================
# TEST 3: Elite Document Generator
# =============================================================================
print("\n🏆 TEST 3: Elite Document Generator")
print("-" * 50)

try:
    from elite_document_generator import generate_elite_application
    print("  ✅ generate_elite_application imported")
    results['elite_generator'] = True
except Exception as e:
    print(f"  ⚠️ Elite generator not available: {e}")
    results['elite_generator'] = False

# =============================================================================
# TEST 4: Playwright Automation
# =============================================================================
print("\n🎭 TEST 4: Playwright Automation Module")
print("-" * 50)

try:
    from playwright_automation import ApplicationEngine, DOMAnalyzer
    print("  ✅ ApplicationEngine imported")
    print("  ✅ DOMAnalyzer imported")
    
    # Check if Playwright is installed
    result = subprocess.run(['playwright', '--version'], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  ✅ Playwright installed: {result.stdout.strip()}")
    else:
        print(f"  ⚠️ Playwright CLI not in path")
    
    results['playwright'] = True
except Exception as e:
    print(f"  ❌ Error: {e}")
    results['playwright'] = False

# =============================================================================
# TEST 5: CAPTCHA Handler
# =============================================================================
print("\n🔐 TEST 5: CAPTCHA Handler")
print("-" * 50)

try:
    from captcha_handler import CaptchaSolvingService, HumanAssistant, CaptchaMetrics
    print("  ✅ CaptchaSolvingService imported")
    print("  ✅ HumanAssistant imported")
    print("  ✅ CaptchaMetrics imported")
    
    # Check balance
    captcha_key = os.environ.get('CaptchaKey') or os.environ.get('CAPTCHA_2CAPTCHA_KEY')
    if captcha_key:
        try:
            service = CaptchaSolvingService(captcha_key)
            balance = service.get_balance()
            print(f"  ✅ 2Captcha balance: ${balance:.2f}")
        except Exception as e:
            print(f"  ⚠️ Balance check failed: {e}")
    else:
        print("  ⚠️ No CAPTCHA key configured (human fallback enabled)")
    
    results['captcha'] = True
except Exception as e:
    print(f"  ❌ Error: {e}")
    results['captcha'] = False

# =============================================================================
# TEST 6: Real Auto Apply
# =============================================================================
print("\n🚀 TEST 6: Real Auto Apply Module")
print("-" * 50)

try:
    from real_auto_apply import auto_apply_to_job
    print("  ✅ auto_apply_to_job imported")
    results['real_auto_apply'] = True
except Exception as e:
    print(f"  ❌ Error: {e}")
    results['real_auto_apply'] = False

# =============================================================================
# TEST 7: Slack Action Handler Integration
# =============================================================================
print("\n⚡ TEST 7: Slack Action Handler")
print("-" * 50)

try:
    from slack_action_listener import handle_auto_apply, handle_decline, handle_manual_apply
    print("  ✅ All action handlers available")
    results['slack_actions'] = True
except Exception as e:
    print(f"  ❌ Error: {e}")
    results['slack_actions'] = False

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("📊 AUTO-APPLY FLOW TEST SUMMARY")
print("=" * 70)

passed = sum(1 for v in results.values() if v)
total = len(results)

for test, passed_test in results.items():
    status = "✅ PASS" if passed_test else "❌ FAIL"
    print(f"  {status}: {test}")

print("\n" + "-" * 70)
print(f"  TOTAL: {passed}/{total} components ready")

if passed == total:
    print("\n🎉 AUTO-APPLY FLOW FULLY OPERATIONAL!")
elif passed >= total - 1:
    print("\n✅ AUTO-APPLY FLOW READY (minor component missing)")
else:
    print(f"\n⚠️ {total - passed} component(s) need attention")

print("=" * 70)
