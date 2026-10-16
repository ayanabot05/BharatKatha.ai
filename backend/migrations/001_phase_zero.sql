-- Apply once with a privileged server-side Supabase connection before this release.
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '30s';
SET LOCAL search_path = pg_catalog;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS content_contract jsonb;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS brief jsonb;
CREATE INDEX IF NOT EXISTS projects_owner_updated_idx ON public.projects(user_id, updated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS files_owner_path_idx ON public.files(user_id, storage_path) WHERE is_deleted = false;
CREATE INDEX IF NOT EXISTS coach_owner_created_idx ON public.coach_reports(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS pulse_owner_event_created_idx ON public.pulse_events(user_id, event, created_at DESC);
CREATE INDEX IF NOT EXISTS users_email_lower_idx ON public.users(lower(email));
CREATE TABLE IF NOT EXISTS public.request_limits (
    bucket text PRIMARY KEY,
    count integer NOT NULL,
    expires_at timestamptz NOT NULL
);
ALTER TABLE public.request_limits ENABLE ROW LEVEL SECURITY;
-- No public policies: only the backend's privileged database connection may access it.
COMMIT;
