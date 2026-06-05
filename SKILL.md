---
name: ruff-liners-ads-pipeline
description: Full architecture, decisions, and build plan for the Ruff Liners multi-channel ads + Shopify reporting pipeline (dlt → Supabase → marts → Vercel dashboard → Claude agents). Use this skill whenever Brandon or Claude Code is working on the ads/reporting data pipeline, the Supabase warehouse, the unified spend/profit marts, the landing-page→product mapping, the CSV interim ad-report loader, the reporting dashboard, or the analyst-agent layer — even if the request only mentions one piece (e.g. "add the Meta source", "fix the spend numbers", "build the profit view", "set up the dashboard"). This is the source of truth for why the pipeline is built the way it is; consult it before changing architecture, schema, or sequencing so changes stay consistent with the locked decisions.
---

# Ruff Liners Ads + Shopify Reporting Pipeline

## What this is

A pipeline that pulls **Meta Ads, Google Ads, Microsoft Ads, and Shopify** into a
Supabase warehouse Brandon owns, normalizes four incompatible schemas into a single
set of marts, feeds a Next.js/Vercel dashboard for daily/weekly/monthly performance
and product-level profit reporting, and (later) lets Claude analyst agents reason
across the data toward goals.

Core principle behind every decision: **Brandon owns the warehouse and the semantic
layer.** He dropped Windsor.ai (a rented aggregator) specifically to stop renting his
data and schema. Don't reintroduce a walled-garden tool that takes that back.

## Architecture (the full flow)

```
dlt (Python, runs on GitHub Actions)
   → Supabase: <source>_raw schemas        raw, dlt-managed (shopify_raw, google_ads_raw, ...)
   → Supabase: staging.*                    rename/cast into the unified contract
   → Supabase: marts.*                       fct_daily_spend, fct_product_profit  (dashboard reads these)
   ↑ Supabase: ref.*                          mapping tables Brandon owns (map_landing_page_product, targets)
Vercel / Next.js dashboard  →  reads marts.* ONLY
Claude analyst agents (Mac Mini, later)  →  query Supabase via a Postgres MCP
```

The repo lives at GitHub `RuffLiners` and locally as `ruff-liners-ads-pipeline/`.

## Locked decisions (and why — don't silently reverse these)

- **dlt, not Fivetran / Airbyte / Triple Whale / Windsor.** Keeps ownership, no new
  monthly bill, lives in code Brandon runs. Fivetran is objectively the easiest button,
  but ownership is the priority that overrides "easiest."
- **Ingestion via API/dlt; analysis via MCP.** MCP is the *analysis layer on top of the
  warehouse* (agents querying Supabase), NOT the ingestion transport. Never point the
  dashboard or ETL at an MCP. This mirrors how Brandon already uses the Euka MCP.
- **GitHub Actions runs the syncs.** Free, scheduled, always available. NOT his PC (not
  always on) and NOT the Mac Mini — the Mac Mini is reserved for the always-on agent/MCP
  workload later. dlt stores incremental state in the destination, so ephemeral CI runners
  are fine.
- **Plain SQL views for the marts, not dbt.** Right-sized for the volume (one account per
  platform, ~13 SKUs, daily grain — thousands of rows, not millions). The `staging/` →
  `marts/` folder convention makes a later dbt migration mechanical if volume ever grows.
  Use materialized views refreshed at the end of each sync (pg_cron or pipeline last step)
  for dashboard-facing marts so reads are fast.
- **Landing-page → product is the spend-allocation join.** Brandon assigns a landing page
  per campaign via a standard naming convention. Parse `landing_page_slug` from the campaign
  name, join to `ref.map_landing_page_product`. The platform's stored final-URL is ground
  truth that can be added later as a cross-check; start with name-parsing because it matches
  his plan and is simplest.
- **CSV-first for ads, swap to live pulls at the staging seam.** While the Google dev token
  approval is pending (weeks) and Meta/Microsoft auth is set up, load manual CSV exports into
  the SAME `marts.fct_daily_spend` contract. When live pulls arrive, point staging at the
  API-fed `*_raw` tables — marts and dashboard never change. This is sequencing, not a
  compromise: it gets a working dashboard in days instead of weeks.
- **Agents last, but build for them.** Don't build OpenClaw's nine agents before clean data
  flows. Prove one analyst agent (Claude Code + Postgres MCP over Supabase) against clean
  marts first, then expand. Encode goals as data (`ref.targets`) so an agent can measure
  "on pace vs target," not guess.

## Data model

**Raw** (`*_raw`, dlt-managed): leave as-is, dlt owns these.

**Staging** (`staging.*`): one view per source that renames/casts raw columns into the
unified contract. **Do NOT fabricate these schemas — finalize them against the REAL columns
after the first load lands** (this is Brandon's explicit ask: align names against actual
tables together). Each `stg_*_spend` view also parses `landing_page_slug` from the campaign
name so it joins to the mapping table.

**Marts** (`marts.*`) — the contract the dashboard and agents read:
- `fct_daily_spend` — one row per `day × channel × campaign × landing_page`. Normalized
  columns: `day, channel, campaign_id, campaign_name, landing_page_slug, impressions, clicks,
  spend, conversions, conv_value, currency`. Each platform names these differently
  (Google `cost_micros`/1e6, Meta `spend`, Microsoft `Spend`) — normalization is the whole
  game; if numbers don't tie out, suspect a join fan-out or an attribution-window/currency/
  timezone mismatch first.
- `fct_daily_spend_by_product` — `fct_daily_spend` joined to `ref.map_landing_page_product`.
- `fct_product_profit` — revenue (Shopify line items) − COGS (Shopify variant unit cost;
  Brandon inputs these) − allocated ad spend − optional fees.

**Reference** (`ref.*`, Brandon owns):
- `map_landing_page_product` — `landing_page_slug → product`. ~13 SKUs + bundles.
- `targets` — long format: one row per `(period, scope, metric)`; scope is store/channel/product.

## Build sequence (ordered by credential lead time — see repo README)

1. **Google Ads developer token** — DAY 0, the long pole (days-to-weeks approval). Requires a
   manager/MCC account; a bare single account can't get API access — create + link an MCC if
   needed. Apply even though Google loads last.
2. **Shopify custom app token** — also day 0; the first working loop. Scopes `read_orders`,
   `read_products`, `read_customers`. Fill variant "Cost per item" (COGS) — Brandon inputs these.
3. **Prove the Shopify loop** — `dlt init shopify_dlt postgres`, fill `.env`, run
   `shopify_pipeline.py`, verify `shopify_raw` appears in Supabase. Milestone: owned data in the
   warehouse. THEN write Shopify staging views against the real columns with Brandon.
4. **Add ad sources** — `dlt init facebook_ads postgres` (Meta system-user token, `ads_read`,
   account id without `act_`), `dlt init google_ads postgres` (after token approved; OAuth
   refresh token, 10-digit customer id). Microsoft Advertising likely has NO verified dlt source —
   verify catalog at dlthub.com; if absent, write a small custom dlt source over the Microsoft
   Reporting API (submit report → poll → download CSV). In parallel, run the CSV interim path.
5. **Reference tables + marts** — run `sql/seed/*`, fill the 13 SKUs and monthly targets,
   finalize `staging/*` and `marts/*` against real columns.
6. **Dashboard** (Next.js/Vercel) — reads `marts.*` only.
7. **Agent layer** (Mac Mini) — Postgres MCP over Supabase, one analyst agent first.

## Repo files

- `shopify_pipeline.py` — step-3 Shopify loader (orders, products, customers).
- `load_csv_reports.py` — interim ad-report loader; per-channel `COLUMN_MAPS` map export headers
  to the contract; lands `manual_reports.ads_spend_manual` tagged `source_method='csv_manual'`.
  Verify the maps against Brandon's real exports (Google/Meta/Microsoft label columns differently).
- `report_imports/<channel>/` — drop CSV exports here (gitignored; daily grain, campaign level,
  same columns each export).
- `sql/seed/01_map_landing_page_product.sql`, `sql/seed/02_targets.sql` — the ref tables.
- `sql/marts/fct_daily_spend.sql`, `sql/marts/fct_product_profit.sql` — target schemas (documented;
  SELECT bodies finalized after first loads).
- `sql/staging/README.md` — staging views are deliberately deferred until real columns are known.
- `.github/workflows/sync-shopify.yml` — daily scheduled sync.
- `.env.example` / `.gitignore` — credential names (dlt double-underscore env nesting); secrets never committed.

## Working with Brandon

Direct, numbers-driven, no filler. He corrects analytical framing when business context is
misread and iterates quickly until behavior matches exactly. He's API-first and automation-forward,
uses Claude as a technical collaborator, and prefers owning tooling over renting it. Surface the
human-only steps (credentials, MCC setup, COGS entry, campaign-naming discipline) as clear, ordered
checklists — those are the real bottlenecks; the code is the easy part.
