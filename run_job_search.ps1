# Job Application Assistant - Scheduled Runner
# Runs Monday-Friday, 7 AM to 6 PM local time
# This script is called by Windows Task Scheduler

$LogFile = "C:\Users\deann\clawd\job-assistant\logs\scheduled_runs.log"
$JobAssistantDir = "C:\Users\deann\clawd\job-assistant"

# Create logs directory if it doesn't exist
if (-not (Test-Path "C:\Users\deann\clawd\job-assistant\logs")) {
    New-Item -ItemType Directory -Path "C:\Users\deann\clawd\job-assistant\logs" -Force
}

# Log start time
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LogFile -Value "[$timestamp] Starting scheduled job search..."

# Set environment variables for the session
$env:OPENROUTER_API_KEY = [System.Environment]::GetEnvironmentVariable("OPENROUTER_API_KEY", "User")
$env:SLACK_BOT_TOKEN = [System.Environment]::GetEnvironmentVariable("SLACK_BOT_TOKEN", "User")
$env:SLACK_APP_TOKEN = [System.Environment]::GetEnvironmentVariable("SLACK_APP_TOKEN", "User")
$env:GMAIL_CLIENT_ID = [System.Environment]::GetEnvironmentVariable("GMAIL_CLIENT_ID", "User")
$env:GMAIL_CLIENT_SECRET = [System.Environment]::GetEnvironmentVariable("GMAIL_CLIENT_SECRET", "User")

# CAPTCHA environment variables for automated solving
$env:CaptchaKey = [System.Environment]::GetEnvironmentVariable("CaptchaKey", "User")
$env:CaptchaBudget = [System.Environment]::GetEnvironmentVariable("CaptchaBudget", "User")
$env:CAPTCHA_2CAPTCHA_KEY = [System.Environment]::GetEnvironmentVariable("CAPTCHA_2CAPTCHA_KEY", "User")
$env:CAPTCHA_DAILY_BUDGET = [System.Environment]::GetEnvironmentVariable("CAPTCHA_DAILY_BUDGET", "User")

# Use CaptchaKey if CAPTCHA_2CAPTCHA_KEY not set
if (-not $env:CAPTCHA_2CAPTCHA_KEY -and $env:CaptchaKey) {
    $env:CAPTCHA_2CAPTCHA_KEY = $env:CaptchaKey
}
if (-not $env:CAPTCHA_DAILY_BUDGET -and $env:CaptchaBudget) {
    $env:CAPTCHA_DAILY_BUDGET = $env:CaptchaBudget
}

# Change to job-assistant directory and run
Set-Location $JobAssistantDir

try {
    # Run the main workflow with max 5 jobs per run to stay within daily target
    python main.py --max-jobs 5 2>&1 | Tee-Object -Append -FilePath $LogFile
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "[$timestamp] Job search completed successfully."
}
catch {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "[$timestamp] ERROR: $($_.Exception.Message)"
}
