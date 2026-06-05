# Manual report exports (interim ads path)

Drop platform CSV exports here, one folder per channel:
- `google/`     — Google Ads report editor export
- `meta/`       — Meta Ads Manager export
- `microsoft/`  — Microsoft Advertising report download

Export rules so `load_csv_reports.py` works cleanly:
- **Daily grain, campaign level.** One row per day per campaign.
- **Same columns every export.** date, campaign id, campaign name, impressions,
  clicks, spend, conversions, conversion value (+ currency for Google).
- Include the final-URL column OR keep campaign names parseable so the
  `landing_page_slug` regex in the loader can extract the product.

The CSVs themselves are gitignored (data, not code). The loader lands them into
Supabase schema `manual_reports.ads_spend_manual`, tagged `source_method='csv_manual'`.
When live API pulls arrive, point the staging views at the API-fed `*_raw` tables
instead — marts and dashboard don't change.
