-- READ ONLY. Execute against BharatKatha Supabase ref nnytovnsypegvrdilqks only.
-- Confirm the connection identity out of band before using this file.
BEGIN TRANSACTION READ ONLY;
SELECT current_database() AS database_name, current_user AS role_name,
       has_database_privilege(current_user, current_database(), 'CREATE') AS can_create_schema,
       has_schema_privilege(current_user, 'public', 'USAGE') AS can_read_public_schema,
       to_regclass('public.projects') AS source_table,
       to_regnamespace('bk_lease_rehearsal_20261016') AS existing_rehearsal_schema;
SELECT table_schema, table_name, column_name, data_type, is_nullable
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'projects'
 ORDER BY ordinal_position;
SELECT current_setting('search_path') AS session_search_path,
       current_schemas(true) AS effective_search_path;
SELECT conname, contype, pg_get_constraintdef(oid) AS definition
  FROM pg_constraint WHERE conrelid = 'public.projects'::regclass
 ORDER BY conname;
SELECT indexname, indexdef FROM pg_indexes
 WHERE schemaname = 'public' AND tablename = 'projects'
 ORDER BY indexname;
SELECT t.tgname, pg_get_triggerdef(t.oid) AS definition,
       p.pronamespace::regnamespace AS function_schema, p.proname AS function_name
  FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
 WHERE t.tgrelid = 'public.projects'::regclass AND NOT t.tgisinternal
 ORDER BY t.tgname;
SELECT policyname, roles, cmd, qual, with_check FROM pg_policies
 WHERE schemaname = 'public' AND tablename = 'projects'
 ORDER BY policyname;
SELECT grantee, privilege_type FROM information_schema.role_table_grants
 WHERE table_schema = 'public' AND table_name = 'projects'
 ORDER BY grantee, privilege_type;
SELECT nspname, nspacl FROM pg_namespace
 WHERE nspname IN ('public', 'bk_lease_rehearsal_20261016');
ROLLBACK;
