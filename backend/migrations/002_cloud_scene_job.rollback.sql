-- Use only after rolling back cloud workers and confirming no active executions.
-- Restore the verified backup if any project data needs recovery.
ALTER TABLE public.projects DROP COLUMN IF EXISTS scene_job_token;
ALTER TABLE public.projects DROP COLUMN IF EXISTS scene_job_started_at;
