-- PREPARED ONLY. Run after authorized creation against BharatKatha ref nnytovnsypegvrdilqks.
-- Catalog privileges do not prove Supabase Data API exposure; also inspect API settings
-- and make an anon-key HTTP request expecting access denied.
BEGIN TRANSACTION READ ONLY;
SELECT current_database() AS database_name, current_user AS role_name,
       current_setting('search_path') AS session_search_path,
       current_schemas(true) AS effective_search_path;
SELECT n.nspname, n.nspacl,
       has_schema_privilege('anon', n.oid, 'USAGE') AS anon_usage,
       has_schema_privilege('authenticated', n.oid, 'USAGE') AS authenticated_usage,
       has_schema_privilege('service_role', n.oid, 'USAGE') AS service_role_usage
  FROM pg_namespace n
 WHERE n.nspname = 'bk_lease_rehearsal_20261016';
SELECT grantee::regrole::text AS grantee, privilege_type
  FROM pg_namespace n,
       LATERAL aclexplode(COALESCE(n.nspacl, acldefault('n', n.nspowner)))
 WHERE n.nspname = 'bk_lease_rehearsal_20261016'
 ORDER BY grantee, privilege_type;
SELECT relname, relkind, relrowsecurity, relforcerowsecurity, relacl
  FROM pg_class
 WHERE relnamespace = 'bk_lease_rehearsal_20261016'::regnamespace;
SELECT count(*) AS rows_in_rehearsal
  FROM bk_lease_rehearsal_20261016.projects;
SELECT conname, contype, pg_get_constraintdef(oid) AS definition
  FROM pg_constraint
 WHERE conrelid = 'bk_lease_rehearsal_20261016.projects'::regclass;
SELECT indexname, indexdef FROM pg_indexes
 WHERE schemaname = 'bk_lease_rehearsal_20261016';
SELECT tgname, pg_get_triggerdef(oid) AS definition FROM pg_trigger
 WHERE tgrelid = 'bk_lease_rehearsal_20261016.projects'::regclass
   AND NOT tgisinternal;
SELECT policyname, roles, cmd FROM pg_policies
 WHERE schemaname = 'bk_lease_rehearsal_20261016';
ROLLBACK;
