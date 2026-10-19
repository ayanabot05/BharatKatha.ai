-- Billing, usage quota, payments and the admin audit trail.
-- Idempotent: safe to run more than once. Apply with backend-only credentials:
--     python migrate.py
-- Every statement uses IF NOT EXISTS so a partially applied run can be repeated.
--
-- Until this is applied the app still works: billing_store falls back to reading
-- the plan from users.plan and counting usage from completed project rows.
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '30s';
SET LOCAL search_path = pg_catalog;

-- One row per user: their current entitlement.
CREATE TABLE IF NOT EXISTS public.subscriptions (
    user_id text PRIMARY KEY,
    plan text NOT NULL DEFAULT 'free',
    status text NOT NULL DEFAULT 'active',      -- active | past_due | cancelled | expired
    provider text NOT NULL DEFAULT '',          -- razorpay | dodo
    currency text NOT NULL DEFAULT 'USD',
    interval text NOT NULL DEFAULT 'month',     -- month | year
    provider_customer_id text,
    provider_subscription_id text,
    current_period_end timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS subscriptions_plan_status_idx ON public.subscriptions(plan, status);
CREATE UNIQUE INDEX IF NOT EXISTS subscriptions_provider_sub_idx
    ON public.subscriptions(provider, provider_subscription_id)
    WHERE provider_subscription_id IS NOT NULL;

-- Video usage counter: one row per user per quota window.
CREATE TABLE IF NOT EXISTS public.render_usage (
    user_id text NOT NULL,
    period_key text NOT NULL,
    used integer NOT NULL DEFAULT 0,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, period_key)
);

-- Every checkout attempt and its outcome. Powers the admin dashboard and receipts.
CREATE TABLE IF NOT EXISTS public.payments (
    id text PRIMARY KEY,
    user_id text,
    email text,
    provider text NOT NULL DEFAULT '',
    provider_payment_id text,
    provider_order_id text,
    plan text NOT NULL DEFAULT '',
    interval text NOT NULL DEFAULT 'month',
    currency text NOT NULL DEFAULT 'USD',
    amount integer NOT NULL DEFAULT 0,          -- minor units (paise / cents)
    status text NOT NULL DEFAULT 'created',     -- created | paid | failed | refunded
    raw jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS payments_user_created_idx ON public.payments(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS payments_status_created_idx ON public.payments(status, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS payments_provider_id_idx
    ON public.payments(provider, provider_payment_id)
    WHERE provider_payment_id IS NOT NULL;

-- Webhook idempotency: a provider event must be applied at most once.
CREATE TABLE IF NOT EXISTS public.billing_events (
    provider text NOT NULL,
    event_id text NOT NULL,
    event_type text,
    received_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (provider, event_id)
);

-- Admin actions, so plan changes and refunds are accountable.
CREATE TABLE IF NOT EXISTS public.admin_audit (
    id text PRIMARY KEY,
    admin_id text,
    action text NOT NULL,
    target_user_id text,
    detail jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS admin_audit_created_idx ON public.admin_audit(created_at DESC);

ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.render_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.billing_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_audit ENABLE ROW LEVEL SECURITY;
-- No public policies: only the backend's privileged connection may access these.
COMMIT;
