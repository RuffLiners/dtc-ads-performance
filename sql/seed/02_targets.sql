-- =============================================================================
-- targets
-- Goals the dashboard tracks and (later) agents reason toward. Encoding targets
-- as data — not prose — is what lets an agent measure "are we on pace" instead
-- of guessing. Mirrors how your MTD tracker and bonus programs already work.
--
-- Flexible long format: one row per (period, scope, metric). Scope lets you set
-- a store-wide target OR a per-channel OR per-product target with the same table.
-- =============================================================================

create schema if not exists ref;

create table if not exists ref.targets (
    target_id     bigint generated always as identity primary key,
    period_type   text not null,        -- 'month' | 'week' | 'quarter'
    period_start  date not null,         -- first day of the period
    scope_type    text not null,         -- 'store' | 'channel' | 'product'
    scope_value   text,                   -- null for store; 'google' / 'meta' / etc; or product_id
    metric        text not null,          -- 'revenue' | 'spend' | 'roas' | 'profit' | 'orders'
    target_value  numeric not null,
    notes         text,
    updated_at    timestamptz default now(),
    unique (period_type, period_start, scope_type, scope_value, metric)
);

-- ---- EXAMPLES ----------------------------------------------------------------
-- insert into ref.targets (period_type, period_start, scope_type, scope_value, metric, target_value) values
--   ('month','2026-06-01','store',  null,    'revenue', 250000),
--   ('month','2026-06-01','channel','google','roas',    4.0),
--   ('month','2026-06-01','product','PROD_BSE','profit', 30000);
