# Ruff Liners Ads Pipeline (dlt → Supabase)

Pulls Meta Ads, Google Ads, Microsoft Ads, and Shopify into your own Supabase,
normalizes into unified marts, and feeds the Vercel dashboard + (later) Claude
analyst agents. You own the warehouse and the semantic layer.

```
dlt (this repo, runs on GitHub Actions)
   → Supabase: <source>_raw schemas      (raw, dlt-managed)
   → Supabase: staging.*  (rename/cast, you + Claude align after first load)
   → Supabase: marts.*    (fct_daily_spend, fct_product_profit — dashboard reads these)
   ↑ ref.* mapping tables you own (landing_page→product, targets)
Vercel/Next.js dashboard reads marts.*
Claude agents (Mac Mini, later) query Supabase via Postgres MCP
```

---

## Order of operations (by lead time — do step 1 TODAY)

### 1. Apply for the Google Ads developer token  ← DAY 0, it's the long pole
This has an approval process (basic→standard access) that can take days to weeks,
so it gates the whole Google piece. Start the clock now even though we load
Google last.
- Google Ads UI → Tools → **API Center** (must be on a **manager/MCC** account; if
  you only have a single account, create a manager account and link it).
- Request a developer token. It works in *test* mode immediately; *basic access*
  (needed for your real account) requires the approval form. Fill it out today.

### 2. Shopify custom app token  ← also today, this is your first working loop
- Shopify admin → **Settings → Apps and sales channels → Develop apps → Create an app**.
- Configure **Admin API scopes**: at minimum `read_orders`, `read_products`,
  `read_customers`. (For >60 days of order history you may need
  `read_all_orders`, requested via the app's API access section.)
- Install the app → copy the **Admin API access token** (`shpat_...`).
- Make sure your product variants have **Cost per item** filled in (Shopify →
  product → variant → Cost per item) — that's your COGS for profit reporting. If
  some are blank we'll maintain a small cost table instead.

### 3. Stand up the pipeline + prove the Shopify loop
```bash
cd ruff-liners-ads-pipeline
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Fetch the verified Shopify source code into this repo:
dlt init shopify_dlt postgres
pip install -r requirements.txt        # picks up the source's own deps

cp .env.example .env                    # then fill DESTINATION + SHOPIFY vars
set -a; source .env; set +a             # export env vars for dlt

python shopify_pipeline.py
```
Check Supabase → you should see a `shopify_raw` schema with `orders`,
`products`, `customers` (and child tables like `orders__line_items`).
**This is the milestone: data you own, in your warehouse, on your terms.**

Then commit the fetched `shopify_dlt/` folder so CI doesn't have to fetch it, and
add the GitHub repo Secrets matching the names in `.env.example`. The workflow in
`.github/workflows/sync-shopify.yml` runs it daily.

### 4. Add the three ad sources (after Shopify works)
```bash
dlt init facebook_ads postgres      # Meta
dlt init google_ads postgres        # Google
```
- **Meta**: create a Meta app, add a **System User** in Business Settings, generate
  a long-lived token with `ads_read`, assign the ad account. Business verification
  may be required. Account id goes in WITHOUT the `act_` prefix.
- **Google**: once the dev token is approved, generate OAuth client + refresh token
  (offline access, `https://www.googleapis.com/auth/adwords` scope). Customer id is
  the 10-digit number, no dashes.
- **Microsoft (4c)**: dlt may not ship a verified Bing/Microsoft Ads source — verify
  the current catalog at dlthub.com. If absent, it's a small custom dlt source over
  the Microsoft Advertising Reporting API (submit report → poll → download CSV).
  Claude will write that source when we get here.

Each ad source lands in its own `*_raw` schema. Then we write the `staging/`
views together against the real columns and union into `marts.fct_daily_spend`.

### 5. Reference tables + marts (in Supabase SQL editor)
```sql
\i sql/seed/01_map_landing_page_product.sql   -- then fill your 13 SKUs + bundles
\i sql/seed/02_targets.sql                     -- then insert your monthly goals
-- staging/* and marts/* finalized after first loads (column names confirmed)
```

### 6. Dashboard (Next.js/Vercel) — reads marts.* only
### 7. Agent layer (Mac Mini) — Postgres MCP over Supabase, one analyst agent first

---

## Why these choices
- **dlt, not Fivetran/Airbyte**: keeps ownership (the reason you dropped Windsor),
  no new monthly bill, lives in code you run.
- **GitHub Actions, not your PC/Mac Mini**: free, scheduled, always available;
  keeps the Mac Mini free for the always-on agent/MCP workload.
- **SQL views, not dbt**: right-sized for your volume; folder convention makes a
  later dbt migration mechanical if you ever need it.
- **Landing-page→product mapping**: campaign naming convention → landing page →
  product; one small table you curate. Final-URL cross-check addable later.
