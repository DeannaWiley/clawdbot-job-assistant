"""
COMPREHENSIVE VERIFICATION SCRIPT
Tests ALL components to ensure 100% Clawdbot integration readiness.
"""
import os
import sys
import traceback

sys.path.insert(0, 'skills')
sys.path.insert(0, r'C:\Users\deann\clawd\skills\job-search-automation')

def check(name, test_func):
    """Run a test and report result"""
    try:
        result = test_func()
        print(f"  ✅ {name}")
        return True, result
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        traceback.print_exc()
        return False, str(e)

def run_all_tests():
    print("=" * 60)
    print("COMPREHENSIVE CLAWDBOT INTEGRATION VERIFICATION")
    print("=" * 60)
    
    errors = []
    
    # 1. MODULE IMPORTS
    print("\n📦 1. MODULE IMPORTS")
    print("-" * 40)
    
    modules_to_test = [
        ('job_search', 'search_all_jobs'),
        ('filter_jobs', 'filter_jobs'),
        ('tailor_resume', 'tailor_resume'),
        ('write_cover_letter', 'write_cover_letter'),
        ('slack_notify', 'send_job_summary'),
        ('apply_job', 'apply_to_job'),
        ('track_status', 'log_application'),
        ('job_boards', 'search_all_extended_boards'),
        ('review_content', 'review_generated_content'),
        ('gmail_handler', 'get_email_summary'),
        ('gmail_handler', 'search_emails'),
        ('gmail_handler', 'reply_to_email'),
        ('slack_dashboard', 'send_dashboard'),
        ('interview_scheduler', 'generate_available_slots'),
        ('job_history', 'filter_new_jobs'),
        ('morning_rollup', 'send_morning_rollup'),
    ]
    
    for module_name, func_name in modules_to_test:
        def test_import(m=module_name, f=func_name):
            module = __import__(m)
            func = getattr(module, f)
            return func
        passed, _ = check(f"{module_name}.{func_name}", test_import)
        if not passed:
            errors.append(f"Import: {module_name}.{func_name}")
    
    # 2. CLAWDBOT BRIDGE MODULES
    print("\n🌉 2. CLAWDBOT BRIDGE MODULES")
    print("-" * 40)
    
    def test_integrations():
        from integrations import SlackNotifier, GmailMonitor, ResumeTailor
        return True
    passed, _ = check("integrations module", test_integrations)
    if not passed:
        errors.append("Clawdbot bridge: integrations")
    
    def test_scripts():
        from scripts import JobScanner, ApplicationProcessor
        return True
    passed, _ = check("scripts module", test_scripts)
    if not passed:
        errors.append("Clawdbot bridge: scripts")
    
    # 3. DATA FILES
    print("\n📁 3. DATA FILES")
    print("-" * 40)
    
    data_files = [
        ('data/base_resume.txt', 'Base resume'),
        ('data/all_resumes.txt', 'All resumes'),
        ('data/gmail_token.pickle', 'Gmail OAuth token'),
        ('config.yaml', 'Configuration'),
        ('data/job_history.json', 'Job history'),
    ]
    
    for path, name in data_files:
        def test_file(p=path):
            full_path = os.path.join(r'C:\Users\deann\clawd\job-assistant', p)
            if os.path.exists(full_path):
                size = os.path.getsize(full_path)
                return f"{size} bytes"
            raise FileNotFoundError(f"Missing: {full_path}")
        passed, _ = check(f"{name} ({path})", test_file)
        if not passed:
            errors.append(f"Data file: {name}")
    
    # 4. ENVIRONMENT VARIABLES
    print("\n🔑 4. ENVIRONMENT VARIABLES")
    print("-" * 40)
    
    import subprocess
    env_vars = [
        'SLACK_BOT_TOKEN',
        'SLACK_APP_TOKEN', 
        'OPENROUTER_API_KEY',
        'GMAIL_CLIENT_ID',
        'GMAIL_CLIENT_SECRET',
    ]
    
    for var in env_vars:
        def test_env(v=var):
            value = os.environ.get(v)
            if not value:
                result = subprocess.run(
                    ['powershell', '-Command', f'[Environment]::GetEnvironmentVariable("{v}", "User")'],
                    capture_output=True, text=True
                )
                value = result.stdout.strip()
            if value:
                return f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "SET"
            raise ValueError(f"Not set")
        passed, _ = check(var, test_env)
        if not passed:
            errors.append(f"Env var: {var}")
    
    # 5. SLACK CONNECTION
    print("\n💬 5. SLACK CONNECTION")
    print("-" * 40)
    
    def test_slack():
        from slack_notify import get_slack_client
        client = get_slack_client()
        # Test auth
        auth = client.auth_test()
        return f"Connected as {auth['user']}"
    passed, result = check("Slack API connection", test_slack)
    if passed:
        print(f"      {result}")
    else:
        errors.append("Slack connection")
    
    # 6. GMAIL CONNECTION
    print("\n📧 6. GMAIL CONNECTION")
    print("-" * 40)
    
    def test_gmail():
        from gmail_handler import get_gmail_service
        service = get_gmail_service()
        if service:
            # Test connection
            profile = service.users().getProfile(userId='me').execute()
            return f"Connected as {profile['emailAddress']}"
        raise Exception("No service")
    passed, result = check("Gmail API connection", test_gmail)
    if passed:
        print(f"      {result}")
    else:
        errors.append("Gmail connection")
    
    # 7. CONFIG VALIDATION
    print("\n⚙️ 7. CONFIGURATION")
    print("-" * 40)
    
    def test_config():
        import yaml
        with open(r'C:\Users\deann\clawd\job-assistant\config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        required = ['user', 'search', 'filtering', 'llm', 'slack', 'preferences']
        missing = [k for k in required if k not in config]
        if missing:
            raise ValueError(f"Missing config sections: {missing}")
        return f"{len(config)} sections"
    passed, result = check("config.yaml structure", test_config)
    if passed:
        print(f"      {result}")
    else:
        errors.append("Configuration")
    
    # 8. JOB HISTORY
    print("\n📊 8. JOB HISTORY TRACKING")
    print("-" * 40)
    
    def test_history():
        from job_history import get_history_stats, filter_new_jobs, mark_job_seen
        stats = get_history_stats()
        return f"Seen: {stats['total_jobs_seen']}, Applied: {stats['total_applied']}"
    passed, result = check("Job history functions", test_history)
    if passed:
        print(f"      {result}")
    else:
        errors.append("Job history")
    
    # 9. FILTER LOGIC
    print("\n🔍 9. FILTER LOGIC")
    print("-" * 40)
    
    def test_filters():
        from filter_jobs import check_deal_breakers, check_scam_keywords
        
        # Test deal-breaker filter
        has_breaker, matched = check_deal_breakers(
            "Part-time Office Assistant",
            "Looking for part time help",
            ["Part time", "Internship"]
        )
        if not has_breaker:
            raise ValueError("Deal-breaker filter not working")
        
        # Test scam filter
        is_scam, kw = check_scam_keywords(
            "Wire transfer payment for training fee",
            ["wire transfer", "training fee"]
        )
        if not is_scam:
            raise ValueError("Scam filter not working")
        
        return "Filters working correctly"
    passed, _ = check("Deal-breaker and scam filters", test_filters)
    if not passed:
        errors.append("Filters")
    
    # 10. CLI COMMANDS
    print("\n🖥️ 10. CLI COMMANDS")
    print("-" * 40)
    
    def test_cli_status():
        import subprocess
        result = subprocess.run(
            ['python', 'cli.py', 'status'],
            cwd=r'C:\Users\deann\clawd\skills\job-search-automation',
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            raise Exception(result.stderr)
        return "CLI status works"
    passed, _ = check("cli.py status", test_cli_status)
    if not passed:
        errors.append("CLI status")
    
    def test_cli_emails():
        import subprocess
        result = subprocess.run(
            ['python', 'cli.py', 'emails'],
            cwd=r'C:\Users\deann\clawd\skills\job-search-automation',
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            raise Exception(result.stderr)
        return "CLI emails works"
    passed, _ = check("cli.py emails", test_cli_emails)
    if not passed:
        errors.append("CLI emails")
    
    # 11. SCHEDULED TASKS
    print("\n⏰ 11. SCHEDULED TASKS")
    print("-" * 40)
    
    def test_tasks():
        import subprocess
        result = subprocess.run(
            ['powershell', '-Command', 'Get-ScheduledTask | Where-Object {$_.TaskName -like "*JobAssistant*"} | Select-Object TaskName, State'],
            capture_output=True, text=True
        )
        if 'JobAssistant' not in result.stdout:
            raise ValueError("No JobAssistant tasks found")
        return result.stdout.strip()
    passed, result = check("Windows Task Scheduler", test_tasks)
    if passed:
        for line in result.split('\n')[2:]:
            if line.strip():
                print(f"      {line.strip()}")
    else:
        errors.append("Scheduled tasks")
    
    # SUMMARY
    print("\n" + "=" * 60)
    if errors:
        print(f"❌ VERIFICATION FAILED - {len(errors)} issues found:")
        for err in errors:
            print(f"   • {err}")
        print("=" * 60)
        return False
    else:
        print("✅ ALL TESTS PASSED - 100% READY FOR CLAWDBOT!")
        print("=" * 60)
        return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
