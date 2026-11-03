# Airline operations: executive findings

## Scope and decision

Use official BTS monthly operational aggregates to prioritize delay investigations. Historical coverage: **January 2018–December 2025**; **186,049 usable carrier-airport-month records**. Figures describe the downloaded US domestic reporting scope, not all aviation worldwide. Passenger satisfaction, route origins and individual aircraft are absent and are not inferred.

## Performance snapshot

| Metric | Calculated value | Denominator / unit |
| --- | --- | --- |
| Reported flights | 56,850,634 | Sum of arr_flights |
| Late-arrival share | 18.74% | arr_del15 / reported flights |
| Cancellation share | 2.12% | cancelled / reported flights |
| Diversion share | 0.24% | diverted / reported flights |
| Minutes per delayed arrival | 69.31 | total recorded delay minutes / delayed arrivals |

Rates are ratios of summed counts. Missing operational records are excluded with a documented audit; the observed totals do not quantify their unknown flight volume.

## Statistical evidence: summer versus autumn

Compare June–August with September–November during **2023–2025** at the **30 largest airports selected using 2018–2022 volume**. Aggregate flights within each airport-season, then give each airport equal weight. The result addresses the typical selected airport, not the typical flight.

Null: the mean paired airport difference is zero. Alternative: a difference in either direction. Method: paired t-test; alpha = 0.05. The observed summer-minus-autumn difference is **8.93 percentage points**, 95% CI **[8.00, 9.86]**, **p = 2.76e-18**, paired Cohen dz = **3.58**. Reject the zero-difference null at alpha 0.05. **30 of 30** airports have a positive difference.

The project uses 2 percentage points as an explicit practical planning threshold; the measured mean difference is above this threshold. It is a study rule, not an established industry standard. Shapiro-Wilk p for paired differences = 0.999; review the Q-Q plot rather than treating this as proof of normality. Sign-flip sensitivity p = 5e-05 (20,000 seeded resamples; symmetry/independence assumptions still apply).

Airports share network and weather shocks. The top-airport sample is purposive, not a random national sample. The test is exploratory and does not establish that season itself causes delay or that the same difference will recur.

## Prediction: honest later-year comparison

Target: a **monthly carrier-airport late-arrival share**, predicted at the start of the month. This is aggregate regression, not individual flight classification. Train through September 2023, select the candidate configuration on January–September 2024, refit through September 2024, then evaluate on 2025. All fitting/selection labels are available before the January 2025 test origin under the conservative publication-gap assumption. Features contain exact t-3 and t-12 historical quantities and known calendar seasonality; current-month operational fields never enter the model. Test features update on a rolling basis with three-month-old information, while model coefficients remain fixed.

| 2025 model | Flight-weighted MAE (pp) | Flight-weighted RMSE (pp) |
| --- | --- | --- |
| Seasonal lag-12 baseline | 5.976 | 7.913 |
| Gradient boosting candidate | 4.585 | 6.154 |

The lower flight-weighted MAE belongs to the **gradient boosting candidate**. Candidate relative MAE change versus baseline: **23.3% reduction** (negative means deterioration). Report equal-row metrics alongside volume-weighted metrics in `prediction_metrics.csv` so large airports do not hide small-segment errors. Coverage: **20,149 test records**, **88.8% of 2025 clean rows** and **98.8% of 2025 clean flight volume**. Segments without the required history are excluded; cold-start performance is unknown.

Current-month flight volume is used only to evaluate exposure-weighted error after outcomes are observed. Training weights use lagged volume. Publication-vintage data are unavailable; using a conservative three-month gap reduces leakage risk but cannot reconstruct every historical revision or publication delay. Do not deploy without vintage-based validation and drift checks.

## Forecasting: monthly national late-arrival share

Choose ETS trend specification on the 2023 validation year using data only through September 2022, so all selection labels are available before the January 2025 test origin. For the fixed-origin 2025 evaluation, use data only through September 2024, forecast 15 months and score the final 12. The seasonal naive baseline recursively repeats the latest available same-calendar-month rate; it respects the same availability gap.

| 2025 forecast | MAE (pp) | RMSE (pp) |
| --- | --- | --- |
| Seasonal naive | 3.449 | 4.540 |
| ETS candidate | 2.074 | 2.601 |

The lower test RMSE belongs to the **ETS candidate**. The displayed ETS band is ±**5.67 pp**, based on the 90th percentile of absolute 2023 validation errors. It covers **100.0%** of 2025 months. It is an illustrative planning band, not a guaranteed 90% prediction interval: there are only 12 dependent validation errors. COVID-era structural breaks and limited holdout years constrain generalization.

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
