-- Durable Cloud Run Job lease for scene generation. Apply before production API.
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS scene_job_started_at timestamptz;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS scene_job_token text;
