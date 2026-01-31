#!/usr/bin/env python3
"""
Test CAPTCHA screenshot capture and Slack upload functionality.
"""
import os
import sys
import asyncio
import subprocess

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

for var in ['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN']:
    load_env(var)

print("=" * 70)
print("🔐 CAPTCHA SCREENSHOT TEST")
print("=" * 70)

# Test 1: Verify screenshot directory exists
print("\n📋 Test 1: Screenshot Directory")
print("-" * 50)

screenshot_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'captcha_screenshots')
if os.path.exists(screenshot_dir):
    files = os.listdir(screenshot_dir)
    print(f"  ✅ Directory exists: {screenshot_dir}")
    print(f"     Contains {len(files)} files")
else:
    os.makedirs(screenshot_dir, exist_ok=True)
    print(f"  ✅ Created directory: {screenshot_dir}")

# Test 2: Verify HumanAssistant class has screenshot method
print("\n📋 Test 2: HumanAssistant Screenshot Method")
print("-" * 50)

try:
    from captcha_handler import HumanAssistant
    assistant = HumanAssistant()
    
    if hasattr(assistant, '_capture_captcha_screenshot'):
        print("  ✅ _capture_captcha_screenshot method exists")
    else:
        print("  ❌ _capture_captcha_screenshot method missing")
    
    if hasattr(assistant, '_send_slack_notification_with_screenshot'):
        print("  ✅ _send_slack_notification_with_screenshot method exists")
    else:
        print("  ❌ _send_slack_notification_with_screenshot method missing")
    
    print(f"  ✅ Slack channel: {assistant.slack_channel}")
    print(f"  ✅ Timeout: {assistant.timeout_seconds}s")
    
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 3: Test Slack file upload capability
print("\n📋 Test 3: Slack File Upload Test")
print("-" * 50)

try:
    from slack_sdk import WebClient
    client = WebClient(token=os.environ.get('SLACK_BOT_TOKEN'))
    
    # Create a test image
    test_image_path = os.path.join(screenshot_dir, 'test_captcha.png')
    
    # Create a simple test image using PIL if available, otherwise skip
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(img)
        draw.rectangle([20, 20, 380, 180], outline='red', width=3)
        draw.text((100, 80), "CAPTCHA TEST", fill='black')
        img.save(test_image_path)
        print(f"  ✅ Test image created: {test_image_path}")
        
        # Upload to Slack
        result = client.files_upload_v2(
            channel='C0ABG9NGNTZ',
            file=test_image_path,
            title="CAPTCHA Screenshot Test",
            initial_comment="🔐 *CAPTCHA Screenshot Test*\n\nThis tests the screenshot upload for human CAPTCHA solving."
        )
        
        if result.get('ok') or result.get('file'):
            print(f"  ✅ File uploaded to Slack successfully!")
        else:
            print(f"  ⚠️ Upload result: {result}")
            
    except ImportError:
        print("  ⚠️ PIL not installed - skipping image creation")
        print("     Install with: pip install Pillow")
        
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 4: Verify CAPTCHA handlers in listener
print("\n📋 Test 4: CAPTCHA Button Handlers")
print("-" * 50)

try:
    from slack_action_listener import handle_captcha_solved, handle_captcha_skip
    print("  ✅ handle_captcha_solved imported")
    print("  ✅ handle_captcha_skip imported")
except ImportError as e:
    print(f"  ❌ Import failed: {e}")

print("\n" + "=" * 70)
print("📊 CAPTCHA SCREENSHOT TEST SUMMARY")
print("=" * 70)
print("""
When a CAPTCHA is detected during job application:
1. Screenshot is captured of the CAPTCHA element
2. Screenshot is uploaded to Slack with buttons
3. User can solve CAPTCHA on their phone/desktop
4. ClawdBot detects when solved and continues

The screenshot allows remote solving without needing desktop access!
""")
print("=" * 70)
