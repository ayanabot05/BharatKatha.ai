# BharatKatha isolated-schema rehearsal and first Linux build review — 16 October 2026

**Prepared SQL only. No rehearsal schema, migration, Cloud Build, or production deployment has been executed.** The founder subsequently completed a PostgreSQL 17 logical backup and isolated application-data restore, summarized in the [current approval packet](CLOUD_DEPLOYMENT_APPROVAL_REVISED_2026-10-16.md). Target Supabase ref: `nnytovnsypegvrdilqks` in the separate BharatKatha account. Never use AYANA Supabase credentials or project.

## Exact schema targeting and SQL

The complete files for review are [read-only preflight](../backend/migrations/rehearsal_002_preflight_read_only.sql), [create and migrate](../backend/migrations/rehearsal_002_create.sql), and [cleanup](../backend/migrations/rehearsal_002_cleanup.sql). The changing statements are exactly:

```sql
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
```

`CREATE TABLE ... LIKE public.projects` copies the current column names, data types and `NOT NULL` settings, without rows, defaults, indexes, foreign keys, triggers, policies or functions under this syntax. `public.projects` is read for metadata only. The only changing statements create the named schema/table and add columns to that table; no `auth`, `storage`, other production schema, existing function, trigger or policy is modified. `SET LOCAL search_path = pg_catalog` and fully qualified relation names prevent resolution through an unexpected application schema. The transaction rolls back on an error. The fixed `CREATE SCHEMA` fails if the name exists. Static scope tests passed; actual PostgreSQL execution and privilege behavior remain unverified. [PostgreSQL `LIKE` behavior](https://www.postgresql.org/docs/current/sql-createtable.html).

## Preconditions before any SQL is run

1. Confirm the connection is to BharatKatha ref `nnytovnsypegvrdilqks` using URL metadata without printing a password. Check that the role has `CREATE` on the database, `USAGE` on `public`, and access to the `public.projects` definition. An earlier read-only query confirmed database `CREATE` privilege, but table privileges and the current exposed-schema API setting still need a fresh check.
2. Verify the current `public.projects` columns, foreign keys/other constraints, indexes, trigger definitions and functions, policies, table/schema grants and effective `search_path` using the reviewed read-only preflight SQL. Catalog inspection of trigger functions does not find all functions that dynamically mention `projects`; this copy intentionally does not exercise production RLS, triggers or foreign keys. Do not run the create file if the schema already exists, the BharatKatha ref differs, or `public.projects` is missing.
3. The founder reports that the 452,754-byte logical backup was restored to an isolated PostgreSQL 17 database: seven application tables, 863 rows, and 11 constraints. This passes the application-data restore check on founder-supplied evidence. Independently compare the GCS object checksum with the local archive, review bucket IAM, and capture source counts before relying on the backup for a live migration. Full Supabase recovery is not established.
4. Check BharatKatha Supabase API settings to confirm `bk_lease_rehearsal_20261016` is **not** in Exposed schemas. No `GRANT` appears in the rehearsal SQL. After authorized creation, run the [read-only post-create verification](../backend/migrations/rehearsal_002_verify_read_only.sql) to inspect effective `anon`, `authenticated`, and `service_role` access plus schema ACLs, relation ACLs, row count, constraints, indexes, triggers, and policies. Reject any unintended grant. Then attempt a Data API request using the project's anon key and `Accept-Profile: bk_lease_rehearsal_20261016`; it must be denied. Do not log the key. Supabase requires explicit exposure and grants for custom schemas. This cannot be empirically verified before schema creation. [Supabase custom schemas](https://supabase.com/docs/guides/api/using-custom-schemas).

These checks are prepared, not passed. Existing BharatKatha `public.projects` read-only column evidence: `id` and `user_id` are `text`; `scenes` and `render` are `jsonb`; lease columns are absent. A prior privilege query showed this connection can create a schema, but no rehearsal schema exists.

### Prior backup plan and actual archive

The earlier proposed table-only path below was **not** the archive used. The founder reports a broader application-data archive at `gs://ayana-video-studio-bhartkath-db-backups/bharatkatha-20261016-071034.dump`, local size 452,754 bytes and SHA-256 `bf4f5a2a2d37b068b6ea8bd657847e11c71871ff1d869c90d088fe0b925eb03f`. Its seven `public` tables and 863 rows restored successfully into an isolated PostgreSQL 17 database. The bucket name contains legacy spelling and remains unchanged. Founder reports public access prevention, uniform access and seven-day soft delete; detailed IAM and independent uploaded-object hash checks remain open. The correct `bharatkatha-database-url` has an enabled version and passed a Cloud Shell `SELECT 1` per founder output. The commands below remain a repeatable **table-only** backup plan; they are not a record of the commands the founder ran.

Exact proposed Cloud Shell command after approval and the security preflight, from the source checkout (the URL passes on stdin and is never printed or put in `pg_dump` arguments):

```bash
set -euo pipefail
umask 077
BK_TMP="$(mktemp -d /tmp/bharatkatha-rehearsal.XXXXXX)"
gcloud secrets versions access latest --project=ayana-video-studio \
  --secret=bharatkatha-database-url | \
  python3 deploy/cloud-shell/dump_bharatkatha_projects.py "$BK_TMP/projects.dump"
gcloud storage cp "$BK_TMP/projects.dump" \
  gs://ayana-video-studio-bhartkath-db-backups/rehearsal-20261016/projects.dump
gcloud storage cp \
  gs://ayana-video-studio-bhartkath-db-backups/rehearsal-20261016/projects.dump \
  "$BK_TMP/downloaded.dump"
test "$(sha256sum "$BK_TMP/projects.dump" | cut -d' ' -f1)" = \
     "$(sha256sum "$BK_TMP/downloaded.dump" | cut -d' ' -f1)"
```

Then, **on the same Cloud Shell host**, restore the downloaded archive into a fresh local PostgreSQL cluster/database; stop if compatible `initdb`, `pg_ctl`, `createdb`, `pg_restore` or the required roles/extensions are unavailable. This uses only a Cloud Shell scratch database, not BharatKatha production or AYANA:

```bash
command -v initdb && command -v pg_ctl && command -v createdb && command -v pg_restore
initdb -D "$BK_TMP/pgdata" --auth-local=trust --auth-host=reject
pg_ctl -D "$BK_TMP/pgdata" -o "-h '' -k $BK_TMP -p 55439" -l "$BK_TMP/postgres.log" start
createdb -h "$BK_TMP" -p 55439 bk_restore
pg_restore --exit-on-error --single-transaction --no-owner --no-acl \
  -h "$BK_TMP" -p 55439 -d bk_restore "$BK_TMP/downloaded.dump"
psql -X -h "$BK_TMP" -p 55439 -d bk_restore -Atc \
  "SELECT count(*) FROM public.projects"
psql -X -h "$BK_TMP" -p 55439 -d bk_restore -Atc \
  "SELECT column_name || ':' || data_type FROM information_schema.columns WHERE table_schema='public' AND table_name='projects' ORDER BY ordinal_position"
pg_ctl -D "$BK_TMP/pgdata" stop
```

Compare row count and column types with a fresh **read-only** production query taken close to the dump snapshot; concurrent writes can change production counts, so document any difference rather than assuming corruption. Check expected constraints/indexes/triggers/policies from `pg_restore --list`. Capture command exit statuses, SHA-256 and comparisons without row contents. This **table-only archive is a rehearsal safety snapshot, not a full production disaster-recovery backup**; a live migration still needs a verified full backup/restore path or confirmed Supabase PITR. Do not set `BHARATKATHA_BACKUP_VERIFIED=yes` until the restore and comparisons pass. If Cloud Shell cannot run a local server, use an approved isolated restore host; do not restore into the live Supabase database.

## Rehearsal, evidence and cleanup after authorization

Run the create SQL only after the backup restore test and founder authorization. Its post-commit read-only selects must show the copied column types, the two new lease columns, and zero rows. Run the already tested atomic claim cases on **synthetic rows only**, with a connection forced to the rehearsal search path; never point the local-only probe at live `public`. Because `LIKE` does not copy constraints, indexes, triggers or policies, this rehearsal checks migration/type compatibility and the claim SQL, while existing production behavior remains a separate read-only review.

Cleanup is exactly:

```sql
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '30s';
SET LOCAL search_path = pg_catalog;
DROP TABLE bk_lease_rehearsal_20261016.projects;
DROP SCHEMA bk_lease_rehearsal_20261016;
COMMIT;
```

There is no `CASCADE`; unexpected dependencies make cleanup fail safely. Verify `to_regnamespace('bk_lease_rehearsal_20261016') IS NULL` afterward. Save the SQL results, backup hash and restore evidence without passwords or user data in logs.

## Commercial voice licensing review

| Component | Verified primary-source terms | Required before commercial beta |
| --- | --- | --- |
| Piper 1.8.0 runtime | The pinned `v1.8.0` package declares GPL-3.0-or-later. GPL permits commercial use; distributing software may require corresponding source and notices. Piper bundles eSpeak NG. | Preserve exact wheel/source license and notices; have counsel review hosted-only use, container distribution and eSpeak before launch. The Piper voice guide says the project is intended for personal use and TTS research, while also saying it imposes no extra voice restrictions; resolve this wording with the publisher/legal review before commercial beta. |
| Telugu `te_IN-padmavathi-medium` voice | Its model card identifies IndicVoices-R training data under CC BY 4.0; the ONNX hash pinned in this packet is `414aa5960d91ceb6e45bbdf8c27fdc71af09f205130d7be4e99470f3c2cfa57d`. The dataset license alone does not establish all weight, speaker or output rights. | Preserve the exact model card and CC BY credit, license link and change notice where required; clear commercial model/voice/output rights with counsel or publisher before beta. |
| Supertonic 3 model | Pinned revision `aafc6e32416a594460b32413efc49d7fe4ce6d46`, pinned LICENSE SHA-256 `0d944a9110fed9a9602d60e0423a272903e7bd21ab060490774efc77c2275e9f`; OpenRAIL-M permits commercial hosted use subject to Attachment A restrictions. The license defines hosted access as Distribution, requires restrictions to flow to users, and disclaims general output ownership claims. | Include use restrictions in enforceable beta Terms, retain full model LICENSE/notices, and clear the M1 voice/training provenance. Runtime verifies the pinned license hash before loading. |
| Supertonic Python 1.3.1 runtime | MIT. | Include copyright and MIT notice with any distributed software. One cloud installation serves Hindi and English. |

Sources: [Piper v1.8.0 package metadata](https://github.com/OHF-Voice/piper1-gpl/blob/v1.8.0/setup.py), [Piper voice guide](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md), [Piper maintainer](https://github.com/OHF-Voice/piper1-gpl/discussions/30), [Telugu model card commit](https://huggingface.co/rhasspy/piper-voices/commit/ff43c1e79f98a765202dcfb03710851f9ec4ff2e), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), [Supertonic model license](https://huggingface.co/supertone-oss-archive/supertonic-3/blob/main/LICENSE), [Supertonic runtime MIT](https://github.com/supertone-oss-archive/supertonic-py/blob/main/LICENSE). This verifies published license text, not every upstream right or legal compliance. Final commercial clearance remains open.

## First Linux Cloud Build validation, prepared only

The first build is **main API only**, with a unique review tag in the existing `asia-south1` Artifact Registry repository. It creates an image and build logs but deploys no Cloud Run service, creates no GPU and leaves `vidbharat-image-worker` untouched. The build may incur Cloud Build, registry and staging-bucket charges, so it requires explicit build approval.

```bash
# Cloud Shell, from the reviewed source checkout; read only preflight:
gcloud config get-value project
gcloud artifacts repositories describe vidbharat-beta --location=asia-south1 --format='yaml(name,format)'
gcloud meta list-files-for-upload > /tmp/bharatkatha-upload-files.txt
grep -E '(^|/)(\.env|env\.txt|.*credentials.*\.json|.*\.onnx|.*\.mp4)$' /tmp/bharatkatha-upload-files.txt && exit 2

# Run only after explicit approval of one billable build:
REVIEW_TAG="review-api-$(date -u +%Y%m%d-%H%M%S)"
IMAGE="asia-south1-docker.pkg.dev/ayana-video-studio/vidbharat-beta/main-api:${REVIEW_TAG}"
gcloud builds submit . --project=ayana-video-studio --region=asia-south1 \
  --config=deploy/main-api/cloudbuild.yaml --substitutions="_IMAGE=${IMAGE}" --timeout=30m
# Record returned build ID; require SUCCESS and inspect logs/digest before any deployment.
```

For later separate approval of the other three images, use the same reviewed source manifest and immutable `REVIEW_TAG`, then run sequentially, stopping at the first non-`SUCCESS` status:

```bash
for SPEC in 'voice-piper:voice-piper-te' 'voice-supertonic:voice-supertonic-hi' 'render-worker:render-worker'; do
  CONFIG="${SPEC%%:*}"
  NAME="${SPEC##*:}"
  gcloud builds submit . --project=ayana-video-studio --region=asia-south1 \
    --config="deploy/${CONFIG}/cloudbuild.yaml" \
    --substitutions="_IMAGE=asia-south1-docker.pkg.dev/ayana-video-studio/vidbharat-beta/${NAME}:${REVIEW_TAG}" \
    --timeout=30m
done
```

The build files specify a 30-minute timeout too. Default Cloud Build `e2-standard-2` is 2 vCPU/8 GB and the published Mumbai rate is **$0.00624/min**. Gross compute estimates: **$0.125 for one 20-minute build, $0.187 for a full 30-minute timeout; $0.50 for four 20-minute builds, $0.75 if all four time out**. Shared free allowance may reduce the bill, but availability is unverified; Artifact Registry image bytes, staging storage and logs add small variable charges. No build has run and Linux image validity remains unverified. The image worker is not a build target. [Cloud Build CLI](https://cloud.google.com/sdk/gcloud/reference/builds/submit), [default machine](https://docs.cloud.google.com/build/docs/build-config-file-schema), [Mumbai pricing](https://cloud.google.com/build/pricing-update), [gcloudignore](https://docs.cloud.google.com/sdk/gcloud/reference/topic/gcloudignore).

## GO / NO-GO gates

| Gate | Status on 16 October 2026 |
| --- | --- |
| Forward migration excludes rollback; create/cleanup files confined to fixed rehearsal schema | **GO for static preparation:** four local regression tests passed. No SQL executed. |
| BharatKatha backup and isolated restore | **GO for application-data restore evidence:** founder reports seven restored `public` tables, 863 rows and 11 constraints. **Still open:** independent GCS hash, bucket IAM, source count comparison and full Supabase-platform recovery. |
| Actual BharatKatha schema, privileges and Data API isolation | **NO-GO:** read-only catalog/API checks and post-create access checks await approved execution; actual schema creation needs separate explicit authorization. |
| Linux images | **NO-GO:** Cloud Build commands and costs are prepared; no build has run or succeeded. |
| Commercial Telugu and Hindi/English voice clearance | **NO-GO for public beta:** published licenses identified, but Telugu voice/weight rights, Piper hosted-use interpretation, Supertonic M1 provenance and beta Terms remain to clear. |
| Cloud deployment and three-language end-to-end video/download | **NO-GO:** no Cloud Run deployment or remote generation evidence. Existing image worker and Growth Coach remain preserved in the prepared plan. |

**Next approval needed:** authorize only the private backup destination/restore rehearsal and isolated-schema creation after reviewing the exact SQL above. Cloud Build and deployment remain separate billable approvals. No production migration is authorized by this packet.
