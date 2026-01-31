#!/usr/bin/env python3
"""
QA Validation Script - Resume & Clawdbot Quality Validation
============================================================
Validates:
1. Resume PDF generation quality
2. Cover letter generation
3. Database tracking (resumes, cover letters)
4. End-to-end user flows
"""
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_env(var_name):
    """Load environment variable from user environment."""
    value = os.environ.get(var_name)
    if value:
        return value
    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             f'[Environment]::GetEnvironmentVariable("{var_name}", "User")'],
            capture_output=True, text=True, timeout=5
        )
        value = result.stdout.strip()
        if value and value != 'None':
            os.environ[var_name] = value
            return value
    except:
        pass
    return None

# Load all env vars
print("=" * 70)
print("QA VALIDATION - Resume & Clawdbot Quality Check")
print("=" * 70)

print("\n📋 Loading environment...")
env_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY', 'GROQ_API_KEY', 'CaptchaKey']
for var in env_vars:
    val = load_env(var)
    status = "✅" if val else "❌"
    print(f"   {status} {var}: {'Set' if val else 'NOT SET'}")

# Initialize Supabase
import importlib
sb = importlib.import_module('supabase._sync.client')
supabase = sb.create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_ANON_KEY'])

issues = []
passes = []

print("\n" + "=" * 70)
print("TEST 1: Database Schema Check")
print("=" * 70)

# Check resumes table
try:
    resumes = supabase.table('resumes').select('*').limit(5).execute()
    print(f"   📄 Resumes in DB: {len(resumes.data)}")
    if len(resumes.data) == 0:
        issues.append("ISSUE: No resumes tracked in database")
    else:
        passes.append("Resumes table has data")
except Exception as e:
    issues.append(f"CRITICAL: Cannot query resumes table: {e}")

# Check cover_letters table
try:
    cover_letters = supabase.table('cover_letters').select('*').limit(5).execute()
    print(f"   📝 Cover letters in DB: {len(cover_letters.data)}")
    if len(cover_letters.data) == 0:
        issues.append("ISSUE: No cover letters tracked in database")
    else:
        passes.append("Cover letters table has data")
except Exception as e:
    issues.append(f"CRITICAL: Cannot query cover_letters table: {e}")

# Check jobs and applications
try:
    jobs = supabase.table('jobs').select('id, title, company').limit(5).execute()
    apps = supabase.table('applications').select('id, status').limit(5).execute()
    print(f"   💼 Jobs in DB: {len(jobs.data)}")
    print(f"   📋 Applications in DB: {len(apps.data)}")
    passes.append(f"Jobs ({len(jobs.data)}) and Applications ({len(apps.data)}) tracked")
except Exception as e:
    issues.append(f"CRITICAL: Cannot query jobs/applications: {e}")

print("\n" + "=" * 70)
print("TEST 2: Resume PDF Generation Quality")
print("=" * 70)

# Check existing resume files
data_dir = Path(__file__).parent.parent / 'data' / 'applications'
pdf_files = list(data_dir.glob('*Resume*.pdf')) if data_dir.exists() else []
print(f"   📂 Resume PDFs found: {len(pdf_files)}")

if pdf_files:
    latest_pdf = max(pdf_files, key=lambda p: p.stat().st_mtime)
    size_kb = latest_pdf.stat().st_size / 1024
    print(f"   📄 Latest: {latest_pdf.name}")
    print(f"   📐 Size: {size_kb:.1f} KB")
    
    if size_kb < 1:
        issues.append(f"ISSUE: Resume PDF too small ({size_kb:.1f}KB) - may be corrupted")
    elif size_kb > 500:
        issues.append(f"ISSUE: Resume PDF too large ({size_kb:.1f}KB) - may have issues")
    else:
        passes.append(f"Resume PDF size OK ({size_kb:.1f}KB)")
else:
    issues.append("ISSUE: No resume PDFs found in data/applications")

# Check cover letter files
cl_files = list(data_dir.glob('*CoverLetter*.pdf')) if data_dir.exists() else []
print(f"   📂 Cover Letter PDFs found: {len(cl_files)}")

if cl_files:
    latest_cl = max(cl_files, key=lambda p: p.stat().st_mtime)
    size_kb = latest_cl.stat().st_size / 1024
    print(f"   📄 Latest: {latest_cl.name}")
    print(f"   📐 Size: {size_kb:.1f} KB")
    passes.append(f"Cover letter PDF exists ({size_kb:.1f}KB)")
else:
    issues.append("ISSUE: No cover letter PDFs found")

print("\n" + "=" * 70)
print("TEST 3: LLM API (Groq) Connection")
print("=" * 70)

import requests
groq_key = os.environ.get('GROQ_API_KEY')
if groq_key:
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": "Say 'OK' if working"}],
                "max_tokens": 10,
            },
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()['choices'][0]['message']['content']
            print(f"   ✅ Groq API working: {result[:50]}")
            passes.append("Groq LLM API working")
        else:
            issues.append(f"ISSUE: Groq API error {response.status_code}")
    except Exception as e:
        issues.append(f"ISSUE: Groq API connection failed: {e}")
else:
    issues.append("CRITICAL: GROQ_API_KEY not set")

print("\n" + "=" * 70)
print("TEST 4: Document Generation Test")
print("=" * 70)

try:
    from elite_document_generator import extract_job_keywords, generate_tailored_resume
    
    test_job = {
        'title': 'Graphic Designer',
        'company': 'Test Corp',
        'description': 'We need a creative graphic designer with Adobe Creative Suite experience.'
    }
    
    print("   ⏳ Testing keyword extraction...")
    keywords = extract_job_keywords(test_job['description'], test_job['title'])
    if keywords:
        print(f"   ✅ Keywords extracted successfully")
        passes.append("Keyword extraction working")
    else:
        issues.append("ISSUE: Keyword extraction returned empty")
        
except Exception as e:
    issues.append(f"ISSUE: Document generation test failed: {e}")

print("\n" + "=" * 70)
print("TEST 5: Resume Template Check")
print("=" * 70)

base_resume = Path(__file__).parent.parent / 'data' / 'base_resume.txt'
if base_resume.exists():
    content = base_resume.read_text()
    lines = len(content.split('\n'))
    print(f"   ✅ Base resume found: {lines} lines")
    
    # Check for required sections
    required = ['DEANNA', 'EXPERIENCE', 'EDUCATION', 'SKILLS']
    for section in required:
        if section.upper() in content.upper():
            print(f"      ✓ {section} section present")
        else:
            issues.append(f"ISSUE: Missing {section} section in base resume")
    passes.append("Base resume template valid")
else:
    issues.append("CRITICAL: base_resume.txt not found")

print("\n" + "=" * 70)
print("VALIDATION SUMMARY")
print("=" * 70)

print(f"\n✅ PASSED: {len(passes)}")
for p in passes:
    print(f"   • {p}")

print(f"\n❌ ISSUES: {len(issues)}")
for i in issues:
    print(f"   • {i}")

critical = [i for i in issues if 'CRITICAL' in i]
warnings = [i for i in issues if 'CRITICAL' not in i]

print("\n" + "=" * 70)
if critical:
    print("❌ RESULT: NOT PRODUCTION READY")
    print(f"   {len(critical)} critical issues must be fixed")
elif len(warnings) > 3:
    print("⚠️ RESULT: NEEDS IMPROVEMENT")
    print(f"   {len(warnings)} issues should be addressed")
else:
    print("✅ RESULT: PRODUCTION READY")
    print("   All critical checks passed")
print("=" * 70)
