# Staging views

These are intentionally empty until the first dlt loads land in Supabase.

Reason: each source's raw column names are only knowable after `pipeline.run()`
creates the tables. Per the plan, you and Claude review the real `shopify_raw.*`,
`google_ads_raw.*`, etc. tables together and align names here — one staging view
per source that renames/casts into the unified contract defined in
`../marts/fct_daily_spend.sql`.

Planned files (created after first loads):
- `stg_shopify_orders.sql`        -> normalized orders + line items
- `stg_shopify_products.sql`      -> catalog + variant unit_cost (COGS)
- `stg_google_spend.sql`          -> into fct_daily_spend contract
- `stg_meta_spend.sql`            -> into fct_daily_spend contract
- `stg_microsoft_spend.sql`       -> into fct_daily_spend contract

Each `stg_*_spend.sql` also parses `landing_page_slug` from the campaign name
using your naming convention (regex on campaign_name), so it joins cleanly to
`ref.map_landing_page_product`.
