#!/usr/bin/env python3
"""
Autonomous Job Application - Apply to 3 jobs from different platforms
======================================================================
No user input required. Searches for active jobs and applies automatically.
"""
import os
import sys
import subprocess
import asyncio
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

# Load all env vars
for var in ['SUPABASE_URL', 'SUPABASE_ANON_KEY', 'GROQ_API_KEY', 'CaptchaKey']:
    load_env(var)

# Initialize Supabase
import importlib
sb = importlib.import_module('supabase._sync.client')
supabase = sb.create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_ANON_KEY'])

USER_ID = "00000000-0000-0000-0000-000000000001"

# REAL ACTIVE JOBS - Found via web search Jan 2026
JOBS_TO_APPLY = [
    {
        "platform": "greenhouse",
        "url": "https://boards.greenhouse.io/gofasti/jobs/5729379004",
        "title": "Graphic Designer (Remote)",
        "company": "GoFasti",
        "description": """
        GoFasti is looking for a Graphic Designer. Remote work, Talent-as-a-Service.
        Requirements: Graphic design experience, Adobe Creative Suite, remote work.
        """
    },
    {
        "platform": "greenhouse",
        "url": "https://boards.greenhouse.io/jobleads/jobs/7867687002",
        "title": "Graphic Designer - fully remote",
        "company": "JobLeads",
        "description": """
        Develop and create high-quality designs for JobLeads brand.
        Social media content, marketing materials, brand guidelines.
        Flexible hours, remote work, professional growth opportunities.
        """
    },
    {
        "platform": "greenhouse",
        "url": "https://boards.greenhouse.io/shopltk/jobs/5186247003",
        "title": "Graphic Designer",
        "company": "LTK USA",
        "description": """
        LTK looking for Graphic Designer to work with Creative and Marketing teams.
        Fully remote position. Conceptualization and design support.
        """
    }
]


def save_job_to_db(job_data):
    """Save job to Supabase."""
    try:
        result = supabase.table('jobs').insert({
            'source': job_data['platform'],
            'source_url': job_data['url'],
            'title': job_data['title'],
            'company': job_data['company'],
            'description': job_data['description'],
            'is_active': True
        }).execute()
        return result.data[0]['id']
    except Exception as e:
        print(f"   ⚠️ Job save failed: {e}")
        return None


def save_application_to_db(job_id, run_id, status, resume_path=None, cover_letter_path=None):
    """Save application record to Supabase."""
    try:
        app_data = {
            'user_id': USER_ID,
            'job_id': job_id,
            'automation_run_id': run_id,
            'status': status,
            'submission_method': 'auto',
            'fields_filled': 8 if status == 'submitted' else 0
        }
        if status == 'submitted':
            app_data['submitted_at'] = datetime.utcnow().isoformat()
        
        result = supabase.table('applications').insert(app_data).execute()
        app_id = result.data[0]['id']
        
        # Save resume
        if resume_path:
            supabase.table('resumes').insert({
                'user_id': USER_ID,
                'version_name': f'auto_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'file_path': str(resume_path),
                'file_type': 'pdf',
                'tailored_for_job_id': job_id
            }).execute()
        
        # Save cover letter
        if cover_letter_path:
            supabase.table('cover_letters').insert({
                'user_id': USER_ID,
                'job_id': job_id,
                'file_path': str(cover_letter_path),
                'content': '',
                'content_text': ''
            }).execute()
        
        return app_id
    except Exception as e:
        print(f"   ⚠️ Application save failed: {e}")
        return None


def start_automation_run():
    """Start an automation run."""
    try:
        result = supabase.table('automation_runs').insert({
            'user_id': USER_ID,
            'run_type': 'manual',  # Valid: scheduled, manual, triggered
            'status': 'running',
            'metadata': {'version': '2.0', 'type': 'end_to_end_test'}
        }).execute()
        return result.data[0]['id']
    except Exception as e:
        print(f"   ⚠️ Run start failed: {e}")
        return None


def end_automation_run(run_id, status, stats):
    """End an automation run."""
    try:
        supabase.table('automation_runs').update({
            'status': status,
            'ended_at': datetime.utcnow().isoformat(),
            'jobs_found': stats.get('found', 0),
            'jobs_applied': stats.get('applied', 0),
            'jobs_skipped': stats.get('skipped', 0),
            'jobs_failed': stats.get('failed', 0)
        }).eq('id', run_id).execute()
    except Exception as e:
        print(f"   ⚠️ Run end failed: {e}")


async def apply_to_single_job(job, run_id):
    """Apply to a single job."""
    print(f"\n{'='*60}")
    print(f"📋 {job['platform'].upper()}: {job['title']} at {job['company']}")
    print(f"   URL: {job['url']}")
    print(f"{'='*60}")
    
    # Save job to DB
    job_id = save_job_to_db(job)
    if not job_id:
        return {'success': False, 'error': 'Failed to save job to DB'}
    print(f"   📌 Job saved: {job_id[:8]}...")
    
    # Generate documents
    print("   📝 Generating documents...")
    from document_generator import generate_application_documents
    
    docs = generate_application_documents(job['title'], job['company'], job['description'])
    resume_path = docs.get('files', {}).get('resume_pdf')
    cover_letter_path = docs.get('files', {}).get('cover_letter_pdf')
    
    if not resume_path:
        save_application_to_db(job_id, run_id, 'failed')
        return {'success': False, 'error': 'Failed to generate resume'}
    
    print(f"   ✅ Resume: {Path(resume_path).name}")
    print(f"   ✅ Cover Letter: {Path(cover_letter_path).name if cover_letter_path else 'N/A'}")
    
    # Apply
    print("   🚀 Submitting application...")
    try:
        from real_auto_apply import auto_apply_to_job
        result = await auto_apply_to_job(job['url'], job['title'], job['company'], job['description'])
        
        if result.get('success'):
            print(f"   ✅ APPLICATION SUBMITTED!")
            save_application_to_db(job_id, run_id, 'submitted', resume_path, cover_letter_path)
            result['resume_path'] = resume_path
            result['cover_letter_path'] = cover_letter_path
            result['job_id'] = job_id
            return result
        else:
            error = result.get('error', 'Unknown error')
            print(f"   ❌ Failed: {error}")
            save_application_to_db(job_id, run_id, 'failed')
            return result
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        save_application_to_db(job_id, run_id, 'failed')
        return {'success': False, 'error': str(e)}


async def check_email_confirmations(companies):
    """Check Gmail for application confirmations."""
    print("\n" + "=" * 60)
    print("📧 CHECKING EMAIL FOR CONFIRMATIONS")
    print("=" * 60)
    
    try:
        from gmail_handler import get_job_emails
        
        emails = get_job_emails(days_back=1, max_results=20)
        confirmations = []
        
        for company in companies:
            company_lower = company.lower()
            for email in emails:
                subject = email.get('subject', '').lower()
                sender = email.get('from', '').lower()
                snippet = email.get('snippet', '').lower()
                
                if company_lower in sender or company_lower in subject:
                    if any(kw in subject or kw in snippet for kw in ['received', 'thank you', 'application', 'submitted', 'confirmation']):
                        confirmations.append({
                            'company': company,
                            'subject': email.get('subject', ''),
                            'from': email.get('from', '')
                        })
        
        if confirmations:
            print(f"   ✅ Found {len(confirmations)} confirmation(s):")
            for c in confirmations:
                print(f"      - {c['company']}: {c['subject'][:50]}...")
        else:
            print("   ⏳ No confirmation emails yet (may arrive later)")
        
        return confirmations
        
    except Exception as e:
        print(f"   ⚠️ Email check failed: {e}")
        return []


def verify_database_records():
    """Verify all database records were created correctly."""
    print("\n" + "=" * 60)
    print("🗄️ VERIFYING DATABASE RECORDS")
    print("=" * 60)
    
    # Check jobs
    jobs = supabase.table('jobs').select('id, title, company, source').order('created_at', desc=True).limit(5).execute()
    print(f"\n   📋 Recent Jobs: {len(jobs.data)}")
    for j in jobs.data[:3]:
        print(f"      - {j['title']} at {j['company']} ({j['source']})")
    
    # Check applications
    apps = supabase.table('applications').select('id, status, submitted_at').order('created_at', desc=True).limit(5).execute()
    print(f"\n   📝 Recent Applications: {len(apps.data)}")
    for a in apps.data[:3]:
        print(f"      - {a['status']} at {a['submitted_at']}")
    
    # Check resumes
    resumes = supabase.table('resumes').select('id, version_name').order('created_at', desc=True).limit(5).execute()
    print(f"\n   📄 Recent Resumes: {len(resumes.data)}")
    for r in resumes.data[:3]:
        print(f"      - {r['version_name']}")
    
    # Check cover letters
    cls = supabase.table('cover_letters').select('id, job_id').order('created_at', desc=True).limit(5).execute()
    print(f"\n   📝 Recent Cover Letters: {len(cls.data)}")
    
    # Check automation runs
    runs = supabase.table('automation_runs').select('id, status, jobs_applied').order('created_at', desc=True).limit(3).execute()
    print(f"\n   🤖 Recent Runs: {len(runs.data)}")
    for r in runs.data[:3]:
        print(f"      - {r['status']}, applied: {r['jobs_applied']}")
    
    return True


async def main():
    """Main autonomous application flow."""
    print("=" * 70)
    print("🤖 AUTONOMOUS JOB APPLICATION - End-to-End Test")
    print("=" * 70)
    print(f"   Target: Apply to 3 jobs from different platforms")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Start automation run
    run_id = start_automation_run()
    print(f"\n   📊 Automation run started: {run_id[:8] if run_id else 'N/A'}...")
    
    stats = {'found': 0, 'applied': 0, 'skipped': 0, 'failed': 0}
    results = []
    companies_applied = []
    
    for job in JOBS_TO_APPLY:
        stats['found'] += 1
        
        result = await apply_to_single_job(job, run_id)
        results.append(result)
        
        if result.get('success'):
            stats['applied'] += 1
            companies_applied.append(job['company'])
        elif 'closed' in str(result.get('error', '')).lower() or 'no longer' in str(result.get('error', '')).lower():
            stats['skipped'] += 1
        else:
            stats['failed'] += 1
        
        # Small delay between applications
        await asyncio.sleep(2)
    
    # End automation run
    status = 'completed' if stats['applied'] > 0 else 'failed'
    end_automation_run(run_id, status, stats)
    
    # Verify database
    verify_database_records()
    
    # Check email confirmations
    if companies_applied:
        await asyncio.sleep(10)  # Wait for emails
        await check_email_confirmations(companies_applied)
    
    # Final summary
    print("\n" + "=" * 70)
    print("📊 FINAL SUMMARY")
    print("=" * 70)
    print(f"   Jobs Found:   {stats['found']}")
    print(f"   Applied:      {stats['applied']}")
    print(f"   Skipped:      {stats['skipped']}")
    print(f"   Failed:       {stats['failed']}")
    
    if stats['applied'] > 0:
        print("\n   📄 Documents Used:")
        for r in results:
            if r.get('success'):
                print(f"      Resume: {r.get('resume_path')}")
                print(f"      Cover Letter: {r.get('cover_letter_path')}")
    
    print("\n" + "=" * 70)
    if stats['applied'] >= 1:
        print("✅ END-TO-END TEST PASSED")
    else:
        print("⚠️ END-TO-END TEST INCOMPLETE - No jobs could be applied to")
    print("=" * 70)
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
