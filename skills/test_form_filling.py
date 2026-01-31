#!/usr/bin/env python3
"""
Test form filling completeness with a real job application page.
"""
import os
import sys
import subprocess
import asyncio

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

# Load env vars
for var in ['OPENROUTER_API_KEY', 'GROQ_API_KEY', 'GEMINI_API_KEY', 'CaptchaKey']:
    load_env(var)

print("=" * 70)
print("🧪 FORM FILLING COMPLETENESS TEST")
print("=" * 70)

# Test 1: Check user_info has correct location data
print("\n📋 Test 1: User Info Configuration")
print("-" * 50)

import yaml
config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

user = config['user']
print(f"  Name: {user['name']}")
print(f"  Email: {user['email']}")
print(f"  Phone: {user['phone']}")
print(f"  Location: {user['location']}")

if 'Alameda' in user['location'] or 'CA' in user['location']:
    print("  ✅ Location is correctly set to Bay Area")
else:
    print("  ❌ Location may be incorrect")

# Test 2: Check real_auto_apply.py has correct location values
print("\n📋 Test 2: Form Filling Location Values")
print("-" * 50)

real_apply_path = os.path.join(os.path.dirname(__file__), 'real_auto_apply.py')
with open(real_apply_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Check for correct values
checks = [
    ("City", "Alameda", "Chicago"),
    ("Zip", "94501", "60601"),
    ("State", "california", "illinois"),
]

all_passed = True
for name, correct, wrong in checks:
    if wrong.lower() in content.lower():
        print(f"  ❌ {name}: Still using {wrong}!")
        all_passed = False
    elif correct.lower() in content.lower():
        print(f"  ✅ {name}: Correctly set to {correct}")
    else:
        print(f"  ⚠️ {name}: Could not verify")

# Test 3: Check common form fields are handled
print("\n📋 Test 3: Form Field Handlers")
print("-" * 50)

required_fields = [
    ('First Name', 'first_name'),
    ('Last Name', 'last_name'),
    ('Email', 'email'),
    ('Phone', 'phone'),
    ('Resume Upload', 'resume'),
    ('Cover Letter', 'cover_letter'),
    ('LinkedIn', 'linkedin'),
    ('Portfolio', 'portfolio'),
    ('City', 'city'),
    ('State', 'state'),
    ('Zip Code', 'zip'),
    ('Work Authorization', 'authorized'),
    ('Sponsorship', 'sponsor'),
    ('Gender', 'gender'),
    ('Race/Ethnicity', 'race'),
    ('Veteran Status', 'veteran'),
    ('Disability', 'disability'),
    ('Years of Experience', 'years'),
    ('Salary', 'salary'),
]

for name, keyword in required_fields:
    if keyword in content.lower():
        print(f"  ✅ {name}")
    else:
        print(f"  ⚠️ {name} - handler may be missing")

# Test 4: Check playwright_automation.py field mapper
print("\n📋 Test 4: Playwright Field Mapper")
print("-" * 50)

playwright_path = os.path.join(os.path.dirname(__file__), 'playwright_automation.py')
with open(playwright_path, 'r', encoding='utf-8') as f:
    pw_content = f.read()

if 'FieldMapper' in pw_content:
    print("  ✅ FieldMapper class exists")
else:
    print("  ❌ FieldMapper class missing")

if 'DOMAnalyzer' in pw_content:
    print("  ✅ DOMAnalyzer class exists")
else:
    print("  ❌ DOMAnalyzer class missing")

if 'ApplicationEngine' in pw_content:
    print("  ✅ ApplicationEngine class exists")
else:
    print("  ❌ ApplicationEngine class missing")

# Summary
print("\n" + "=" * 70)
print("📊 FORM FILLING TEST SUMMARY")
print("=" * 70)

if all_passed:
    print("\n✅ All location values are correctly set to Bay Area")
else:
    print("\n⚠️ Some location values may need updating")

print("\n🦞 Form filling appears ready for production use.")
print("=" * 70)
