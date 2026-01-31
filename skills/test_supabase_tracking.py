#!/usr/bin/env python3
"""Quick test of Supabase tracking functions."""
import os
import subprocess
from datetime import datetime

def load_env(var_name):
    result = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         f'[Environment]::GetEnvironmentVariable("{var_name}", "User")'],
        capture_output=True, text=True, timeout=5
    )
    val = result.stdout.strip()
    if val and val != 'None':
        os.environ[var_name] = val
    return val

# Load env vars
load_env('SUPABASE_URL')
load_env('SUPABASE_ANON_KEY')

import importlib
sb = importlib.import_module('supabase._sync.client')
client = sb.create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_ANON_KEY'])

USER_ID = "00000000-0000-0000-0000-000000000001"

print("=" * 60)
print("TESTING SUPABASE TRACKING")
print("=" * 60)

# Test 1: Insert a job
print("\n1. Testing job insert...")
test_job = {
    'source': 'greenhouse',
    'source_url': f'https://test.example.com/job/test-{datetime.now().timestamp()}',
    'title': 'Test Graphic Designer',
    'company': 'Test Company',
    'location': 'Remote',
    'is_active': True
}
result = client.table('jobs').insert(test_job).execute()
job_id = result.data[0]['id']
print(f"   ✅ Job inserted: {job_id[:8]}...")

# Test 2: Start automation run
print("\n2. Testing automation run...")
result = client.table('automation_runs').insert({
    'user_id': USER_ID,
    'run_type': 'test',
    'status': 'running'
}).execute()
run_id = result.data[0]['id']
print(f"   ✅ Run started: {run_id[:8]}...")

# Test 3: Create application
print("\n3. Testing application creation...")
result = client.table('applications').insert({
    'user_id': USER_ID,
    'job_id': job_id,
    'automation_run_id': run_id,
    'status': 'submitted',
    'submission_method': 'auto',
    'fields_filled': 8,
    'submitted_at': datetime.utcnow().isoformat()
}).execute()
app_id = result.data[0]['id']
print(f"   ✅ Application created: {app_id[:8]}...")

# Test 4: End run
print("\n4. Ending automation run...")
client.table('automation_runs').update({
    'status': 'completed',
    'ended_at': datetime.utcnow().isoformat(),
    'jobs_found': 1,
    'jobs_applied': 1
}).eq('id', run_id).execute()
print(f"   ✅ Run completed")

# Verify data
print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)

jobs = client.table('jobs').select('id, title, company').order('created_at', desc=True).limit(3).execute()
print(f"\n📋 Jobs: {len(jobs.data)}")
for j in jobs.data:
    print(f"   - {j['title']} at {j['company']}")

apps = client.table('applications').select('id, status, submitted_at').order('created_at', desc=True).limit(3).execute()
print(f"\n📝 Applications: {len(apps.data)}")
for a in apps.data:
    print(f"   - {a['status']} at {a['submitted_at']}")

runs = client.table('automation_runs').select('id, status, jobs_applied').order('created_at', desc=True).limit(3).execute()
print(f"\n🤖 Runs: {len(runs.data)}")
for r in runs.data:
    print(f"   - {r['status']}, applied: {r['jobs_applied']}")

print("\n" + "=" * 60)
print("✅ ALL SUPABASE TRACKING TESTS PASSED!")
print("=" * 60)
