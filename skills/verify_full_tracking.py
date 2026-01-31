#!/usr/bin/env python3
"""Verify full database tracking including resumes and cover letters."""
import os
import subprocess

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

load_env('SUPABASE_URL')
load_env('SUPABASE_ANON_KEY')

import importlib
sb = importlib.import_module('supabase._sync.client')
client = sb.create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_ANON_KEY'])

print("=" * 60)
print("FULL SUPABASE TRACKING VERIFICATION")
print("=" * 60)

# Jobs
jobs = client.table('jobs').select('id, title, company, source').order('created_at', desc=True).limit(5).execute()
print(f"\n📋 Jobs: {len(jobs.data)}")
for j in jobs.data:
    print(f"   - {j['title']} at {j['company']} ({j['source']})")

# Applications
apps = client.table('applications').select('id, status, fields_filled, submitted_at').order('created_at', desc=True).limit(5).execute()
print(f"\n📝 Applications: {len(apps.data)}")
for a in apps.data:
    print(f"   - {a['status']}, fields: {a['fields_filled']}, submitted: {a['submitted_at']}")

# Resumes
resumes = client.table('resumes').select('id, version_name, file_path, file_type').order('created_at', desc=True).limit(5).execute()
print(f"\n📄 Resumes: {len(resumes.data)}")
for r in resumes.data:
    print(f"   - {r['version_name']} ({r['file_type']})")
    if r.get('file_path'):
        print(f"     Path: ...{r['file_path'][-50:]}")

# Cover Letters
cover_letters = client.table('cover_letters').select('id, job_id, content, file_path').order('created_at', desc=True).limit(5).execute()
print(f"\n📝 Cover Letters: {len(cover_letters.data)}")
for cl in cover_letters.data:
    content_preview = cl.get('content', '')[:80] if cl.get('content') else 'No content'
    print(f"   - Job: {cl['job_id'][:8]}...")
    print(f"     Content: {content_preview}...")
    if cl.get('file_path'):
        print(f"     Path: ...{cl['file_path'][-50:]}")

# Automation Runs
runs = client.table('automation_runs').select('id, status, jobs_found, jobs_applied').order('created_at', desc=True).limit(3).execute()
print(f"\n🤖 Automation Runs: {len(runs.data)}")
for r in runs.data:
    print(f"   - {r['status']}: found {r['jobs_found']}, applied {r['jobs_applied']}")

# Users
users = client.table('users').select('id, full_name, email').execute()
print(f"\n👤 Users: {len(users.data)}")
for u in users.data:
    print(f"   - {u['full_name']} ({u['email']})")

print("\n" + "=" * 60)
print("✅ FULL TRACKING VERIFICATION COMPLETE")
print("=" * 60)
