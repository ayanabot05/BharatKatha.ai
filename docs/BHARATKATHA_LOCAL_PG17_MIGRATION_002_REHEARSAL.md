# BharatKatha migration 002: restored-cluster rehearsal

**Rehearsal passed on founder-supplied Cloud Shell output, 2026-10-16.** The founder ran the inline equivalent containing the two exact migration 002 ALTER statements because the repository files were absent in Cloud Shell. PostgreSQL 17.11, cluster `17/bharatkatha_test`, local Unix socket, port `5433`, database `bharatkatha_restore_test` were confirmed. The output reported PASS, ROLLBACK, zero lease columns afterwards, 44 rows and unchanged fingerprint `deaf9f6edda11b7049a649bdefb8cfed`. Production migration remains unexecuted. The file-based procedure below is retained for reproducibility; the files themselves were not transferred or executed in that run.

**Main API build authorized, not yet submitted.** The founder approved ONE build with a 30-minute timeout, plus source transfer. Local CLI access requires reauthentication and the external Cloud Shell browser is not accessible to this agent. A 60-file allowlisted source ZIP was prepared at `deliverables/bharatkatha-main-api-build-20261016.zip` (1,112,749 bytes; SHA-256 `c5a80c5c1c9d2bd86de64605cb39e327f77faa0ab657af5b9744effc47367e25`). Archive round-trip and exclusion of configured credential values passed. It includes a per-file checksum manifest. Transfer to the founder's authenticated Cloud Shell is pending. No build ID or image digest exists yet.

Pricing correction for the pending build: Google's current **default pool** e2-standard-2 rate is $0.006/minute (2 vCPU, 8 GB), so 20 minutes is $0.12 and 30 minutes is $0.18 gross compute, plus storage/logs/transfer where applicable. The earlier $0.00624 rate came from the private pool table. No actual build charges are available. Source: https://cloud.google.com/build/pricing .

## Scope and expected restored schema

The exact forward file `backend/migrations/002_cloud_scene_job.sql` adds nullable, default-free `scene_job_started_at timestamptz` and `scene_job_token text` to `public.projects`. It does not change rows, indexes, constraints, triggers, policies, functions, `auth`, or `storage`. The founder's restored snapshot reports 44 `projects` rows, seven public tables and 863 total rows. Earlier read-only source checks found `id` and `user_id` as `text`, `scenes` and `render` as `jsonb`, and both lease columns absent. The local restored database has not yet been queried by this agent; preflight must confirm those facts, plus index and constraint definitions, before running the rehearsal.

The rehearsal executes the reviewed forward file inside one transaction, verifies both new column definitions and a fingerprint of every original project row, and **rolls back**. It then checks both lease columns are absent. A failed check exits `psql` with `ON_ERROR_STOP=1`; the open transaction rolls back when the connection closes. `lock_timeout=3s` and `statement_timeout=30s` bound blocking. The script refuses the wrong database, port, PostgreSQL major version, data directory, TCP connection, column types, existing lease columns, or unexpected 44-row count. It uses a temporary baseline table only after those checks. All persistent table names are schema-qualified.

## Run in Cloud Shell, one checked step at a time

Stop if any output differs from the expected result. Do not substitute a production connection URI. These commands assume the reviewed repository files are present in a Cloud Shell checkout at `$HOME/BharatKatha.ai`; verify the checkout contains the same migration 002 and rehearsal files before running SQL. If it is not present, first transfer the reviewed files into a private Cloud Shell directory, then adjust only the local `-f` paths. Do not fetch a different branch and assume its SQL is identical.

1. Cluster inventory, no SQL:

   ```bash
   pg_lsclusters --no-header
   ```

   Require exactly the intended cluster line to show version `17`, name `bharatkatha_test`, port `5433`, status `online`. A second cluster may exist, but the commands below never use its port.

2. Verify the reviewed files in the Cloud Shell checkout before using them:

   ```bash
   sha256sum "$HOME/BharatKatha.ai/backend/migrations/002_cloud_scene_job.sql" "$HOME/BharatKatha.ai/backend/migrations/rehearsal_local_002_preflight.sql" "$HOME/BharatKatha.ai/backend/migrations/rehearsal_local_002_transaction.sql"
   ```

   Require these SHA-256 digests, in the same file order: `1a00f9fadb800c516cbb291847addb6550db2a332c448f8dfe890a0a67fc4dc6`, `7d529228aca74ebe8dcb7f7af40224d4c50db2e355f8b32a7f13e3c3f8904178`, `75bc4e0e14614275ac41a6d83a8d7bef3d6d2bc19082fa0038c74b018df7e2eb`. A differing digest, including one caused by line-ending conversion, requires reinspection before executing SQL. No SQL is run in this step.

3. Read-only preflight, with an explicit local socket and fixed target:

   ```bash
   sudo -u postgres psql -X -v ON_ERROR_STOP=1 -h /var/run/postgresql -p 5433 -U postgres -d bharatkatha_restore_test -f "$HOME/BharatKatha.ai/backend/migrations/rehearsal_local_002_preflight.sql"
   ```

   Require local `tcp_address` blank, port `5433`, version 17, data directory ending `/17/bharatkatha_test`, `public.projects` present, 44 rows, no lease columns, and the expected `id`, `user_id`, `scenes`, `render` types. Review printed index, constraint and trigger definitions. `request_limits` may be absent if migration 001 was not part of the backup; this does not block 002 itself but does block full API startup until 001 is handled separately. Record the row fingerprint for comparison.

4. Rollback-only rehearsal, after inspecting step 3 output:

   ```bash
   sudo -u postgres psql -X -v ON_ERROR_STOP=1 -h /var/run/postgresql -p 5433 -U postgres -d bharatkatha_restore_test -f "$HOME/BharatKatha.ai/backend/migrations/rehearsal_local_002_transaction.sql"
   ```

   Require `MIGRATION_002_REHEARSAL_VERIFIED_IN_TRANSACTION`, `ROLLBACK`, and `lease_columns_after_rollback = 0`; require process exit 0. Any exception, timeout, missing file or different cluster identity is a failure. Do not proceed to production migration on a failed rehearsal.

5. Re-run step 3. Require the same row count, fingerprint, indexes and constraints as before, and no lease columns. This verifies that the rollback restored the local snapshot.

## Limitations and next approval

This proves the SQL works against this restored application schema without persisting a change. A transaction rollback cannot prove a committed production migration, Supabase-specific privileges, production lock duration, Cloud Run Job dispatch, or remote video generation. The companion `002_cloud_scene_job.rollback.sql` drops the lease columns, which would discard any lease values written after a real migration; it is not a lossless rollback once jobs start. Production migration still needs separate approval and a quiet-job window.

After step 5 passes, request separate approval for **one main API Cloud Build only**. Candidate command from the repository root in Cloud Shell:

```bash
gcloud builds submit . --project=ayana-video-studio --region=asia-south1 --timeout=30m --config=deploy/main-api/cloudbuild.yaml --substitutions="_IMAGE=asia-south1-docker.pkg.dev/ayana-video-studio/vidbharat-beta/main-api:review-20261016"
```

It uses the existing Artifact Registry repository, builds a Linux image and stores logs. It does not deploy Cloud Run or touch `vidbharat-image-worker`. The default 2-vCPU/8-GB Cloud Build machine is estimated at about **US$0.125 for 20 minutes**, or **US$0.187 at the 30-minute cap**, plus small registry, staging storage and log charges, before any applicable free allowance. A failed build still incurs elapsed build charges. Rollback is simply to leave the review image unused; no serving traffic changes. Confirm current Google pricing and quota before authorization.
