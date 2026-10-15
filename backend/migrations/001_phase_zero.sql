-- Apply once with a privileged server-side Supabase connection before this release.
BEGIN;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS content_contract jsonb;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS brief jsonb;
CREATE INDEX IF NOT EXISTS projects_owner_updated_idx ON projects(user_id, updated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS files_owner_path_idx ON files(user_id, storage_path) WHERE is_deleted = false;
CREATE INDEX IF NOT EXISTS coach_owner_created_idx ON coach_reports(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS pulse_owner_event_created_idx ON pulse_events(user_id, event, created_at DESC);
CREATE INDEX IF NOT EXISTS users_email_lower_idx ON users(lower(email));
CREATE TABLE IF NOT EXISTS request_limits (
    bucket text PRIMARY KEY,
    count integer NOT NULL,
    expires_at timestamptz NOT NULL
);
ALTER TABLE request_limits ENABLE ROW LEVEL SECURITY;
-- No public policies: only the backend's privileged database connection may access it.
COMMIT;
