-- 004: isolated administrator credentials, password resets, early-access
-- signups and first-party product analytics.
--
-- Idempotent on purpose: migrate.py re-runs every forward migration on each
-- invocation, so every statement must be safe to repeat.
--
-- Apply with:  cd backend && python migrate.py

-- --------------------------------------------------------------- admins
-- An administrator is NOT a row in `users`. The credential store is separate
-- so that no user-facing code path (signup, plan changes, role columns) can
-- ever grant administrative access. Authorization reads only this table.
CREATE TABLE IF NOT EXISTS admin_credentials (
  id                  TEXT PRIMARY KEY,
  email               TEXT UNIQUE NOT NULL,
  password_hash       TEXT NOT NULL,
  name                TEXT NOT NULL DEFAULT 'Administrator',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  password_changed_at TIMESTAMPTZ,
  last_login_at       TIMESTAMPTZ
);

-- Retire the previous role-based admin model. This does not delete any account
-- or any project; it only removes an admin role that no longer grants anything.
-- The account keeps working as a normal user account.
UPDATE users SET role = 'user' WHERE role = 'admin';

-- --------------------------------------------------------------- password resets
-- Only a SHA-256 hash of the reset token is stored, so a database leak cannot
-- be replayed to take over an account.
CREATE TABLE IF NOT EXISTS password_resets (
  token_hash TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  used_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS password_resets_user_idx ON password_resets (user_id);

-- --------------------------------------------------------------- early access
-- "Notify me" captures for features that are honestly not live yet
-- (full AI video motion). One row per person per topic.
CREATE TABLE IF NOT EXISTS notify_signups (
  id         TEXT PRIMARY KEY,
  email      TEXT NOT NULL,
  topic      TEXT NOT NULL DEFAULT 'ai_motion',
  source     TEXT NOT NULL DEFAULT '',
  note       TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (email, topic)
);

-- --------------------------------------------------------------- analytics
-- First-party, server-side funnel events. No third-party scripts, no cookies
-- from other companies: the data stays in this database.
CREATE TABLE IF NOT EXISTS growth_events (
  id         BIGSERIAL PRIMARY KEY,
  user_id    TEXT,
  session_id TEXT NOT NULL DEFAULT '',
  name       TEXT NOT NULL,
  props      JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS growth_events_name_idx ON growth_events (name, created_at DESC);
CREATE INDEX IF NOT EXISTS growth_events_user_idx ON growth_events (user_id);
