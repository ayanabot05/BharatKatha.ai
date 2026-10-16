-- ONLY for local restored PostgreSQL cluster 17/bharatkatha_test on port 5433.
-- Deliberately rolls back: the restored database is unchanged on success.
-- Use psql -X -v ON_ERROR_STOP=1 with explicit Unix socket, port, user and DB.
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '30s';
SET LOCAL search_path = pg_catalog;

DO $guard$
BEGIN
  IF current_database() <> 'bharatkatha_restore_test'
     OR current_setting('port') <> '5433'
     OR inet_server_addr() IS NOT NULL
     OR current_setting('server_version_num')::int NOT BETWEEN 170000 AND 179999
     OR right(current_setting('data_directory'), length('/17/bharatkatha_test')) <> '/17/bharatkatha_test'
  THEN
    RAISE EXCEPTION 'Refusing migration 002 rehearsal: unexpected database or cluster';
  END IF;
  IF to_regclass('public.projects') IS NULL THEN
    RAISE EXCEPTION 'Refusing migration 002 rehearsal: public.projects is absent';
  END IF;
  IF (SELECT count(*) FROM information_schema.columns
       WHERE table_schema = 'public' AND table_name = 'projects'
         AND (column_name, data_type) IN
           (('id','text'), ('user_id','text'), ('scenes','jsonb'), ('render','jsonb'))) <> 4
  THEN
    RAISE EXCEPTION 'Refusing migration 002 rehearsal: projects column types differ';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns
       WHERE table_schema = 'public' AND table_name = 'projects'
         AND column_name IN ('scene_job_started_at', 'scene_job_token'))
  THEN
    RAISE EXCEPTION 'Refusing migration 002 rehearsal: lease columns already exist';
  END IF;
  IF (SELECT count(*) FROM public.projects) <> 44 THEN
    RAISE EXCEPTION 'Refusing migration 002 rehearsal: expected 44 restored projects';
  END IF;
END
$guard$;

CREATE TEMP TABLE pg_temp.bk002_baseline ON COMMIT DROP AS
SELECT count(*) AS row_count,
       md5(string_agg(to_jsonb(p)::text, '|' ORDER BY p.id)) AS data_fingerprint
  FROM public.projects AS p;

-- Execute the reviewed forward migration itself; \ir resolves relative to this file.
\ir 002_cloud_scene_job.sql

DO $verify$
BEGIN
  IF (SELECT count(*) FROM information_schema.columns
       WHERE table_schema = 'public' AND table_name = 'projects'
         AND ((column_name = 'scene_job_started_at' AND data_type = 'timestamp with time zone')
           OR (column_name = 'scene_job_token' AND data_type = 'text'))
         AND is_nullable = 'YES' AND column_default IS NULL) <> 2
  THEN
    RAISE EXCEPTION 'Migration 002 did not create the expected nullable, default-free columns';
  END IF;
  IF (SELECT count(*) FROM public.projects) <> (SELECT row_count FROM pg_temp.bk002_baseline)
     OR (SELECT md5(string_agg((to_jsonb(p) - 'scene_job_started_at' - 'scene_job_token')::text,
                               '|' ORDER BY p.id)) FROM public.projects AS p)
        IS DISTINCT FROM (SELECT data_fingerprint FROM pg_temp.bk002_baseline)
  THEN
    RAISE EXCEPTION 'Migration 002 changed restored project rows';
  END IF;
END
$verify$;
SELECT 'MIGRATION_002_REHEARSAL_VERIFIED_IN_TRANSACTION' AS result;
ROLLBACK;

-- A successful run must leave the restored database with neither lease column.
SELECT count(*) AS lease_columns_after_rollback
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'projects'
   AND column_name IN ('scene_job_started_at', 'scene_job_token');
