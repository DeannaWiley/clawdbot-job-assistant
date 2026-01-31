"""
Comprehensive verification script for Job Application Assistant
Run this to ensure everything is properly configured.
"""
import os
import sys

sys.path.insert(0, 'skills')

def check_mark(passed):
    return "✅" if passed else "❌"

def verify_all():
    print("=" * 60)
    print("JOB APPLICATION ASSISTANT - SETUP VERIFICATION")
    print("=" * 60)
    
    all_passed = True
    
    # 1. Check all modules import
    print("\n📦 MODULE IMPORTS")
    print("-" * 40)
    modules = [
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
        ('slack_dashboard', 'send_dashboard'),
        ('interview_scheduler', 'generate_available_slots'),
        ('job_history', 'filter_new_jobs'),
    ]
    
    for module_name, func_name in modules:
        try:
            module = __import__(module_name)
            func = getattr(module, func_name)
            print(f"  {check_mark(True)} {module_name}.{func_name}")
        except Exception as e:
            print(f"  {check_mark(False)} {module_name}: {e}")
            all_passed = False
    
    # 2. Check data files
    print("\n📁 DATA FILES")
    print("-" * 40)
    data_files = [
        ('data/base_resume.txt', 'Base resume'),
        ('data/all_resumes.txt', 'All resumes'),
        ('data/gmail_token.pickle', 'Gmail token'),
        ('config.yaml', 'Configuration'),
    ]
    
    for path, name in data_files:
        exists = os.path.exists(path)
        size = os.path.getsize(path) if exists else 0
        print(f"  {check_mark(exists)} {name}: {size} bytes" if exists else f"  {check_mark(False)} {name}: MISSING")
        if not exists and 'token' not in path:
            all_passed = False
    
    # 3. Check environment variables
    print("\n🔑 ENVIRONMENT VARIABLES")
    print("-" * 40)
    env_vars = [
        ('SLACK_BOT_TOKEN', 'Slack Bot Token'),
        ('SLACK_APP_TOKEN', 'Slack App Token'),
        ('OPENROUTER_API_KEY', 'OpenRouter API Key'),
        ('GMAIL_CLIENT_ID', 'Gmail Client ID'),
        ('GMAIL_CLIENT_SECRET', 'Gmail Client Secret'),
    ]
    
    for var, name in env_vars:
        # Check both current session and persistent
        value = os.environ.get(var)
        if not value:
            # Try to get from system
            import subprocess
            try:
                result = subprocess.run(
                    ['powershell', '-Command', f'[Environment]::GetEnvironmentVariable("{var}", "User")'],
                    capture_output=True, text=True
                )
                value = result.stdout.strip()
            except:
                pass
        
        exists = bool(value)
        masked = f"{value[:10]}...{value[-4:]}" if value and len(value) > 14 else "SET" if value else "NOT SET"
        print(f"  {check_mark(exists)} {name}: {masked}")
        if not exists:
            all_passed = False
    
    # 4. Check config.yaml settings
    print("\n⚙️ CONFIGURATION")
    print("-" * 40)
    try:
        import yaml
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        checks = [
            ('user.name', config.get('user', {}).get('name')),
            ('user.email', config.get('user', {}).get('email')),
            ('preferences.salary.minimum', config.get('preferences', {}).get('salary', {}).get('minimum')),
            ('preferences.locations', len(config.get('preferences', {}).get('locations', {}).get('preferred', []))),
            ('automation.daily_target', config.get('automation', {}).get('daily_target')),
        ]
        
        for key, value in checks:
            exists = value is not None and value != ''
            print(f"  {check_mark(exists)} {key}: {value}")
            
    except Exception as e:
        print(f"  {check_mark(False)} Config error: {e}")
        all_passed = False
    
    # 5. Check job history
    print("\n📊 JOB HISTORY")
    print("-" * 40)
    try:
        from job_history import get_history_stats
        stats = get_history_stats()
        print(f"  {check_mark(True)} Total seen: {stats['total_jobs_seen']}")
        print(f"  {check_mark(True)} Total applied: {stats['total_applied']}")
        print(f"  {check_mark(True)} Total skipped: {stats['total_skipped']}")
    except Exception as e:
        print(f"  {check_mark(False)} History error: {e}")
    
    # 6. Check Clawdbot skills directory
    print("\n🦞 CLAWDBOT SKILLS")
    print("-" * 40)
    skills_dir = os.path.expanduser("~/.clawdbot/skills") if os.name != 'nt' else os.path.join(os.environ.get('USERPROFILE', ''), '.clawdbot', 'skills')
    clawd_skills_dir = r"C:\Users\deann\clawd\skills"
    
    if os.path.exists(clawd_skills_dir):
        skills = os.listdir(clawd_skills_dir)
        print(f"  {check_mark(True)} Clawdbot skills installed: {len(skills)}")
        for skill in skills[:6]:
            print(f"      - {skill}")
    else:
        print(f"  {check_mark(False)} No Clawdbot skills found")
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL CHECKS PASSED - System ready!")
    else:
        print("⚠️ SOME CHECKS FAILED - Review issues above")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    verify_all()
