-- =============================================================================
-- map_landing_page_product
-- The join that allocates ad spend to products. You own and curate this.
-- One row per landing page. ~13 products plus any bundles/collections.
--
-- How it's used: each campaign points to a landing page (via your naming
-- convention). We parse the landing-page slug from the campaign name (and later
-- can cross-check against the platform's stored final URL), then join here to
-- attribute that campaign's spend to a product.
-- =============================================================================

create schema if not exists ref;

create table if not exists ref.map_landing_page_product (
    landing_page_slug   text primary key,          -- e.g. 'back-seat-extender'
    landing_page_url    text,                       -- full URL, optional ground-truth cross-check
    product_id          text not null,              -- your internal/Shopify product id
    product_name        text not null,              -- 'Back Seat Extender'
    product_type        text,                        -- 'core' | 'bundle' | 'collection'
    notes               text,
    updated_at          timestamptz default now()
);

-- ---- SEED TEMPLATE (replace with your real 13 SKUs + bundles) ----------------
-- insert into ref.map_landing_page_product
--   (landing_page_slug, landing_page_url, product_id, product_name, product_type)
-- values
--   ('back-seat-extender', 'https://ruff-liners.com/products/back-seat-extender', 'PROD_BSE', 'Back Seat Extender', 'core'),
--   ('xl-floor-cover',     'https://ruff-liners.com/products/xl-floor-cover',     'PROD_XLF', 'XL Floor Cover',     'core'),
--   ('travel-dog-bed',     'https://ruff-liners.com/products/travel-dog-bed',     'PROD_TDB', 'Travel Dog Bed',     'core'),
--   ('hammock',            'https://ruff-liners.com/products/hammock',            'PROD_HAM', 'Hammock',            'core')
-- on conflict (landing_page_slug) do update set
--   landing_page_url = excluded.landing_page_url,
--   product_id       = excluded.product_id,
--   product_name     = excluded.product_name,
--   product_type     = excluded.product_type,
--   updated_at       = now();
