-- NOT EXECUTED. Run only after preserving the rehearsal evidence.
-- No CASCADE: fail if another object has acquired a dependency on this schema.
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '30s';
SET LOCAL search_path = pg_catalog;
DROP TABLE bk_lease_rehearsal_20261016.projects;
DROP SCHEMA bk_lease_rehearsal_20261016;
COMMIT;
