# 🔧 Environment Setup Guide

ClawdBot supports multiple methods for loading environment variables. Choose what works best for you.

## 📋 Required Environment Variables

### Minimum to Run ClawdBot
```bash
GROQ_API_KEY=your-groq-api-key
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
```

### Optional (for extended features)
```bash
# Alternative LLMs
OPENROUTER_API_KEY=your-openrouter-key
ANTHROPIC_API_KEY=your-anthropic-key

# Slack notifications
SLACK_BOT_TOKEN=xoxb-your-slack-token
SLACK_APP_TOKEN=xapp-your-slack-token

# Gmail confirmations
GMAIL_EMAIL=your-email@gmail.com
GMAIL_PASSWORD=your-app-password
GMAIL_CLIENT_ID=your-gmail-client-id
GMAIL_CLIENT_SECRET=your-gmail-client-secret

# CAPTCHA solving
CaptchaKey=your-2captcha-key
```

---

## 🚀 Setup Methods

### Method 1: .env File (Recommended)

1. **Copy the template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit .env with your values:**
   ```bash
   # Required
   GROQ_API_KEY=gsk_your_actual_key_here
   SUPABASE_URL=https://your_project.supabase.co
   SUPABASE_ANON_KEY=your_actual_anon_key_here
   
   # Optional as needed
   SLACK_BOT_TOKEN=xoxb_your_actual_token
   CaptchaKey=your_2captcha_key
   ```

3. **Install python-dotenv (if not already):**
   ```bash
   pip install python-dotenv
   ```

### Method 2: Windows Environment Variables

1. **Open Environment Variables:**
   - Press `Win + R`
   - Type `sysdm.cpl`
   - Go to "Advanced" tab
   - Click "Environment Variables"

2. **Add User Variables:**
   - Click "New..." under User variables
   - Add each required variable:
     - Variable name: `GROQ_API_KEY`
     - Variable value: `your_actual_key`

3. **Add these variables:**
   - `GROQ_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SLACK_BOT_TOKEN` (if using Slack)
   - `CaptchaKey` (if using auto-apply)

4. **Restart PowerShell/Command Prompt** to load new variables

### Method 3: PowerShell Profile

1. **Open PowerShell profile:**
   ```powershell
   notepad $PROFILE
   ```

2. **Add to profile:**
   ```powershell
   # Required
   $env:GROQ_API_KEY = "your_actual_key_here"
   $env:SUPABASE_URL = "https://your_project.supabase.co"
   $env:SUPABASE_ANON_KEY = "your_actual_anon_key_here"
   
   # Optional
   $env:SLACK_BOT_TOKEN = "xoxb_your_token"
   $env:CaptchaKey = "your_2captcha_key"
   ```

3. **Reload PowerShell:**
   ```powershell
   . $PROFILE
   ```

---

## 🔍 How ClawdBot Loads Environment

ClawdBot uses a custom `load_env()` function that:

1. **First checks** `os.environ` (current session)
2. **Then checks** Windows User Environment Variables
3. **Falls back to** `.env` file (if python-dotenv available)
4. **Raises error** if required keys missing

### Example from `job_queue_manager.py`:
```python
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
```

---

## 🧪 Test Your Setup

```bash
# Test database connection
python skills/test_supabase_connection.py

# Test job queue
python skills/job_queue_manager.py

# Test resume generation
python skills/test_resume_generation.py
```

If you get "API key not set" errors:
1. Check which method you used above
2. Verify variables are set correctly
3. Restart your terminal/PowerShell
4. Try the test commands again

---

## 🔑 Getting API Keys

| Service | URL | Cost |
|---------|-----|------|
| **Groq** (LLM) | https://console.groq.com/keys | FREE |
| **Supabase** (DB) | https://supabase.com/dashboard | FREE tier |
| **2Captcha** | https://2captcha.com/ | ~$2/1000 solves |
| **Slack** | https://api.slack.com/apps | FREE |
| **OpenRouter** | https://openrouter.ai/keys | Pay-as-you-go |

---

## 🚨 Common Issues

### "GROQ_API_KEY not set"
- Check if key is set in your chosen method
- Restart terminal after setting environment variables
- Verify key format (starts with `gsk_`)

### "Supabase connection failed"
- Verify SUPABASE_URL format (https://project.supabase.co)
- Check SUPABASE_ANON_KEY from Supabase dashboard
- Ensure project is active

### "Slack token invalid"
- Token should start with `xoxb-` (bot token)
- Ensure bot has required permissions
- Check token hasn't expired

---

## 📁 Environment File Locations

- **Project root**: `.env`
- **Windows User**: System Properties → Environment Variables
- **PowerShell**: `$PROFILE` (usually `Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`)

---

## 🔒 Security Best Practices

1. **Never commit** `.env` to git
2. **Use different keys** for dev/prod
3. **Rotate keys** periodically
4. **Use least privilege** (only needed permissions)
5. **Monitor usage** on API dashboards

---

**Need help?** Check the main `SETUP.md` for complete installation instructions.
