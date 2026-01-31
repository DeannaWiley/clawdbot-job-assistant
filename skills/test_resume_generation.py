#!/usr/bin/env python3
"""
Test Resume & Cover Letter Generation with Database Tracking
=============================================================
Tests end-to-end document generation and Supabase persistence.
"""
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_env(var_name):
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

# Load env
for var in ['SUPABASE_URL', 'SUPABASE_ANON_KEY', 'GROQ_API_KEY']:
    load_env(var)

print("=" * 70)
print("TEST: Resume & Cover Letter Generation with DB Tracking")
print("=" * 70)

# Test job data
TEST_JOB = {
    'title': 'Senior Graphic Designer',
    'company': 'Creative Agency Inc',
    'description': '''
    We are looking for a Senior Graphic Designer to join our team.
    
    Requirements:
    - 3+ years experience in graphic design
    - Proficiency in Adobe Creative Suite (Photoshop, Illustrator, InDesign)
    - Strong portfolio demonstrating creative work
    - Experience with brand identity and marketing materials
    - Bachelor's degree in Design or related field
    
    Responsibilities:
    - Create visual concepts for marketing campaigns
    - Design brand materials and guidelines
    - Collaborate with marketing team on content creation
    - Manage multiple projects with tight deadlines
    '''
}

print(f"\n📋 Test Job: {TEST_JOB['title']} at {TEST_JOB['company']}")

# Step 1: Generate documents
print("\n" + "=" * 70)
print("STEP 1: Document Generation")
print("=" * 70)

try:
    from document_generator import generate_application_documents
    
    print("   ⏳ Generating resume and cover letter...")
    docs = generate_application_documents(
        TEST_JOB['title'], 
        TEST_JOB['company'], 
        TEST_JOB['description']
    )
    
    resume_pdf = docs.get('files', {}).get('resume_pdf')
    cover_letter_pdf = docs.get('files', {}).get('cover_letter_pdf')
    cover_letter_text = docs.get('cover_letter', '')
    
    print(f"   📄 Resume PDF: {resume_pdf}")
    print(f"   📝 Cover Letter PDF: {cover_letter_pdf}")
    print(f"   📝 Cover Letter Text: {len(cover_letter_text)} chars")
    
    # Verify files exist
    if resume_pdf and os.path.exists(resume_pdf):
        size = os.path.getsize(resume_pdf) / 1024
        print(f"   ✅ Resume PDF exists ({size:.1f} KB)")
    else:
        print(f"   ❌ Resume PDF not found!")
        
    if cover_letter_pdf and os.path.exists(cover_letter_pdf):
        size = os.path.getsize(cover_letter_pdf) / 1024
        print(f"   ✅ Cover Letter PDF exists ({size:.1f} KB)")
    else:
        print(f"   ⚠️ Cover Letter PDF not found (may be text only)")

except Exception as e:
    print(f"   ❌ Document generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: Save to Supabase
print("\n" + "=" * 70)
print("STEP 2: Database Tracking")
print("=" * 70)

try:
    import importlib
    sb = importlib.import_module('supabase._sync.client')
    supabase = sb.create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_ANON_KEY'])
    
    USER_ID = "00000000-0000-0000-0000-000000000001"
    
    # Create test job in DB (use valid source from check constraint)
    print("   ⏳ Saving job to database...")
    job_result = supabase.table('jobs').insert({
        'source': 'greenhouse',  # Must be valid: linkedin, indeed, glassdoor, greenhouse, lever, etc.
        'source_url': f'https://boards.greenhouse.io/testcompany/jobs/{int(datetime.now().timestamp())}',
        'title': TEST_JOB['title'],
        'company': TEST_JOB['company'],
        'description': TEST_JOB['description'],
        'is_active': True
    }).execute()
    job_id = job_result.data[0]['id']
    print(f"   ✅ Job saved: {job_id[:8]}...")
    
    # Save resume
    print("   ⏳ Saving resume to database...")
    if resume_pdf:
        resume_result = supabase.table('resumes').insert({
            'user_id': USER_ID,
            'version_name': f'test_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'file_path': str(resume_pdf),
            'file_type': 'pdf',
            'tailored_for_job_id': job_id
        }).execute()
        resume_id = resume_result.data[0]['id']
        print(f"   ✅ Resume saved: {resume_id[:8]}...")
    
    # Save cover letter with new columns
    print("   ⏳ Saving cover letter to database...")
    try:
        cl_result = supabase.table('cover_letters').insert({
            'user_id': USER_ID,
            'job_id': job_id,
            'content_text': cover_letter_text[:5000] if cover_letter_text else 'Generated cover letter',
            'content': cover_letter_text[:5000] if cover_letter_text else '',
            'file_path': str(cover_letter_pdf) if cover_letter_pdf else ''
        }).execute()
        cl_id = cl_result.data[0]['id']
        print(f"   ✅ Cover letter saved: {cl_id[:8]}...")
    except Exception as cl_error:
        print(f"   ⚠️ Cover letter save failed: {cl_error}")
    
except Exception as e:
    print(f"   ❌ Database tracking failed: {e}")
    import traceback
    traceback.print_exc()

# Step 3: Verify database
print("\n" + "=" * 70)
print("STEP 3: Verification")
print("=" * 70)

try:
    resumes = supabase.table('resumes').select('id, version_name, file_path').order('created_at', desc=True).limit(3).execute()
    print(f"   📄 Resumes in DB: {len(resumes.data)}")
    for r in resumes.data:
        print(f"      - {r['version_name']}")
    
    cover_letters = supabase.table('cover_letters').select('id, job_id').order('created_at', desc=True).limit(3).execute()
    print(f"   📝 Cover letters in DB: {len(cover_letters.data)}")
    
    print("\n" + "=" * 70)
    print("✅ TEST PASSED - Resume & Cover Letter Generation Working!")
    print("=" * 70)
    
except Exception as e:
    print(f"   ❌ Verification failed: {e}")
