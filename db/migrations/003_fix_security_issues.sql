-- ============================================================================
-- Fix Supabase Security Issues
-- Version: 1.0.2
-- ============================================================================
-- This migration fixes security warnings detected by Supabase:
-- 1. SECURITY DEFINER views -> Change to SECURITY INVOKER
-- 2. Function search_path mutable -> Set explicit search_path
-- 3. Extension in public schema -> Move to extensions schema
-- ============================================================================

-- ============================================================================
-- 1. FIX VIEWS: Change from SECURITY DEFINER to SECURITY INVOKER
-- ============================================================================

-- Drop and recreate daily_application_stats with SECURITY INVOKER
DROP VIEW IF EXISTS daily_application_stats;
CREATE VIEW daily_application_stats 
WITH (security_invoker = true) AS
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

-- Drop and recreate captcha_performance with SECURITY INVOKER
DROP VIEW IF EXISTS captcha_performance;
CREATE VIEW captcha_performance
WITH (security_invoker = true) AS
SELECT 
    captcha_type,
    resolution_method,
    COUNT(*) as total_attempts,
    COUNT(*) FILTER (WHERE solved = true) as solved,
    ROUND(COUNT(*) FILTER (WHERE solved = true)::numeric / NULLIF(COUNT(*), 0) * 100, 2) as success_rate,
    AVG(solve_time_ms) as avg_solve_time_ms,
    SUM(cost_usd) as total_cost
FROM captcha_logs
GROUP BY captcha_type, resolution_method
ORDER BY total_attempts DESC;

-- Drop and recreate job_source_stats with SECURITY INVOKER
DROP VIEW IF EXISTS job_source_stats;
CREATE VIEW job_source_stats
WITH (security_invoker = true) AS
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

-- Drop and recreate weekly_summary with SECURITY INVOKER
DROP VIEW IF EXISTS weekly_summary;
CREATE VIEW weekly_summary
WITH (security_invoker = true) AS
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
-- 2. FIX FUNCTION: Set explicit search_path
-- ============================================================================

-- Drop existing function and triggers
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
DROP TRIGGER IF EXISTS update_jobs_updated_at ON jobs;
DROP TRIGGER IF EXISTS update_resumes_updated_at ON resumes;
DROP TRIGGER IF EXISTS update_applications_updated_at ON applications;
DROP FUNCTION IF EXISTS update_updated_at();

-- Recreate function with explicit search_path
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- Recreate triggers
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

-- Fix other functions with search_path
DROP FUNCTION IF EXISTS check_duplicate_application(UUID, UUID);
CREATE OR REPLACE FUNCTION check_duplicate_application(
    p_user_id UUID,
    p_job_id UUID
) RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM applications 
        WHERE user_id = p_user_id 
        AND job_id = p_job_id 
        AND status NOT IN ('failed', 'withdrawn')
    );
END;
$$;

DROP FUNCTION IF EXISTS upsert_job(TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, JSONB);
CREATE OR REPLACE FUNCTION upsert_job(
    p_source TEXT,
    p_source_url TEXT,
    p_title TEXT,
    p_company TEXT,
    p_location TEXT DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_raw_data JSONB DEFAULT NULL
) RETURNS UUID
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
    v_job_id UUID;
BEGIN
    SELECT id INTO v_job_id FROM jobs WHERE source_url = p_source_url;
    
    IF v_job_id IS NOT NULL THEN
        UPDATE jobs SET last_seen_at = NOW() WHERE id = v_job_id;
        RETURN v_job_id;
    END IF;
    
    INSERT INTO jobs (source, source_url, title, company, location, description, raw_data)
    VALUES (p_source, p_source_url, p_title, p_company, p_location, p_description, p_raw_data)
    RETURNING id INTO v_job_id;
    
    RETURN v_job_id;
END;
$$;

-- ============================================================================
-- 3. FIX EXTENSION: Move pg_trgm to extensions schema
-- ============================================================================

-- Create extensions schema if not exists
CREATE SCHEMA IF NOT EXISTS extensions;

-- Grant usage to authenticated and anon roles
GRANT USAGE ON SCHEMA extensions TO anon, authenticated;

-- Move extension (drop and recreate in new schema)
DROP EXTENSION IF EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA extensions;

-- Recreate the trigram index using the extensions schema
DROP INDEX IF EXISTS idx_jobs_title;
CREATE INDEX idx_jobs_title ON jobs USING gin(title extensions.gin_trgm_ops);

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- After running this migration, verify in Supabase Dashboard:
-- 1. No SECURITY DEFINER warnings on views
-- 2. No search_path warnings on functions
-- 3. pg_trgm extension moved to 'extensions' schema
