# Complete explanation and presentation guide

## What this project does

This project turns official airline operations records into evidence a manager can review. It answers three different questions: what happened, whether a seasonal difference is meaningful, and how well historical information predicts later outcomes. These questions require different methods and should not be mixed.

The dataset contains monthly summaries. One row says, in effect, “for this carrier at this arrival airport during this month, this many flights were reported and this many were delayed/cancelled/diverted.” A row is not a customer, a survey response, an aircraft, or an individual flight. That is why the project analyzes delay shares rather than passenger satisfaction.

## Files to open

Start with `reports/executive_report.html`: it works in a normal browser, includes calculated findings and embeds all charts. Open `reports/notebook.html` for a read-only version of every code cell and output. Use `notebooks/airline_delay_analysis.ipynb` to rerun or change the analysis in Jupyter. Read the README for setup commands. All source code is under `src/`; data definitions and assignment coverage are under `docs/`.

## How the code is organized

`src/analysis.py` contains the analytical functions. `verify_source()` compares the original file hashes with the provenance record. `audit_and_clean()` profiles the source and creates the separate cleaned table. `aggregate()` calculates rates from sums. `kpi_tables()` produces monthly, annual, carrier and airport summaries. `seasonal_test()` runs the paired comparison. `build_features()` joins exact historical months. `prediction_analysis()` trains and evaluates the prediction models. `forecasting()` validates the time-series forecasts. `charts()` draws the visual outputs. `sql_analysis()` runs SQL and reconciles totals. `run()` performs them in that order.

`src/reporting.py` writes the audit, findings and self-contained HTML report using computed values. The reporting text is generated from results, so it does not claim that a model wins when it loses. The notebook calls the same functions phase by phase; reusable functions avoid having two inconsistent versions of the mathematics.

## The cleaning logic

An empty number is not automatically zero. The project identifies 250 rows whose delayed count is blank but whose entire flight volume consists of cancellations/diversions and whose delay counters are all explicitly zero. In those rows there are logically no late arrivals, so the cleaned value is zero. The original blank is preserved in the raw file.

Another 322 rows lack required operational quantities. These are excluded from the analytical table instead of inventing their flight volume. Missingness by year and carrier is saved for review. Their unknown flight volume cannot be estimated from the fact that Pandas sums known values to zero.

Large numbers at large airports are not necessarily errors. Extreme disruption months, including COVID-era changes, are retained. IQR flags are documented, not automatically removed. Counts of attributed cause minutes do not perfectly sum to total delay minutes in every record; the small residual is reported rather than forced into a cause.

## Understanding the KPIs

The headline late-arrival share is total delayed arrivals divided by total reported flights. Across the cleaned 2018–2025 reporting scope, it is about **18.74%**. Cancellation share is about **2.12%**. Mean delay among delayed arrivals is about **69.31 minutes**; this is not the average delay for every flight or a measure of every passenger's experience.

Denominators change the question. A small airport with a high delay percentage may affect fewer flights than a large airport with a moderate percentage. The project displays both volume and rates and applies a transparent 10,000-flight ranking threshold.

Never average row percentages unless the question explicitly asks for an equal-row average. Ten delayed flights among 100 flights and ten among 1,000 flights produce 20/1,100 = 1.82%, not the unweighted average of 10% and 1% (5.5%).

## How to explain the charts

1. **Monthly delay share:** examines changes in the late-arrival rate. Separate rate changes from changes in reporting volume.
2. **Monthly volume:** shows the scale of operations and the COVID disruption. A change in volume can alter who is represented.
3. **Carrier comparison:** compares weighted historical rates. It does not isolate airline quality because airport and network mix differ.
4. **Airport comparison:** shows rates at the 20 largest airports. Airport size and exposure matter alongside the ranking.
5. **Year-month heatmap:** reveals whether high-rate months repeat consistently or vary by year.
6. **Cause composition:** shows shares of recorded delay minutes assigned to operational categories. Attribution is not proof that those minutes could be eliminated.
7. **Matched seasonal differences:** each bar is one selected airport's summer rate minus its autumn rate, not a flight-level effect.
8. **Prediction errors:** lower MAE is better; compare the candidate with the same-period baseline.
9. **Forecast chart:** compares actual monthly 2025 rates with predictions made using a fixed earlier information cutoff.
10. **Volume-risk scatter:** helps distinguish high-rate small segments from high-exposure large segments.
11. **Q-Q diagnostic:** checks whether the airport seasonal differences are roughly compatible with a normal distribution; it does not prove independence.

## Hypothesis testing in plain language

The project compares summer (June–August) and autumn (September–November). The 30 airports are chosen using earlier 2018–2022 volume, then evaluated during 2023–2025. Choosing the airports with earlier data avoids selecting them because of the seasonal result itself.

For each airport, calculate a summer rate and an autumn rate, then subtract. This creates 30 paired differences. A paired t-test asks whether the mean difference is compatible with zero under the statistical assumptions. It is better suited to this question than treating every monthly observation as independent.

The mean summer-minus-autumn difference is about **8.93 percentage points** for these airports. Read the exact p-value, confidence interval, effect size and diagnostic outputs from `reports/hypothesis_test.json` or the notebook. A percentage point is an absolute percentage difference; a rate of 25% compared with 16% differs by 9 percentage points.

The p-value is the probability of data at least this extreme under the null model and its assumptions. It is not the probability that the null hypothesis is true. The 95% confidence interval expresses uncertainty in the mean difference under the model. Cohen dz describes the difference relative to variation in the paired differences.

The project declares 2 percentage points as a practical review threshold before interpreting the result. This is an explicit planning assumption, not an industry rule. Statistical significance alone does not tell a manager what action is worthwhile.

Airports share weather and network disruptions, and the largest airports were not randomly sampled. Therefore the test is exploratory; neither the t-test nor the sign-flip sensitivity check proves a causal seasonal effect. A large observed difference can support a seasonal review without proving that a specific intervention will fix it.

## Prediction and data leakage

Prediction means estimating a future **monthly carrier-airport delay share**, not whether a specific passenger's flight will be late. The target is a continuous fraction, so this is regression. There is no binary classification label and no satisfaction outcome in this dataset.

At the start of a target month, same-month delays, cancellations, volume and cause minutes are unknown. Using them as predictors would leak the outcome. The project uses only known calendar seasonality and historical outcomes from exactly 3 and 12 months earlier. A three-month information gap allows for BTS publication delay. Exact calendar joins are important: if February is absent, shifting one row from March could accidentally refer to January.

Train with data through September 2023, select one of two model configurations on January–September 2024, refit through September 2024, then evaluate 2025. The last-quarter 2024 outcomes are deliberately unavailable for fitting or selection at the January 2025 origin. The simple baseline repeats each segment's rate from 12 months earlier. Gradient boosting learns nonlinear combinations of historical rates and seasonality. Its settings are chosen before final test evaluation.

On the 2025 held-out records, flight-weighted MAE is about **5.98 pp** for the baseline and **4.59 pp** for the candidate, approximately **23.3% lower error**. This is an error reduction, not a reduction in actual flight delays. RMSE penalizes large mistakes more heavily. R² can be negative if a prediction is worse than a constant reference; it is not a probability or accuracy percentage.

Both equal-record and flight-weighted errors are reported because large airports can dominate a weighted metric. Required lag histories are unavailable for some segments; the report states how much row and flight volume coverage remains. Cold-start performance is not measured. No actual publication-vintage archive is available, so retrospective leakage protection is approximate and production use would need stronger validation.

## Forecasting and uncertainty

Prediction estimates rates for many carrier-airport segments. Forecasting estimates a single national monthly rate across time. The designs are deliberately different.

For the 2025 forecast, pretend it is 1 January 2025 and only records through September 2024 are available. Forecast the next 15 months, then evaluate the final 12 months, January–December 2025. The baseline repeats the latest available same-month rate recursively. ETS combines level and recurring monthly seasonality, optionally with a damped trend.

The ETS specification is chosen using a separate 2023 validation exercise. Final 2025 RMSE is about **4.54 pp** for seasonal naive and **2.60 pp** for ETS. Lower error on this one year is evidence for further evaluation, not proof of reliable performance under every future disruption.

The shaded band uses the 90th percentile of absolute validation-year errors. There are only 12 dependent validation observations, so it is an illustrative planning range, not a guaranteed 90% prediction interval. The report explicitly shows how often the actual test values fall within it.

## What recommendations are justified

Review high-volume segments with many delayed arrivals, use rates to detect disproportionate exposure, and examine attributed cause composition. Plan a pre-summer operational review using the seasonal evidence. Confirm feasibility with local teams and monitor a pilot.

A scenario calculation can clarify scale: a 1-percentage-point improvement among 100,000 comparable flights corresponds to 1,000 fewer late arrivals. This is arithmetic, not a predicted achievable benefit. The dataset cannot estimate staffing cost, causal return, ticket revenue or passenger satisfaction.

## A five-minute presentation

Spend 30 seconds on the airline operations problem; 45 seconds on source, grain and cleaning; one minute on three key charts; one minute on the paired test; one minute on honest baseline comparisons; and 45 seconds on recommendations and limitations. Keep exact calculated results open in the notebook. If presenting only coursework through hypothesis testing, devote the model/forecast time to cleaning, assumptions and the confidence interval instead.

## Likely viva questions

**Why not predict satisfaction?** There is no satisfaction outcome; inventing one would make the analysis invalid.

**Why not use a random train/test split?** Later observations can share historical patterns with earlier records; a random split does not represent forecasting future performance. Chronological validation is closer to the intended decision.

**Why three-month lags?** Monthly publication is delayed. The gap is conservative, though exact release vintages and revisions remain unavailable.

**Does the model prove which cause matters?** No. Predictive association and held-out feature importance are not causal effects.

**Why keep a simple baseline?** It sets a meaningful minimum. A complex model is useful only if it improves relevant later-period performance and remains practical.

**Can we compare carriers fairly?** These descriptive rates reflect network/airport mix. They are investigation signals, not adjusted causal quality scores.

**What would improve the work?** More held-out years, actual publication-vintage snapshots, flight-level pre-departure fields for individual predictions, operational cost/capacity data, and a monitored intervention study. Any added dataset would need a justified join and a new privacy/leakage audit.
