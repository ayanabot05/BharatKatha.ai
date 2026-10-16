-- Read-only inventory for the restored Cloud Shell PostgreSQL 17 test cluster.
-- Invoke with -h /var/run/postgresql -p 5433 -d bharatkatha_restore_test.
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '30s';
SET LOCAL search_path = pg_catalog;

SELECT current_database() AS database_name, current_user AS role_name,
       current_setting('port') AS server_port,
       inet_server_addr() AS tcp_address,
       current_setting('server_version_num') AS server_version_num,
       current_setting('data_directory') AS data_directory,
       current_setting('search_path') AS search_path;
SELECT to_regclass('public.projects') AS projects_table,
       to_regclass('public.request_limits') AS request_limits_table;
SELECT column_name, data_type, is_nullable, column_default
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'projects'
 ORDER BY ordinal_position;
SELECT indexname, indexdef FROM pg_indexes
 WHERE schemaname = 'public' AND tablename = 'projects'
 ORDER BY indexname;
SELECT conname, contype, pg_get_constraintdef(oid) AS definition
  FROM pg_constraint WHERE conrelid = to_regclass('public.projects')
 ORDER BY conname;
SELECT tgname, pg_get_triggerdef(oid) AS definition
  FROM pg_trigger WHERE tgrelid = to_regclass('public.projects') AND NOT tgisinternal
 ORDER BY tgname;
SELECT count(*) AS projects_rows,
       md5(string_agg(to_jsonb(p)::text, '|' ORDER BY p.id)) AS projects_data_fingerprint
  FROM public.projects AS p;
ROLLBACK;
