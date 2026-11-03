# Data audit and treatment record

## Verified snapshot

Official BTS `Airline_Delay_Cause.csv`, downloaded 3 November 2026. Requested and verified coverage: January 2018–December 2025. The archive's server-provided filename and file SHA-256 hashes are preserved in `data/raw/provenance.json`. No immutable release ID is supplied by BTS. The CSV and downloaded ZIP are unchanged.

- Raw shape: **186,371 rows × 21 columns**.
- Grain: year-month × carrier code × arrival airport code.
- Exact duplicates: **0**. Duplicate business keys: **0**.
- Clean records: **186,049**; 28 carrier codes; 395 airport codes.
- Clean dates: **2018-01-01 through 2025-12-01**, 96 months; global missing months: [].
- Invalid date rows: 0; invalid airport codes: 0; negative numeric fields: 0 values.

## Missingness and decisions

| Field | Raw missing rows |
| --- | --- |
| year | 0 |
| month | 0 |
| carrier | 0 |
| carrier_name | 0 |
| airport | 0 |
| airport_name | 0 |
| arr_flights | 322 |
| arr_del15 | 572 |
| carrier_ct | 322 |
| weather_ct | 322 |
| nas_ct | 322 |
| security_ct | 322 |
| late_aircraft_ct | 322 |
| arr_cancelled | 322 |
| arr_diverted | 322 |
| arr_delay | 322 |
| carrier_delay | 322 |
| weather_delay | 322 |
| nas_delay | 322 |
| security_delay | 322 |
| late_aircraft_delay | 322 |

**Structural zeros:** 250 missing `arr_del15` values are derived as zero only when all recorded flights are cancelled/diverted and every delay-minute/cause counter is explicitly zero. The raw file retains its blanks. This is logical reconciliation, not blanket imputation.

**Exclusions:** 322 records lack required operational quantities or have nonpositive volume and are excluded from the analytical table. Known flight volume in excluded rows is 0; this is not an estimate of unreported flight volume. Exclusion counts by year: {'2018': 28, '2019': 30, '2020': 141, '2021': 37, '2022': 17, '2023': 47, '2024': 16, '2025': 6}. Missingness is profiled by year and carrier in `missingness_segments.csv`; missing rows are not assumed random.

**Names and categories:** trim surrounding whitespace; changes by column: {'carrier': 0, 'carrier_name': 0, 'airport': 0, 'airport_name': 0}. Carrier codes with multiple names: 2; airport codes with multiple names: 33. Preserve legitimate name changes; aggregate by codes rather than splitting by labels. No joins to external datasets are used.

**Logical consistency:** delayed, cancelled and diverted counts cannot exceed total flight volume. Cause-minute sums differ from total minutes in 20 clean records, with a total positive gap of 6,270 minutes. Preserve this discrepancy and display unallocated minutes rather than silently forcing causes to sum to the outcome.

**Outliers:** IQR flags are reported in `outlier_profile.csv`; none are deleted solely for being extreme. Large hubs and disruption months legitimately generate large values. Numeric profiles and categorical cardinalities are recorded in `numeric_profile.csv` and `audit.json`.

**Privacy and leakage:** None in the selected 21-column operational aggregate schema. Same-month delay counts, cause counts/minutes, cancellations and total volume are outcomes, unavailable as predictors before that month. Only exact t-3/t-12 historical features and calendar seasonality enter the model. Carrier/airport labels are used for grouping, not individual profiling.

**Panel gaps:** a globally complete monthly series does not mean every carrier-airport pair appears every month. Missing combinations are not invented as zero flights. Feature joins require exact lag dates; model coverage is reported separately.

## Handling plan

Keep `data/raw/` read-only in normal use. Rerun source hash checks before cleaning. Derive `data/processed/cleaned_delays.csv` deterministically; do not manually edit it. Generated report tables, figures, notebook outputs and the cleaned table can all be rebuilt. Source revisions require a new dated manifest and a full audit.
