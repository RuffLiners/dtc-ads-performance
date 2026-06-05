"""
Shopify -> Supabase loader (STEP 1 of the Ruff Liners ads pipeline).

This is the first source we stand up because Shopify is the fastest credential
to get and proves the whole dlt -> Supabase loop before we touch the three
painful ad APIs.

Prereqs (see README):
  1. `dlt init shopify_dlt postgres`   # fetches the verified Shopify source code
  2. `pip install -r requirements.txt`
  3. Fill .env (DESTINATION__POSTGRES__CREDENTIALS + SOURCES__SHOPIFY_DLT__*)

Run:
  python shopify_pipeline.py
"""

import dlt
from shopify_dlt import shopify_source  # provided by `dlt init shopify_dlt postgres`

# Pull from the start of last year so we have history for trend reporting.
# Incremental state is stored in the destination, so subsequent runs only fetch
# new/changed records — this start_date only matters on the very first run.
START_DATE = "2024-01-01"


def load_shopify() -> None:
    pipeline = dlt.pipeline(
        pipeline_name="ruff_liners_shopify",
        destination="postgres",
        dataset_name="shopify_raw",  # lands as schema "shopify_raw" in Supabase
        progress="log",
    )

    # Resources we care about for marketing + product-level profit reporting.
    # orders -> revenue and line items (product-level); products -> catalog +
    # variant unit cost (COGS); customers -> for LTV/repeat later.
    source = shopify_source(start_date=START_DATE).with_resources(
        "orders",
        "products",
        "customers",
    )

    load_info = pipeline.run(source)
    print(load_info)


if __name__ == "__main__":
    load_shopify()
