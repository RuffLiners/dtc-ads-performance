"""
Manual ad-report loader (INTERIM ads path).

Loads CSV exports from Google / Meta / Microsoft Ads into the SAME unified
contract as live API pulls, so the dashboard works before the Google developer
token is approved and Meta/Microsoft auth is set up. When live dlt pulls arrive,
you retire this path — the marts and dashboard never change.

Folder layout (CSVs are gitignored; this is data, not code):
  report_imports/google/*.csv
  report_imports/meta/*.csv
  report_imports/microsoft/*.csv

Export each report at DAILY grain, CAMPAIGN level, with the same columns every
time. Then verify the COLUMN_MAPS below against your actual export headers.

Run:
  python load_csv_reports.py
"""

import glob
import os
import re
from datetime import datetime, timezone

import dlt
import pandas as pd

# The unified contract — must match sql/marts/fct_daily_spend.sql
CONTRACT = [
    "day", "channel", "campaign_id", "campaign_name", "landing_page_slug",
    "impressions", "clicks", "spend", "conversions", "conv_value", "currency",
]

# Map each platform's EXPORT HEADER -> contract column.
# These are typical names — CONFIRM against your real exports and adjust.
COLUMN_MAPS = {
    "google": {
        "Day": "day",
        "Campaign ID": "campaign_id",
        "Campaign": "campaign_name",
        "Impr.": "impressions",
        "Clicks": "clicks",
        "Cost": "spend",                 # Google UI exports Cost already in currency units
        "Conversions": "conversions",
        "Conv. value": "conv_value",
        "Currency code": "currency",
    },
    "meta": {
        "Day": "day",
        "Campaign ID": "campaign_id",
        "Campaign name": "campaign_name",
        "Impressions": "impressions",
        "Link clicks": "clicks",
        "Amount spent (USD)": "spend",
        "Results": "conversions",
        "Purchases conversion value": "conv_value",
    },
    "microsoft": {
        "GregorianDate": "day",
        "CampaignId": "campaign_id",
        "CampaignName": "campaign_name",
        "Impressions": "impressions",
        "Clicks": "clicks",
        "Spend": "spend",
        "Conversions": "conversions",
        "Revenue": "conv_value",
    },
}

# Parse the landing-page slug from the campaign name using your naming convention.
# EXAMPLE: campaign "GG_SEARCH_back-seat-extender_US" -> "back-seat-extender".
# Adjust this regex to match how you actually name campaigns.
SLUG_RE = re.compile(r"(back-seat-extender|xl-floor-cover|travel-dog-bed|hammock)")


def parse_slug(campaign_name: str) -> str | None:
    if not isinstance(campaign_name, str):
        return None
    m = SLUG_RE.search(campaign_name.lower())
    return m.group(1) if m else None


def load_channel(channel: str) -> list[dict]:
    files = glob.glob(f"report_imports/{channel}/*.csv")
    if not files:
        return []
    colmap = COLUMN_MAPS[channel]
    rows: list[dict] = []
    for path in files:
        df = pd.read_csv(path)
        df = df.rename(columns=colmap)
        df["channel"] = channel
        if "currency" not in df.columns:
            df["currency"] = "USD"
        df["landing_page_slug"] = df["campaign_name"].apply(parse_slug)
        # keep only contract columns that exist; fill missing with None
        for col in CONTRACT:
            if col not in df.columns:
                df[col] = None
        df = df[CONTRACT]
        df["day"] = pd.to_datetime(df["day"]).dt.date.astype(str)
        rows.extend(df.to_dict(orient="records"))
    return rows


def main() -> None:
    all_rows: list[dict] = []
    for channel in COLUMN_MAPS:
        ch_rows = load_channel(channel)
        print(f"{channel}: {len(ch_rows)} rows")
        all_rows.extend(ch_rows)

    if not all_rows:
        print("No CSVs found under report_imports/<channel>/. Nothing to load.")
        return

    loaded_at = datetime.now(timezone.utc).isoformat()
    for r in all_rows:
        r["source_method"] = "csv_manual"   # provenance vs live 'api' later
        r["loaded_at"] = loaded_at

    pipeline = dlt.pipeline(
        pipeline_name="ruff_liners_manual_reports",
        destination="postgres",
        dataset_name="manual_reports",      # schema "manual_reports" in Supabase
        progress="log",
    )
    # write_disposition merge would need a primary key; for manual reports we
    # replace the table each run so re-exports overwrite cleanly.
    load_info = pipeline.run(
        all_rows, table_name="ads_spend_manual", write_disposition="replace"
    )
    print(load_info)


if __name__ == "__main__":
    main()
