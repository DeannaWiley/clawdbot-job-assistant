-- ============================================================================
-- ClawdBot Supabase Database Schema
-- Version: 1.0.0
-- Created: 2026-01-31
-- ============================================================================
-- This migration creates the complete database schema for ClawdBot's
-- job application tracking, automation logging, and analytics system.
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search optimization

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Table: users
-- Stores ClawdBot user profiles (supports multi-user in future)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT,
    location TEXT,
    linkedin_url TEXT,
    portfolio_url TEXT,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

-- ----------------------------------------------------------------------------
-- Table: automation_runs
-- Tracks each ClawdBot execution session
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS automation_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    run_type TEXT NOT NULL CHECK (run_type IN ('scheduled', 'manual', 'test', 'retry')),
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    jobs_found INTEGER DEFAULT 0,
    jobs_applied INTEGER DEFAULT 0,
    jobs_skipped INTEGER DEFAULT 0,
    jobs_failed INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_automation_runs_user ON automation_runs(user_id);
CREATE INDEX idx_automation_runs_status ON automation_runs(status);
CREATE INDEX idx_automation_runs_started ON automation_runs(started_at DESC);

-- ----------------------------------------------------------------------------
-- Table: jobs
-- Stores job posting details (deduplicated by URL)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id TEXT,  -- ID from job board (if available)
    source TEXT NOT NULL CHECK (source IN ('linkedin', 'indeed', 'glassdoor', 'greenhouse', 'lever', 'workday', 'company_site', 'other')),
    source_url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    job_type TEXT,  -- full-time, part-time, contract, etc.
    remote_type TEXT,  -- remote, hybrid, onsite
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency TEXT DEFAULT 'USD',
    description TEXT,
    requirements TEXT,
    posted_date DATE,
    expires_date DATE,
    is_active BOOLEAN DEFAULT true,
    raw_data JSONB,  -- Original scraped data
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jobs_source ON jobs(source);
CREATE INDEX idx_jobs_company ON jobs(company);
CREATE INDEX idx_jobs_title ON jobs USING gin(title gin_trgm_ops);
CREATE INDEX idx_jobs_location ON jobs(location);
CREATE INDEX idx_jobs_active ON jobs(is_active) WHERE is_active = true;
CREATE INDEX idx_jobs_posted ON jobs(posted_date DESC);
CREATE INDEX idx_jobs_source_url ON jobs(source_url);

-- ----------------------------------------------------------------------------
-- Table: resumes
-- Stores resume versions with metadata
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS resumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    version_name TEXT NOT NULL,  -- e.g., "base", "tailored_graphic_design"
    is_base BOOLEAN DEFAULT false,
    file_path TEXT,  -- Local file path
    file_url TEXT,   -- Supabase storage URL (if uploaded)
    file_type TEXT DEFAULT 'pdf' CHECK (file_type IN ('pdf', 'docx', 'html', 'txt')),
    file_size_bytes INTEGER,
    content_text TEXT,  -- Plain text for search/analysis
    content_hash TEXT,  -- SHA256 for deduplication
    tailored_for_job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    ai_modifications JSONB,  -- What AI changed
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_resumes_user ON resumes(user_id);
CREATE INDEX idx_resumes_base ON resumes(is_base) WHERE is_base = true;
CREATE INDEX idx_resumes_hash ON resumes(content_hash);

-- ----------------------------------------------------------------------------
-- Table: cover_letters
-- Stores cover letter versions with metadata
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cover_letters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    version_name TEXT,
    file_path TEXT,
    file_url TEXT,
    content_text TEXT NOT NULL,
    content_hash TEXT,
    ai_generated BOOLEAN DEFAULT true,
    ai_model_used TEXT,
    generation_prompt TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cover_letters_user ON cover_letters(user_id);
CREATE INDEX idx_cover_letters_job ON cover_letters(job_id);

-- ----------------------------------------------------------------------------
-- Table: match_scores
-- AI-generated job fit analysis
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS match_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    overall_score DECIMAL(5,2) NOT NULL CHECK (overall_score >= 0 AND overall_score <= 100),
    skills_match DECIMAL(5,2),
    experience_match DECIMAL(5,2),
    location_match DECIMAL(5,2),
    salary_match DECIMAL(5,2),
    culture_match DECIMAL(5,2),
    matched_keywords TEXT[],
    missing_keywords TEXT[],
    reasoning TEXT,
    ai_model_used TEXT,
    recommendation TEXT CHECK (recommendation IN ('strong_apply', 'apply', 'maybe', 'skip', 'no_match')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, job_id)
);

CREATE INDEX idx_match_scores_user ON match_scores(user_id);
CREATE INDEX idx_match_scores_job ON match_scores(job_id);
CREATE INDEX idx_match_scores_score ON match_scores(overall_score DESC);
CREATE INDEX idx_match_scores_recommendation ON match_scores(recommendation);

-- ----------------------------------------------------------------------------
-- Table: applications
-- Each job application attempt
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    automation_run_id UUID REFERENCES automation_runs(id) ON DELETE SET NULL,
    resume_id UUID REFERENCES resumes(id) ON DELETE SET NULL,
    cover_letter_id UUID REFERENCES cover_letters(id) ON DELETE SET NULL,
    match_score_id UUID REFERENCES match_scores(id) ON DELETE SET NULL,
    
    -- Application status
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'in_progress', 'submitted', 'failed', 
        'rejected', 'interview', 'offer', 'accepted', 'withdrawn'
    )),
    submission_method TEXT CHECK (submission_method IN ('auto', 'manual', 'easy_apply', 'email')),
    
    -- Timestamps
    started_at TIMESTAMPTZ DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    
    -- Form filling details
    fields_filled INTEGER DEFAULT 0,
    fields_total INTEGER,
    fields_failed TEXT[],
    
    -- Outcome tracking
    confirmation_received BOOLEAN DEFAULT false,
    confirmation_email_id TEXT,
    response_received BOOLEAN DEFAULT false,
    response_type TEXT,  -- rejection, interview_request, offer, etc.
    response_date DATE,
    
    -- Error handling
    retry_count INTEGER DEFAULT 0,
    last_error TEXT,
    error_screenshot_path TEXT,
    
    -- Metadata
    notes TEXT,
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_applications_user ON applications(user_id);
CREATE INDEX idx_applications_job ON applications(job_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_submitted ON applications(submitted_at DESC);
CREATE INDEX idx_applications_run ON applications(automation_run_id);
CREATE UNIQUE INDEX idx_applications_unique_job ON applications(user_id, job_id) 
    WHERE status NOT IN ('failed', 'withdrawn');

-- ----------------------------------------------------------------------------
-- Table: captcha_logs
-- CAPTCHA encounter and resolution tracking
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS captcha_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id UUID REFERENCES applications(id) ON DELETE CASCADE,
    automation_run_id UUID REFERENCES automation_runs(id) ON DELETE SET NULL,
    
    -- CAPTCHA details
    captcha_type TEXT NOT NULL CHECK (captcha_type IN (
        'recaptcha_v2', 'recaptcha_v3', 'recaptcha_enterprise',
        'hcaptcha', 'funcaptcha', 'turnstile', 'geetest', 'image', 'text', 'unknown'
    )),
    site_key TEXT,
    page_url TEXT,
    
    -- Resolution
    resolution_method TEXT CHECK (resolution_method IN ('2captcha', 'anti-captcha', 'human', 'bypass', 'failed')),
    resolution_tier INTEGER,  -- 1=auto, 2=service, 3=human
    solved BOOLEAN DEFAULT false,
    solve_time_ms INTEGER,
    cost_usd DECIMAL(10,6),
    
    -- Error details
    error_code TEXT,
    error_message TEXT,
    screenshot_path TEXT,
    
    -- Metadata
    attempts INTEGER DEFAULT 1,
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_captcha_logs_application ON captcha_logs(application_id);
CREATE INDEX idx_captcha_logs_type ON captcha_logs(captcha_type);
CREATE INDEX idx_captcha_logs_solved ON captcha_logs(solved);
CREATE INDEX idx_captcha_logs_method ON captcha_logs(resolution_method);

-- ----------------------------------------------------------------------------
-- Table: form_field_logs
-- Detailed form field filling logs for debugging
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS form_field_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id UUID REFERENCES applications(id) ON DELETE CASCADE,
    
    field_name TEXT,
    field_type TEXT,  -- text, select, radio, checkbox, file, etc.
    field_label TEXT,
    
    value_used TEXT,
    value_source TEXT,  -- profile, ai_generated, default, user_input
    
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_form_field_logs_application ON form_field_logs(application_id);
CREATE INDEX idx_form_field_logs_success ON form_field_logs(success) WHERE success = false;

-- ----------------------------------------------------------------------------
-- Table: email_tracking
-- Track emails related to job applications
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS email_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    application_id UUID REFERENCES applications(id) ON DELETE SET NULL,
    
    gmail_message_id TEXT UNIQUE,
    thread_id TEXT,
    
    email_type TEXT CHECK (email_type IN (
        'confirmation', 'rejection', 'interview_request', 
        'offer', 'follow_up', 'assessment', 'other'
    )),
    
    from_address TEXT,
    subject TEXT,
    received_at TIMESTAMPTZ,
    snippet TEXT,
    
    processed BOOLEAN DEFAULT false,
    ai_classification TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_email_tracking_user ON email_tracking(user_id);
CREATE INDEX idx_email_tracking_application ON email_tracking(application_id);
CREATE INDEX idx_email_tracking_gmail_id ON email_tracking(gmail_message_id);
CREATE INDEX idx_email_tracking_type ON email_tracking(email_type);

-- ============================================================================
-- ANALYTICS VIEWS
-- ============================================================================

-- Daily application statistics
CREATE OR REPLACE VIEW daily_application_stats AS
SELECT 
    DATE(submitted_at) as date,
    user_id,
    COUNT(*) as total_applications,
    COUNT(*) FILTER (WHERE status = 'submitted') as successful,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    COUNT(*) FILTER (WHERE status = 'interview') as interviews,
    COUNT(*) FILTER (WHERE confirmation_received = true) as confirmed,
    AVG(fields_filled::float / NULLIF(fields_total, 0) * 100) as avg_form_completion
FROM applications
WHERE submitted_at IS NOT NULL
GROUP BY DATE(submitted_at), user_id
ORDER BY date DESC;

-- CAPTCHA performance metrics
CREATE OR REPLACE VIEW captcha_performance AS
SELECT 
    captcha_type,
    resolution_method,
    COUNT(*) as total_attempts,
    COUNT(*) FILTER (WHERE solved = true) as solved,
    ROUND(COUNT(*) FILTER (WHERE solved = true)::numeric / COUNT(*) * 100, 2) as success_rate,
    AVG(solve_time_ms) as avg_solve_time_ms,
    SUM(cost_usd) as total_cost
FROM captcha_logs
GROUP BY captcha_type, resolution_method
ORDER BY total_attempts DESC;

-- Job source effectiveness
CREATE OR REPLACE VIEW job_source_stats AS
SELECT 
    j.source,
    COUNT(DISTINCT j.id) as jobs_found,
    COUNT(DISTINCT a.id) as applications,
    COUNT(DISTINCT a.id) FILTER (WHERE a.status = 'submitted') as successful_applications,
    COUNT(DISTINCT a.id) FILTER (WHERE a.status = 'interview') as interviews,
    ROUND(AVG(ms.overall_score), 2) as avg_match_score
FROM jobs j
LEFT JOIN applications a ON j.id = a.job_id
LEFT JOIN match_scores ms ON j.id = ms.job_id
GROUP BY j.source
ORDER BY applications DESC;

-- Weekly summary
CREATE OR REPLACE VIEW weekly_summary AS
SELECT 
    DATE_TRUNC('week', a.submitted_at) as week_start,
    a.user_id,
    COUNT(*) as applications_submitted,
    COUNT(*) FILTER (WHERE a.status = 'interview') as interviews,
    COUNT(*) FILTER (WHERE a.status = 'offer') as offers,
    ROUND(AVG(ms.overall_score), 2) as avg_match_score,
    COUNT(DISTINCT j.company) as unique_companies
FROM applications a
LEFT JOIN jobs j ON a.job_id = j.id
LEFT JOIN match_scores ms ON a.match_score_id = ms.id
WHERE a.submitted_at IS NOT NULL
GROUP BY DATE_TRUNC('week', a.submitted_at), a.user_id
ORDER BY week_start DESC;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to relevant tables
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_resumes_updated_at
    BEFORE UPDATE ON resumes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_applications_updated_at
    BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Function to check for duplicate job applications
CREATE OR REPLACE FUNCTION check_duplicate_application(
    p_user_id UUID,
    p_job_id UUID
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM applications 
        WHERE user_id = p_user_id 
        AND job_id = p_job_id 
        AND status NOT IN ('failed', 'withdrawn')
    );
END;
$$ LANGUAGE plpgsql;

-- Function to get or create job by URL
CREATE OR REPLACE FUNCTION upsert_job(
    p_source TEXT,
    p_source_url TEXT,
    p_title TEXT,
    p_company TEXT,
    p_location TEXT DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_raw_data JSONB DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_job_id UUID;
BEGIN
    -- Try to find existing job
    SELECT id INTO v_job_id FROM jobs WHERE source_url = p_source_url;
    
    IF v_job_id IS NOT NULL THEN
        -- Update last_seen_at
        UPDATE jobs SET last_seen_at = NOW() WHERE id = v_job_id;
        RETURN v_job_id;
    END IF;
    
    -- Insert new job
    INSERT INTO jobs (source, source_url, title, company, location, description, raw_data)
    VALUES (p_source, p_source_url, p_title, p_company, p_location, p_description, p_raw_data)
    RETURNING id INTO v_job_id;
    
    RETURN v_job_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE automation_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE resumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE cover_letters ENABLE ROW LEVEL SECURITY;
ALTER TABLE match_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE captcha_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE form_field_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_tracking ENABLE ROW LEVEL SECURITY;

-- Jobs table: publicly readable (no user-specific data)
CREATE POLICY "Jobs are publicly readable" ON jobs
    FOR SELECT USING (true);

CREATE POLICY "Service role can manage jobs" ON jobs
    FOR ALL USING (auth.role() = 'service_role');

-- Users: users can only see their own data
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Service role can manage users" ON users
    FOR ALL USING (auth.role() = 'service_role');

-- Applications: users can only see their own applications
CREATE POLICY "Users can view own applications" ON applications
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own applications" ON applications
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own applications" ON applications
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage applications" ON applications
    FOR ALL USING (auth.role() = 'service_role');

-- Resumes: users can only see their own resumes
CREATE POLICY "Users can manage own resumes" ON resumes
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage resumes" ON resumes
    FOR ALL USING (auth.role() = 'service_role');

-- Cover Letters: users can only see their own cover letters
CREATE POLICY "Users can manage own cover_letters" ON cover_letters
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage cover_letters" ON cover_letters
    FOR ALL USING (auth.role() = 'service_role');

-- Match Scores: users can only see their own scores
CREATE POLICY "Users can manage own match_scores" ON match_scores
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage match_scores" ON match_scores
    FOR ALL USING (auth.role() = 'service_role');

-- Automation Runs: users can only see their own runs
CREATE POLICY "Users can manage own automation_runs" ON automation_runs
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage automation_runs" ON automation_runs
    FOR ALL USING (auth.role() = 'service_role');

-- CAPTCHA Logs: linked through applications
CREATE POLICY "Users can view captcha_logs through applications" ON captcha_logs
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM applications a 
            WHERE a.id = captcha_logs.application_id 
            AND a.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role can manage captcha_logs" ON captcha_logs
    FOR ALL USING (auth.role() = 'service_role');

-- Form Field Logs: linked through applications
CREATE POLICY "Users can view form_field_logs through applications" ON form_field_logs
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM applications a 
            WHERE a.id = form_field_logs.application_id 
            AND a.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role can manage form_field_logs" ON form_field_logs
    FOR ALL USING (auth.role() = 'service_role');

-- Email Tracking: users can only see their own emails
CREATE POLICY "Users can manage own email_tracking" ON email_tracking
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage email_tracking" ON email_tracking
    FOR ALL USING (auth.role() = 'service_role');

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert default user (Deanna) - will be updated with actual auth.uid later
-- This is for development/testing purposes
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
) ON CONFLICT (email) DO NOTHING;
