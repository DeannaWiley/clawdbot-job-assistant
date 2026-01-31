-- ============================================================================
-- Job Queue Management System
-- ============================================================================
-- Adds job_status enum and queue management for autonomous applications

-- Add application_status to jobs table for queue management
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS application_status TEXT DEFAULT 'pending'
    CHECK (application_status IN ('pending', 'queued', 'applying', 'applied', 'skipped', 'expired', 'failed'));

-- Add priority for job queue ordering
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 5 
    CHECK (priority >= 1 AND priority <= 10);

-- Add match score for sorting
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS estimated_match_score NUMERIC(5,2);

-- Add deadline tracking
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS application_deadline TIMESTAMPTZ;

-- Add last check timestamp
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS last_checked_at TIMESTAMPTZ;

-- Add notes for manual review
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS notes TEXT;

-- Create index for queue queries
CREATE INDEX IF NOT EXISTS idx_jobs_queue ON jobs(application_status, priority DESC, created_at);

-- Create view for pending job queue
CREATE OR REPLACE VIEW job_queue AS
SELECT 
    id,
    title,
    company,
    source,
    source_url,
    application_status,
    priority,
    estimated_match_score,
    application_deadline,
    created_at,
    CASE 
        WHEN application_deadline IS NOT NULL AND application_deadline < NOW() THEN true
        ELSE false
    END AS is_expired
FROM jobs
WHERE application_status IN ('pending', 'queued')
  AND is_active = true
ORDER BY priority DESC, estimated_match_score DESC NULLS LAST, created_at;

-- Create view for job statistics
CREATE OR REPLACE VIEW job_queue_stats AS
SELECT 
    application_status,
    count(*) AS count,
    avg(estimated_match_score) AS avg_match_score
FROM jobs
GROUP BY application_status;

-- Function to add job to queue
CREATE OR REPLACE FUNCTION add_job_to_queue(
    p_url TEXT,
    p_title TEXT,
    p_company TEXT,
    p_source TEXT DEFAULT 'other',
    p_description TEXT DEFAULT '',
    p_priority INTEGER DEFAULT 5
) RETURNS UUID
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
    v_job_id UUID;
BEGIN
    INSERT INTO jobs (source_url, title, company, source, description, priority, application_status, is_active)
    VALUES (p_url, p_title, p_company, p_source, p_description, p_priority, 'queued', true)
    ON CONFLICT (source_url) DO UPDATE SET
        application_status = CASE 
            WHEN jobs.application_status = 'expired' THEN 'queued'
            ELSE jobs.application_status
        END,
        priority = GREATEST(jobs.priority, p_priority),
        last_checked_at = NOW()
    RETURNING id INTO v_job_id;
    
    RETURN v_job_id;
END;
$$;

-- Function to get next job from queue
CREATE OR REPLACE FUNCTION get_next_job_from_queue()
RETURNS TABLE(
    id UUID,
    title TEXT,
    company TEXT,
    source TEXT,
    source_url TEXT,
    description TEXT,
    priority INTEGER
)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    UPDATE jobs j
    SET application_status = 'applying',
        last_checked_at = NOW()
    WHERE j.id = (
        SELECT j2.id FROM jobs j2
        WHERE j2.application_status = 'queued'
          AND j2.is_active = true
          AND (j2.application_deadline IS NULL OR j2.application_deadline > NOW())
        ORDER BY j2.priority DESC, j2.estimated_match_score DESC NULLS LAST, j2.created_at
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    )
    RETURNING j.id, j.title, j.company, j.source, j.source_url, j.description, j.priority;
END;
$$;

-- Function to mark job as applied
CREATE OR REPLACE FUNCTION mark_job_applied(p_job_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
    UPDATE jobs SET application_status = 'applied' WHERE id = p_job_id;
END;
$$;

-- Function to mark job as failed
CREATE OR REPLACE FUNCTION mark_job_failed(p_job_id UUID, p_reason TEXT DEFAULT NULL)
RETURNS VOID
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
    UPDATE jobs 
    SET application_status = 'failed',
        notes = COALESCE(notes || E'\n', '') || 'Failed: ' || COALESCE(p_reason, 'Unknown')
    WHERE id = p_job_id;
END;
$$;

-- Function to mark job as expired
CREATE OR REPLACE FUNCTION mark_job_expired(p_job_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
    UPDATE jobs SET application_status = 'expired', is_active = false WHERE id = p_job_id;
END;
$$;
