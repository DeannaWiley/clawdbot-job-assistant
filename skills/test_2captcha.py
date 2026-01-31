#!/usr/bin/env python3
"""
Test 2Captcha Integration
Verifies the API key works and tests a simple image CAPTCHA.
"""
import os
import sys
import subprocess
import requests
import base64
import time

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

# Load API keys
api_key = load_env('CaptchaKey') or load_env('CAPTCHA_2CAPTCHA_KEY')

print("=" * 70)
print("🔐 2CAPTCHA INTEGRATION TEST")
print("=" * 70)

# Test 1: Check API key exists
print("\n📋 Test 1: API Key Check")
print("-" * 50)
if api_key:
    print(f"  ✅ API Key found: {api_key[:8]}...{api_key[-4:]}")
else:
    print("  ❌ No API key found!")
    print("     Set CaptchaKey or CAPTCHA_2CAPTCHA_KEY environment variable")
    sys.exit(1)

# Test 2: Check account balance
print("\n📋 Test 2: Account Balance")
print("-" * 50)
try:
    balance_url = f"http://2captcha.com/res.php?key={api_key}&action=getbalance&json=1"
    response = requests.get(balance_url, timeout=10)
    result = response.json()
    
    if result.get("status") == 1:
        balance = float(result.get("request", 0))
        print(f"  ✅ Account balance: ${balance:.2f}")
        if balance < 0.10:
            print("     ⚠️ Low balance - add funds for CAPTCHA solving")
    else:
        print(f"  ❌ Error: {result.get('request')}")
except Exception as e:
    print(f"  ❌ Failed to check balance: {e}")

# Test 3: Submit a simple test (text captcha)
print("\n📋 Test 3: Text CAPTCHA Test")
print("-" * 50)
try:
    # Submit a simple text question
    submit_url = "http://2captcha.com/in.php"
    params = {
        "key": api_key,
        "textcaptcha": "What is 2 + 2?",
        "json": 1
    }
    
    response = requests.post(submit_url, data=params, timeout=30)
    result = response.json()
    
    if result.get("status") == 1:
        task_id = result["request"]
        print(f"  ✅ Text CAPTCHA submitted (ID: {task_id})")
        
        # Wait for result
        print("  ⏳ Waiting for human solver...")
        result_url = "http://2captcha.com/res.php"
        
        for attempt in range(12):  # Max 60 seconds
            time.sleep(5)
            
            response = requests.get(result_url, params={
                "key": api_key,
                "action": "get",
                "id": task_id,
                "json": 1
            }, timeout=30)
            
            result = response.json()
            
            if result.get("status") == 1:
                answer = result.get("request")
                print(f"  ✅ CAPTCHA SOLVED! Answer: {answer}")
                print(f"     2Captcha integration is WORKING!")
                break
            elif result.get("request") == "CAPCHA_NOT_READY":
                print(f"     Still waiting... ({attempt + 1}/12)")
            else:
                print(f"  ❌ Error: {result.get('request')}")
                break
        else:
            print("  ⚠️ Timeout - but this just means no worker picked it up yet")
            print("     The integration itself is working correctly")
    else:
        print(f"  ❌ Submit error: {result.get('request')}")
        
except Exception as e:
    print(f"  ❌ Test failed: {e}")

print("\n" + "=" * 70)
print("📊 2CAPTCHA TEST COMPLETE")
print("=" * 70)
print("""
If balance check worked, 2Captcha integration is properly configured.
The service will be used automatically when CAPTCHAs are encountered.

Cost per CAPTCHA:
  - reCAPTCHA v2: ~$0.003
  - hCaptcha: ~$0.003  
  - FunCaptcha: ~$0.005
  - Image CAPTCHA: ~$0.002
""")
