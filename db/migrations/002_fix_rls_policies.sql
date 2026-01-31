-- ============================================================================
-- Fix RLS Policies for ClawdBot
-- Version: 1.0.1
-- ============================================================================
-- This migration updates RLS policies to allow the anon key to perform
-- necessary operations for ClawdBot automation.
-- ============================================================================

-- Drop existing restrictive policies
DROP POLICY IF EXISTS "Jobs are publicly readable" ON jobs;
DROP POLICY IF EXISTS "Service role can manage jobs" ON jobs;

DROP POLICY IF EXISTS "Users can view own profile" ON users;
DROP POLICY IF EXISTS "Users can update own profile" ON users;
DROP POLICY IF EXISTS "Service role can manage users" ON users;

DROP POLICY IF EXISTS "Users can view own applications" ON applications;
DROP POLICY IF EXISTS "Users can insert own applications" ON applications;
DROP POLICY IF EXISTS "Users can update own applications" ON applications;
DROP POLICY IF EXISTS "Service role can manage applications" ON applications;

DROP POLICY IF EXISTS "Users can manage own resumes" ON resumes;
DROP POLICY IF EXISTS "Service role can manage resumes" ON resumes;

DROP POLICY IF EXISTS "Users can manage own cover_letters" ON cover_letters;
DROP POLICY IF EXISTS "Service role can manage cover_letters" ON cover_letters;

DROP POLICY IF EXISTS "Users can manage own match_scores" ON match_scores;
DROP POLICY IF EXISTS "Service role can manage match_scores" ON match_scores;

DROP POLICY IF EXISTS "Users can manage own automation_runs" ON automation_runs;
DROP POLICY IF EXISTS "Service role can manage automation_runs" ON automation_runs;

DROP POLICY IF EXISTS "Users can view captcha_logs through applications" ON captcha_logs;
DROP POLICY IF EXISTS "Service role can manage captcha_logs" ON captcha_logs;

DROP POLICY IF EXISTS "Users can view form_field_logs through applications" ON form_field_logs;
DROP POLICY IF EXISTS "Service role can manage form_field_logs" ON form_field_logs;

DROP POLICY IF EXISTS "Users can manage own email_tracking" ON email_tracking;
DROP POLICY IF EXISTS "Service role can manage email_tracking" ON email_tracking;

-- ============================================================================
-- NEW POLICIES: Allow anon key to perform all necessary operations
-- For single-user ClawdBot, we allow full access with anon key
-- ============================================================================

-- Jobs: Full access (anyone can read/write jobs)
CREATE POLICY "Allow all on jobs" ON jobs FOR ALL USING (true) WITH CHECK (true);

-- Users: Full access
CREATE POLICY "Allow all on users" ON users FOR ALL USING (true) WITH CHECK (true);

-- Applications: Full access
CREATE POLICY "Allow all on applications" ON applications FOR ALL USING (true) WITH CHECK (true);

-- Resumes: Full access
CREATE POLICY "Allow all on resumes" ON resumes FOR ALL USING (true) WITH CHECK (true);

-- Cover Letters: Full access
CREATE POLICY "Allow all on cover_letters" ON cover_letters FOR ALL USING (true) WITH CHECK (true);

-- Match Scores: Full access
CREATE POLICY "Allow all on match_scores" ON match_scores FOR ALL USING (true) WITH CHECK (true);

-- Automation Runs: Full access
CREATE POLICY "Allow all on automation_runs" ON automation_runs FOR ALL USING (true) WITH CHECK (true);

-- CAPTCHA Logs: Full access
CREATE POLICY "Allow all on captcha_logs" ON captcha_logs FOR ALL USING (true) WITH CHECK (true);

-- Form Field Logs: Full access
CREATE POLICY "Allow all on form_field_logs" ON form_field_logs FOR ALL USING (true) WITH CHECK (true);

-- Email Tracking: Full access
CREATE POLICY "Allow all on email_tracking" ON email_tracking FOR ALL USING (true) WITH CHECK (true);

-- ============================================================================
-- Insert default user if not exists
-- ============================================================================
INSERT INTO users (id, email, full_name, phone, location, linkedin_url, portfolio_url, preferences)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'DeannaWileyCareers@gmail.com',
    'Deanna Wiley',
    '7082658734',
    'Alameda, CA',
    'https://www.linkedin.com/in/deannafwiley/',
    'https://dwileydesign.myportfolio.com/',
    '{
        "salary_min": 60000,
        "salary_target": 80000,
        "salary_max": 100000,
        "willing_to_relocate": false,
        "remote_preferred": true,
        "education": {
            "school": "DeVry University",
            "degree": "BS Multimedia Design & Business Administration",
            "graduation_year": 2023
        },
        "experience": {
            "years_design": 3,
            "current_title": "Graphic Designer",
            "cannabis_experience": "2 years Budtender at Cannabist, Chicago"
        }
    }'::jsonb
) ON CONFLICT (email) DO UPDATE SET
    preferences = EXCLUDED.preferences,
    updated_at = NOW();
