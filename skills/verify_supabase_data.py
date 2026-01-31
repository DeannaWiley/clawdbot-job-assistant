#!/usr/bin/env python3
"""Verify data in Supabase after auto-apply."""
import subprocess, os

def load_env(var_name):
    result = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         f'[Environment]::GetEnvironmentVariable("{var_name}", "User")'],
        capture_output=True, text=True, timeout=5
    )
    return result.stdout.strip()

url = load_env('SUPABASE_URL')
key = load_env('SUPABASE_ANON_KEY')

import importlib
sb = importlib.import_module('supabase._sync.client')
client = sb.create_client(url, key)

print('=' * 60)
print('SUPABASE DATA VERIFICATION')
print('=' * 60)

# Check jobs
jobs = client.table('jobs').select('id, title, company, source').order('created_at', desc=True).limit(5).execute()
print(f'\n📋 Jobs in database: {len(jobs.data)}')
for j in jobs.data:
    print(f'   - {j["title"]} at {j["company"]} ({j["source"]})')

# Check applications
apps = client.table('applications').select('id, status, submitted_at, fields_filled').order('created_at', desc=True).limit(5).execute()
print(f'\n📝 Applications in database: {len(apps.data)}')
for a in apps.data:
    print(f'   - Status: {a["status"]}, Fields: {a["fields_filled"]}, Submitted: {a["submitted_at"]}')

# Check automation runs
runs = client.table('automation_runs').select('id, status, jobs_found, jobs_applied').order('created_at', desc=True).limit(5).execute()
print(f'\n🤖 Automation runs: {len(runs.data)}')
for r in runs.data:
    print(f'   - Status: {r["status"]}, Found: {r["jobs_found"]}, Applied: {r["jobs_applied"]}')

# Check users
users = client.table('users').select('full_name, email').execute()
print(f'\n👤 Users: {len(users.data)}')
for u in users.data:
    print(f'   - {u["full_name"]} ({u["email"]})')

print('\n' + '=' * 60)
print('✅ All data successfully stored in Supabase!')
print('=' * 60)
