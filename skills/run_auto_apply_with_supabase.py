#!/usr/bin/env python3
"""
Auto-Apply with Supabase Tracking
==================================
Runs the full auto-apply flow with complete Supabase backend tracking.
"""
import os
import sys
import subprocess
import asyncio
from datetime import datetime
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_env_var(var_name):
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
    except Exception:
        pass
    return None

# Load all required environment variables
print("=" * 70)
print("🤖 CLAWDBOT AUTO-APPLY WITH SUPABASE TRACKING")
print("=" * 70)

print("\n📋 Loading environment variables...")
env_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY', 'OpenRouterKey', 'CaptchaKey']
for var in env_vars:
    val = load_env_var(var)
    if val:
        print(f"   ✅ {var}: {'*' * 10}...")
    else:
        print(f"   ⚠️ {var}: Not set")

# Initialize Supabase client
print("\n📋 Initializing Supabase...")
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_ANON_KEY')

if SUPABASE_URL and SUPABASE_KEY:
    try:
        # Use importlib to avoid conflict with local supabase folder
        import importlib
        supabase_module = importlib.import_module('supabase._sync.client')
        create_client = supabase_module.create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("   ✅ Supabase client ready")
        SUPABASE_ENABLED = True
    except Exception as e:
        print(f"   ⚠️ Supabase init failed: {e}")
        SUPABASE_ENABLED = False
else:
    SUPABASE_ENABLED = False
    print("   ⚠️ Supabase not configured")

# Default user ID
USER_ID = "00000000-0000-0000-0000-000000000001"

# Global Supabase client (lazy initialized)
supabase = None

# Jobs to try - Use active Greenhouse/Lever jobs
JOBS_TO_TRY = [
    {
        "url": "https://boards.greenhouse.io/embed/job_app?for=gofasti&token=5709006004",
        "title": "Graphic Designer (Remote)",
        "company": "GoFasti",
        "source": "greenhouse"
    }
]

def get_supabase():
    """Get Supabase client (lazy initialization)."""
    global supabase, SUPABASE_ENABLED
    if supabase is None:
        url = os.environ.get('SUPABASE_URL')
        key = os.environ.get('SUPABASE_ANON_KEY')
        if url and key:
            try:
                # Try different import paths
                try:
                    import importlib
                    sb = importlib.import_module('supabase._sync.client')
                    supabase = sb.create_client(url, key)
                except:
                    # Fallback: direct import from supabase package
                    import sys
                    # Temporarily remove local supabase from path
                    original_path = sys.path.copy()
                    sys.path = [p for p in sys.path if 'job-assistant' not in p]
                    try:
                        from supabase import create_client
                        supabase = create_client(url, key)
                    finally:
                        sys.path = original_path
                SUPABASE_ENABLED = True
                print(f"   ✅ Supabase client ready (lazy init)")
            except Exception as e:
                print(f"   ⚠️ Supabase lazy init failed: {e}")
                SUPABASE_ENABLED = False
    return supabase

def save_job_to_supabase(job_data):
    """Save job to Supabase and return job_id."""
    client = get_supabase()
    if not client:
        print("   ⚠️ Supabase not available")
        return None
    
    try:
        # Check if job already exists
        result = client.table('jobs')\
            .select('id')\
            .eq('source_url', job_data['url'])\
            .execute()
        
        if result.data:
            job_id = result.data[0]['id']
            # Update last_seen_at
            client.table('jobs').update({
                'last_seen_at': datetime.utcnow().isoformat()
            }).eq('id', job_id).execute()
            print(f"   📌 Job exists in Supabase: {job_id[:8]}...")
            return job_id
        
        # Insert new job
        insert_data = {
            'source': job_data.get('source', 'greenhouse'),
            'source_url': job_data['url'],
            'title': job_data['title'],
            'company': job_data['company'],
            'location': job_data.get('location', 'Remote'),
            'is_active': True
        }
        
        result = client.table('jobs').insert(insert_data).execute()
        job_id = result.data[0]['id']
        print(f"   📌 Job saved to Supabase: {job_id[:8]}...")
        return job_id
    except Exception as e:
        print(f"   ⚠️ Failed to save job: {e}")
        return None

def start_automation_run():
    """Start an automation run in Supabase."""
    client = get_supabase()
    if not client:
        return None
    
    try:
        result = client.table('automation_runs').insert({
            'user_id': USER_ID,
            'run_type': 'manual',
            'status': 'running',
            'metadata': {'version': '1.0.0', 'timestamp': datetime.utcnow().isoformat()}
        }).execute()
        
        run_id = result.data[0]['id']
        print(f"   📊 Automation run started: {run_id[:8]}...")
        return run_id
    except Exception as e:
        print(f"   ⚠️ Failed to start run: {e}")
        return None

def end_automation_run(run_id, status, stats):
    """End an automation run in Supabase."""
    client = get_supabase()
    if not client or not run_id:
        return
    
    try:
        client.table('automation_runs').update({
            'status': status,
            'ended_at': datetime.utcnow().isoformat(),
            'jobs_found': stats.get('found', 0),
            'jobs_applied': stats.get('applied', 0),
            'jobs_skipped': stats.get('skipped', 0),
            'jobs_failed': stats.get('failed', 0)
        }).eq('id', run_id).execute()
        print(f"   📊 Automation run ended: {status}")
    except Exception as e:
        print(f"   ⚠️ Failed to end run: {e}")

def create_application_record(job_id, run_id, resume_id=None):
    """Create an application record in Supabase."""
    client = get_supabase()
    if not client:
        return None
    
    try:
        # Check for duplicate
        existing = client.table('applications')\
            .select('id')\
            .eq('user_id', USER_ID)\
            .eq('job_id', job_id)\
            .not_.in_('status', ['failed', 'withdrawn'])\
            .execute()
        
        if existing.data:
            print(f"   ⚠️ Already applied to this job")
            return None
        
        result = client.table('applications').insert({
            'user_id': USER_ID,
            'job_id': job_id,
            'automation_run_id': run_id,
            'resume_id': resume_id,
            'status': 'in_progress',
            'submission_method': 'auto'
        }).execute()
        
        app_id = result.data[0]['id']
        print(f"   📝 Application record created: {app_id[:8]}...")
        return app_id
    except Exception as e:
        print(f"   ⚠️ Failed to create application: {e}")
        return None

def update_application_status(app_id, status, fields_filled=0, error=None):
    """Update application status in Supabase."""
    client = get_supabase()
    if not client or not app_id:
        return
    
    try:
        update_data = {
            'status': status,
            'fields_filled': fields_filled
        }
        
        if status == 'submitted':
            update_data['submitted_at'] = datetime.utcnow().isoformat()
        
        if error:
            update_data['last_error'] = error
        
        client.table('applications').update(update_data).eq('id', app_id).execute()
    except Exception as e:
        print(f"   ⚠️ Failed to update application: {e}")

def save_resume_to_supabase(file_path, job_id):
    """Save resume record to Supabase."""
    client = get_supabase()
    if not client:
        return None
    
    try:
        result = client.table('resumes').insert({
            'user_id': USER_ID,
            'version_name': f'tailored_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'file_path': str(file_path),
            'file_type': 'pdf',
            'tailored_for_job_id': job_id
        }).execute()
        
        resume_id = result.data[0]['id']
        print(f"   📄 Resume saved to DB: {resume_id[:8]}...")
        return resume_id
    except Exception as e:
        print(f"   ⚠️ Failed to save resume: {e}")
        return None

def save_cover_letter_to_supabase(file_path, job_id, content=None):
    """Save cover letter record to Supabase."""
    client = get_supabase()
    if not client:
        return None
    
    try:
        result = client.table('cover_letters').insert({
            'user_id': USER_ID,
            'job_id': job_id,
            'file_path': str(file_path),
            'content': content or ''
        }).execute()
        
        cl_id = result.data[0]['id']
        print(f"   📝 Cover letter saved to DB: {cl_id[:8]}...")
        return cl_id
    except Exception as e:
        print(f"   ⚠️ Failed to save cover letter: {e}")
        return None

async def run_auto_apply():
    """Run the full auto-apply flow with Supabase tracking."""
    
    # Import the auto-apply function
    try:
        from real_auto_apply import auto_apply_to_job
    except ImportError as e:
        print(f"❌ Failed to import auto_apply_to_job: {e}")
        return
    
    stats = {'found': 0, 'applied': 0, 'skipped': 0, 'failed': 0}
    
    # Start automation run
    run_id = start_automation_run()
    
    print("\n" + "=" * 70)
    print("🚀 STARTING AUTO-APPLY")
    print("=" * 70)
    
    for job in JOBS_TO_TRY:
        stats['found'] += 1
        
        print(f"\n{'='*70}")
        print(f"📋 JOB: {job['title']} at {job['company']}")
        print(f"   URL: {job['url']}")
        print(f"{'='*70}")
        
        # Save job to Supabase
        job_id = save_job_to_supabase(job)
        
        # Check if already applied
        if SUPABASE_ENABLED and job_id:
            existing = supabase.table('applications')\
                .select('id, status')\
                .eq('user_id', USER_ID)\
                .eq('job_id', job_id)\
                .not_.in_('status', ['failed', 'withdrawn'])\
                .execute()
            
            if existing.data:
                print(f"   ⏭️ Skipping - already applied (status: {existing.data[0]['status']})")
                stats['skipped'] += 1
                continue
        
        # Create application record
        app_id = create_application_record(job_id, run_id)
        
        # Run the auto-apply
        try:
            # Pass empty description - the function will scrape it from the page
            job_description = job.get('description', '')
            result = await auto_apply_to_job(job['url'], job['title'], job['company'], job_description)
            
            if result.get('success'):
                print(f"\n✅ APPLICATION SUBMITTED SUCCESSFULLY!")
                update_application_status(app_id, 'submitted', 
                    fields_filled=result.get('fields_filled', 0))
                stats['applied'] += 1
                
                # Save resume and cover letter to database
                if result.get('resume_path'):
                    save_resume_to_supabase(result['resume_path'], job_id)
                if result.get('cover_letter_path'):
                    save_cover_letter_to_supabase(result['cover_letter_path'], job_id)
                
                # We got one successful application - stop here
                print("\n🎉 Successfully applied to 1 job!")
                break
            else:
                error = result.get('error', 'Unknown error')
                print(f"\n❌ Application failed: {error}")
                update_application_status(app_id, 'failed', error=error)
                stats['failed'] += 1
                
        except Exception as e:
            print(f"\n❌ Exception during application: {e}")
            update_application_status(app_id, 'failed', error=str(e))
            stats['failed'] += 1
    
    # End automation run
    status = 'completed' if stats['applied'] > 0 else 'failed'
    end_automation_run(run_id, status, stats)
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 FINAL SUMMARY")
    print("=" * 70)
    print(f"   Jobs found:   {stats['found']}")
    print(f"   Applied:      {stats['applied']}")
    print(f"   Skipped:      {stats['skipped']}")
    print(f"   Failed:       {stats['failed']}")
    
    if SUPABASE_ENABLED:
        print(f"\n   📊 View in Supabase: {SUPABASE_URL}/project/default/editor")

if __name__ == "__main__":
    asyncio.run(run_auto_apply())
