-- NOT EXECUTED. Requires explicit founder approval after verified backup restore.
-- The only live object read is public.projects metadata; no rows are copied.
-- CREATE/ALTER target ONLY bk_lease_rehearsal_20261016.*.
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '30s';
SET LOCAL search_path = pg_catalog;
CREATE SCHEMA bk_lease_rehearsal_20261016;
CREATE TABLE bk_lease_rehearsal_20261016.projects (LIKE public.projects);
ALTER TABLE bk_lease_rehearsal_20261016.projects
  ADD COLUMN IF NOT EXISTS scene_job_started_at timestamptz;
ALTER TABLE bk_lease_rehearsal_20261016.projects
  ADD COLUMN IF NOT EXISTS scene_job_token text;
COMMIT;

-- Verify types and that the isolated copy has no rows.
SELECT column_name, data_type FROM information_schema.columns
 WHERE table_schema = 'bk_lease_rehearsal_20261016'
   AND table_name = 'projects'
   AND column_name IN ('id','user_id','scenes','render','scene_job_started_at','scene_job_token')
 ORDER BY column_name;
SELECT count(*) AS rehearsal_rows FROM bk_lease_rehearsal_20261016.projects;
