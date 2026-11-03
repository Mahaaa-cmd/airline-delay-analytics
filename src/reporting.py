"""Generate evidence-linked narrative reports from calculated results."""
from pathlib import Path
import base64
import html
import json
import mistune

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'


def markdown_table(rows):
    header, *body = rows
    return '\n'.join(['| '+' | '.join(map(str, header))+' |',
                      '| '+' | '.join(['---']*len(header))+' |',
                      *['| '+' | '.join(map(str, row))+' |' for row in body]])


def write_reports(audit, metrics, test, tables, prediction_metrics, prediction_design, forecast_metrics, forecast_design):
    pm = prediction_metrics[prediction_metrics.weighting.str.startswith('target')].set_index('model')
    candidate_error = pm.loc['Gradient boosting candidate', 'mae_pp']
    baseline_error = pm.loc['Seasonal lag-12 baseline', 'mae_pp']
    prediction_winner = 'gradient boosting candidate' if candidate_error < baseline_error else 'seasonal lag-12 baseline'
    fm = forecast_metrics.set_index('model')
    forecast_winner = 'ETS candidate' if fm.loc['ETS candidate', 'rmse_pp'] < fm.loc['Seasonal naive', 'rmse_pp'] else 'seasonal naive baseline'
    priority = tables['carrier_airport'].query('arr_flights >= 10000').sort_values('arr_del15', ascending=False).head(10)
    priority.to_csv(REPORTS / 'priority_segments_all_years.csv')
    audit_text = f'''# Data audit and treatment record

## Verified snapshot

Official BTS `Airline_Delay_Cause.csv`, downloaded 3 November 2026. Requested and verified coverage: January 2018–December 2025. The archive's server-provided filename and file SHA-256 hashes are preserved in `data/raw/provenance.json`. No immutable release ID is supplied by BTS. The CSV and downloaded ZIP are unchanged.

- Raw shape: **{audit['raw_rows']:,} rows × {audit['raw_columns']} columns**.
- Grain: year-month × carrier code × arrival airport code.
- Exact duplicates: **{audit['exact_duplicates']}**. Duplicate business keys: **{audit['business_key_duplicates']}**.
- Clean records: **{audit['clean_rows']:,}**; {audit['carriers']} carrier codes; {audit['airports']} airport codes.
- Clean dates: **{audit['date_min']} through {audit['date_max']}**, {audit['observed_months']} months; global missing months: {audit['global_missing_months']}.
- Invalid date rows: {audit['invalid_date_rows']}; invalid airport codes: {audit['invalid_airport_codes']}; negative numeric fields: {sum(audit['negative_by_field'].values())} values.

## Missingness and decisions

{markdown_table([['Field', 'Raw missing rows'], *[[k, v] for k, v in audit['missing_by_field'].items()]])}

**Structural zeros:** {audit['structural_zero_delayed_count_rows']} missing `arr_del15` values are derived as zero only when all recorded flights are cancelled/diverted and every delay-minute/cause counter is explicitly zero. The raw file retains its blanks. This is logical reconciliation, not blanket imputation.

**Exclusions:** {audit['excluded_rows_missing_or_nonpositive_volume']} records lack required operational quantities or have nonpositive volume and are excluded from the analytical table. Known flight volume in excluded rows is {audit['excluded_known_flight_volume']:,.0f}; this is not an estimate of unreported flight volume. Exclusion counts by year: {audit['excluded_by_year']}. Missingness is profiled by year and carrier in `missingness_segments.csv`; missing rows are not assumed random.

**Names and categories:** trim surrounding whitespace; changes by column: {audit['trimmed_strings']}. Carrier codes with multiple names: {audit['carrier_codes_with_multiple_names']}; airport codes with multiple names: {audit['airport_codes_with_multiple_names']}. Preserve legitimate name changes; aggregate by codes rather than splitting by labels. No joins to external datasets are used.

**Logical consistency:** delayed, cancelled and diverted counts cannot exceed total flight volume. Cause-minute sums differ from total minutes in {audit['rows_cause_minutes_not_reconciled']} clean records, with a total positive gap of {audit['unallocated_delay_minutes']:,.0f} minutes. Preserve this discrepancy and display unallocated minutes rather than silently forcing causes to sum to the outcome.

**Outliers:** IQR flags are reported in `outlier_profile.csv`; none are deleted solely for being extreme. Large hubs and disruption months legitimately generate large values. Numeric profiles and categorical cardinalities are recorded in `numeric_profile.csv` and `audit.json`.

**Privacy and leakage:** {audit['personal_fields']} Same-month delay counts, cause counts/minutes, cancellations and total volume are outcomes, unavailable as predictors before that month. Only exact t-3/t-12 historical features and calendar seasonality enter the model. Carrier/airport labels are used for grouping, not individual profiling.

**Panel gaps:** a globally complete monthly series does not mean every carrier-airport pair appears every month. Missing combinations are not invented as zero flights. Feature joins require exact lag dates; model coverage is reported separately.

## Handling plan

Keep `data/raw/` read-only in normal use. Rerun source hash checks before cleaning. Derive `data/processed/cleaned_delays.csv` deterministically; do not manually edit it. Generated report tables, figures, notebook outputs and the cleaned table can all be rebuilt. Source revisions require a new dated manifest and a full audit.
'''
    (REPORTS / 'audit.md').write_text(audit_text)
    statistical_decision = 'Reject the zero-difference null at alpha 0.05' if test['p_value'] < .05 else 'Fail to reject the zero-difference null at alpha 0.05'
    findings = f'''# Airline operations: executive findings

## Scope and decision

Use official BTS monthly operational aggregates to prioritize delay investigations. Historical coverage: **January 2018–December 2025**; **{audit['clean_rows']:,} usable carrier-airport-month records**. Figures describe the downloaded US domestic reporting scope, not all aviation worldwide. Passenger satisfaction, route origins and individual aircraft are absent and are not inferred.

## Performance snapshot

{markdown_table([['Metric', 'Calculated value', 'Denominator / unit'],
['Reported flights', f"{metrics['reported_flights']:,.0f}", 'Sum of arr_flights'],
['Late-arrival share', f"{metrics['late_arrival_pct']:.2f}%", 'arr_del15 / reported flights'],
['Cancellation share', f"{metrics['cancellation_pct']:.2f}%", 'cancelled / reported flights'],
['Diversion share', f"{metrics['diversion_pct']:.2f}%", 'diverted / reported flights'],
['Minutes per delayed arrival', f"{metrics['minutes_per_delayed_arrival']:.2f}", 'total recorded delay minutes / delayed arrivals']])}

Rates are ratios of summed counts. Missing operational records are excluded with a documented audit; the observed totals do not quantify their unknown flight volume.

## Statistical evidence: summer versus autumn

Compare June–August with September–November during **2023–2025** at the **30 largest airports selected using 2018–2022 volume**. Aggregate flights within each airport-season, then give each airport equal weight. The result addresses the typical selected airport, not the typical flight.

Null: the mean paired airport difference is zero. Alternative: a difference in either direction. Method: paired t-test; alpha = 0.05. The observed summer-minus-autumn difference is **{test['difference_pp']:.2f} percentage points**, 95% CI **[{test['ci_low_pp']:.2f}, {test['ci_high_pp']:.2f}]**, **p = {test['p_value']:.3g}**, paired Cohen dz = **{test['paired_cohen_dz']:.2f}**. {statistical_decision}. **{test['positive_difference_airports']} of {test['paired_airports']}** airports have a positive difference.

The project uses 2 percentage points as an explicit practical planning threshold; the measured mean difference is {'above' if abs(test['difference_pp']) >= 2 else 'below'} this threshold. It is a study rule, not an established industry standard. Shapiro-Wilk p for paired differences = {test['shapiro_difference_p']:.3g}; review the Q-Q plot rather than treating this as proof of normality. Sign-flip sensitivity p = {test['signflip_sensitivity_p']:.3g} (20,000 seeded resamples; symmetry/independence assumptions still apply).

Airports share network and weather shocks. The top-airport sample is purposive, not a random national sample. The test is exploratory and does not establish that season itself causes delay or that the same difference will recur.

## Prediction: honest later-year comparison

Target: a **monthly carrier-airport late-arrival share**, predicted at the start of the month. This is aggregate regression, not individual flight classification. Train through September 2023, select the candidate configuration on January–September 2024, refit through September 2024, then evaluate on 2025. All fitting/selection labels are available before the January 2025 test origin under the conservative publication-gap assumption. Features contain exact t-3 and t-12 historical quantities and known calendar seasonality; current-month operational fields never enter the model. Test features update on a rolling basis with three-month-old information, while model coefficients remain fixed.

{markdown_table([['2025 model', 'Flight-weighted MAE (pp)', 'Flight-weighted RMSE (pp)'],
['Seasonal lag-12 baseline', f"{baseline_error:.3f}", f"{pm.loc['Seasonal lag-12 baseline', 'rmse_pp']:.3f}"],
['Gradient boosting candidate', f"{candidate_error:.3f}", f"{pm.loc['Gradient boosting candidate', 'rmse_pp']:.3f}"]])}

The lower flight-weighted MAE belongs to the **{prediction_winner}**. Candidate relative MAE change versus baseline: **{100*(baseline_error-candidate_error)/baseline_error:.1f}% reduction** (negative means deterioration). Report equal-row metrics alongside volume-weighted metrics in `prediction_metrics.csv` so large airports do not hide small-segment errors. Coverage: **{prediction_design['test_rows']:,} test records**, **{prediction_design['test_row_coverage_pct']:.1f}% of 2025 clean rows** and **{prediction_design['test_flight_coverage_pct']:.1f}% of 2025 clean flight volume**. Segments without the required history are excluded; cold-start performance is unknown.

Current-month flight volume is used only to evaluate exposure-weighted error after outcomes are observed. Training weights use lagged volume. Publication-vintage data are unavailable; using a conservative three-month gap reduces leakage risk but cannot reconstruct every historical revision or publication delay. Do not deploy without vintage-based validation and drift checks.

## Forecasting: monthly national late-arrival share

Choose ETS trend specification on the 2023 validation year using data only through September 2022, so all selection labels are available before the January 2025 test origin. For the fixed-origin 2025 evaluation, use data only through September 2024, forecast 15 months and score the final 12. The seasonal naive baseline recursively repeats the latest available same-calendar-month rate; it respects the same availability gap.

{markdown_table([['2025 forecast', 'MAE (pp)', 'RMSE (pp)'],
*[[row['model'], f"{row['mae_pp']:.3f}", f"{row['rmse_pp']:.3f}"] for row in forecast_metrics.to_dict('records')]])}

The lower test RMSE belongs to the **{forecast_winner}**. The displayed ETS band is ±**{forecast_design['band_radius_pp']:.2f} pp**, based on the 90th percentile of absolute 2023 validation errors. It covers **{forecast_design['test_band_coverage_pct']:.1f}%** of 2025 months. It is an illustrative planning band, not a guaranteed 90% prediction interval: there are only 12 dependent validation errors. COVID-era structural breaks and limited holdout years constrain generalization.

## Priorities, actions and trade-offs

1. **Prioritize exposure, then diagnose.** Review the carrier-airport segments in `sql_result_3.csv` ranked by 2025 delayed-arrival counts with at least 10,000 reported flights. High rates at tiny airports and high counts at large hubs answer different questions. Use both rate and volume before allocating investigation time.
2. **Plan a seasonal review.** Use the observed seasonal difference to schedule a pre-summer operations review. Confirm capacity, schedules and local causes with managers before changing resources. The paired comparison is a planning signal, not an estimated treatment benefit.
3. **Investigate attributed causes.** The cause-minute chart distinguishes carrier, NAS, late-aircraft, weather and security exposure. NAS includes some non-extreme weather; the weather category is not all weather. Protect the small unallocated source gap. Prioritize feasible causes and do not assume all attributed minutes are avoidable.
4. **Prefer the validated winner.** Keep the simple baseline whenever the candidate loses. Evaluate additional years and error by segment before using either model operationally. Predictions should support a review queue, not automatic penalties or passenger eligibility decisions.
5. **Measure a pilot.** A hypothetical 1-percentage-point reduction over 100,000 comparable reported flights would correspond to 1,000 fewer late arrivals. This is arithmetic scenario analysis, not a forecast of achievable benefit. Actual financial return, staffing and passenger impact cannot be estimated from these fields.

Monitor monthly late share, cancellation share, flight volume, missingness, source reconciliation gaps, and model errors. Review comparable seasons and segment mix; use a controlled or carefully matched pilot to estimate any intervention effect.

## Assumptions and responsible use

The source's reported categories are used as defined by BTS; no flight-level deduplication is possible from monthly aggregates. Missingness and name changes are documented. Outliers and pandemic months are retained. Operational counts contain no direct passenger identifiers. Public carrier/airport comparisons can still be misleading without context; they are associations affected by network mix. There is no individual fairness claim because no passenger attributes are available. Geographic and volume disparities in error should be monitored separately.

This project was prepared with AI assistance. The student should rerun it, explain the methods and limitations, and follow course attribution rules. No personal name, institution, survey result or satisfaction score has been invented.

## Sources

- [BTS Airline On-Time Statistics and Delay Causes](https://www.transtats.bts.gov/OT_Delay/OT_DelayCause1.asp), official download and reporting-scope notes.
- [BTS definitions and reporting coverage](https://www.bts.gov/explore-topics-and-geography/topics/airline-time-performance-and-causes-flight-delays), including the 15-minute late-arrival threshold and cause definitions.
- Exact download URL, server archive filename, download date, raw byte sizes and hashes: `data/raw/provenance.json`.
'''
    (REPORTS / 'findings.md').write_text(findings)
    renderer = mistune.create_markdown(plugins=['table'])
    figures = []
    for path in sorted((REPORTS / 'figures').glob('*.png')):
        encoded = base64.b64encode(path.read_bytes()).decode()
        figures.append(f'<figure><img src="data:image/png;base64,{encoded}" alt="{html.escape(path.stem)}"><figcaption>{html.escape(path.name)}</figcaption></figure>')
    document = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Airline operations — executive report</title><style>
    body{font:17px/1.65 system-ui,sans-serif;color:#20313d;background:#eff4f6;margin:0}main{max-width:1100px;margin:36px auto;background:white;padding:48px;border-radius:18px}h1{font-size:38px;line-height:1.15;color:#075568}h2{margin-top:42px;color:#075568}table{border-collapse:collapse;width:100%;font-size:15px}th,td{padding:12px;border-bottom:1px solid #dce4e9;text-align:left}th{background:#e8f3f4}img{max-width:100%;height:auto}figure{margin:36px 0;break-inside:avoid}figcaption{font-size:12px;color:#657782}a{color:#0b7087}li{margin:12px 0}@media(max-width:700px){main{margin:0;padding:22px;border-radius:0}h1{font-size:29px}table{display:block;overflow:auto}}@media print{body{background:white}main{padding:0;margin:0;max-width:none}}
    </style><main>'''+renderer(findings)+'<h2>Reproducible figures</h2>'+''.join(figures)+'<h2>Data audit</h2>'+renderer(audit_text)+'</main></html>'
    (REPORTS / 'executive_report.html').write_text(document)
