#!/usr/bin/env python3
"""
Test Supabase Connection
Verifies the database is set up correctly and operations work.
"""
import os
import sys
import subprocess
from datetime import datetime

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

# Load environment variables
SUPABASE_URL = load_env_var('SUPABASE_URL')
SUPABASE_ANON_KEY = load_env_var('SUPABASE_ANON_KEY')

print("=" * 70)
print("🔌 SUPABASE CONNECTION TEST")
print("=" * 70)

# Test 1: Check environment variables
print("\n📋 Test 1: Environment Variables")
print("-" * 50)

if SUPABASE_URL:
    print(f"  ✅ SUPABASE_URL: {SUPABASE_URL[:40]}...")
else:
    print("  ❌ SUPABASE_URL not set")
    sys.exit(1)

if SUPABASE_ANON_KEY:
    print(f"  ✅ SUPABASE_ANON_KEY: {SUPABASE_ANON_KEY[:30]}...")
else:
    print("  ❌ SUPABASE_ANON_KEY not set")
    sys.exit(1)

# Test 2: Import and create client
print("\n📋 Test 2: Supabase Client")
print("-" * 50)

try:
    from supabase import create_client
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    print("  ✅ Supabase client created successfully")
except ImportError as e:
    print(f"  ❌ Import error: {e}")
    print("     Run: pip install supabase")
    sys.exit(1)
except Exception as e:
    print(f"  ❌ Client creation failed: {e}")
    sys.exit(1)

# Test 3: Query users table
print("\n📋 Test 3: Database Query (users table)")
print("-" * 50)

try:
    result = client.table('users').select('*').limit(5).execute()
    print(f"  ✅ Query successful - Found {len(result.data)} user(s)")
    for user in result.data:
        print(f"     - {user.get('full_name', 'Unknown')} ({user.get('email', 'no email')})")
except Exception as e:
    print(f"  ❌ Query failed: {e}")
    print("     Make sure you ran the SQL migration in Supabase")

# Test 4: Query jobs table
print("\n📋 Test 4: Database Query (jobs table)")
print("-" * 50)

try:
    result = client.table('jobs').select('id, title, company').limit(5).execute()
    print(f"  ✅ Query successful - Found {len(result.data)} job(s)")
    for job in result.data:
        print(f"     - {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
except Exception as e:
    print(f"  ❌ Query failed: {e}")

# Test 5: Insert test job
print("\n📋 Test 5: Insert Test Job")
print("-" * 50)

try:
    test_job = {
        'source': 'other',
        'source_url': f'https://test.example.com/job/{datetime.now().timestamp()}',
        'title': 'Test Position',
        'company': 'Test Company',
        'location': 'Remote',
        'is_active': True
    }
    
    result = client.table('jobs').insert(test_job).execute()
    if result.data:
        job_id = result.data[0]['id']
        print(f"  ✅ Insert successful - Job ID: {job_id[:8]}...")
        
        # Clean up - delete test job
        client.table('jobs').delete().eq('id', job_id).execute()
        print(f"  ✅ Cleanup successful - Test job deleted")
    else:
        print(f"  ⚠️ Insert returned no data")
except Exception as e:
    print(f"  ❌ Insert failed: {e}")

# Test 6: Query analytics views
print("\n📋 Test 6: Analytics Views")
print("-" * 50)

views = ['daily_application_stats', 'weekly_summary', 'captcha_performance', 'job_source_stats']
for view in views:
    try:
        result = client.table(view).select('*').limit(1).execute()
        print(f"  ✅ {view}: accessible")
    except Exception as e:
        print(f"  ⚠️ {view}: {str(e)[:50]}")

print("\n" + "=" * 70)
print("📊 SUPABASE CONNECTION TEST COMPLETE")
print("=" * 70)
print("""
If all tests passed, Supabase is fully configured!

Next steps:
1. Run ClawdBot auto-apply with Supabase tracking
2. Check Supabase dashboard for data

Dashboard: """ + SUPABASE_URL.replace('.supabase.co', '.supabase.co/project/default/editor'))
