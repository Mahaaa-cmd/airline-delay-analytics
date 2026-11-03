"""Build the educational notebook; execution is a separate, verifiable step."""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
cells = []
def md(text):
    cells.append(nbf.v4.new_markdown_cell(text.strip()))
def code(text):
    cells.append(nbf.v4.new_code_cell(text.strip()))

md('''# Airline Operations & Delay Analytics
### From official BTS records to defensible operational decisions

**Advanced data analytics capstone · Python notebook · 10 reproducible phases**

This notebook follows the supplied airline assignment. It uses official BTS monthly delay-cause records for **2018–2025**. Its scope is operational delay analysis; there are no passenger satisfaction records, route origins, or individual aircraft identifiers. No unsupported fields are invented.

**Research question:** How do delay exposure and operational patterns vary across airports, carriers, and months, and can historical information anticipate future monthly delay rates?

**Learning route:** business understanding → acquisition → audit/cleaning → KPI design → EDA → hypothesis testing → prediction → forecasting → decisions → reproducibility.

If the course currently requires only material through hypothesis testing, present **Phases 1–6** as the core submission. Phases 7–10 provide the complete capstone extension. This project was prepared with AI assistance; understand, rerun and attribute it according to course rules.
''')
md('''## Setup

Install `requirements.txt` in a virtual environment as described in the README. Start Jupyter in the project root or notebook directory. The code below finds the project and imports reusable functions; `src/analysis.py` contains every transformation. Bundled raw files allow offline analysis after dependencies are installed. Full execution may take a few minutes.
''')
code('''from pathlib import Path
import sys, json, inspect
import pandas as pd
import numpy as np
from IPython.display import display, Markdown, Image

ROOT = next((p for p in [Path.cwd(), *Path.cwd().parents]
             if (p / 'src/analysis.py').exists() and (p / 'data/raw/provenance.json').exists()), None)
if ROOT is None:
    raise RuntimeError('Open Jupyter from the project root or notebooks folder.')
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.analysis import (verify_source, audit_and_clean, kpi_tables, aggregate, charts,
                         seasonal_test, build_features, prediction_analysis, forecasting, sql_analysis)
from src.reporting import write_reports
pd.set_option('display.max_columns', 30)
print('Project:', ROOT.name)
''')
md('''## Phase 1 — Business understanding

**Stakeholders:** airline operations managers, airport coordinators, and analysts. **Decision:** prioritize operational investigation and seasonal review capacity. Success means reliable definitions, reproducible results, and later-period error lower than a simple baseline where the data support it.

We cannot estimate staffing requirements, intervention effects, passenger satisfaction, or financial return because these variables are absent. Carrier rankings are not causal performance ratings: network mix, weather and airport conditions differ.
''')
code("display(Markdown((ROOT / 'docs/BUSINESS_UNDERSTANDING.md').read_text()))")
md('''## Phase 2 — Acquisition, provenance and grain

The assignment specifies [BTS TranStats](https://www.transtats.bts.gov/). We selected its official **Airline On-Time Statistics and Delay Causes** raw download, requesting all carriers and airports for January 2018–December 2025. These complete years avoid partial-year 2026 comparisons. The source summarizes operations at **year-month × carrier × arrival airport**, not individual flight grain.

The ZIP contains an unchanged CSV and an original column-definition workbook. The CSV has 21 columns; the actual audit verifies its size and schema. Exact server filename, URL, date, byte sizes and SHA-256 hashes are recorded. BTS did not provide an immutable version identifier; the hashes identify this snapshot. No external join is needed.
''')
code('''provenance = verify_source()
display(pd.Series({k: v for k, v in provenance.items() if k != 'files'}).to_frame('value'))
display(pd.DataFrame(provenance['files']).T)
raw = pd.read_csv(ROOT / 'data/raw/Airline_Delay_Cause.csv')
print('Actual raw shape:', raw.shape)
display(raw.head())
display(raw.dtypes.to_frame('dtype'))
''')
md('''## Phase 3 — Audit, cleaning and validation

Audit missingness, exact and business-key duplicates, dates, categories, numeric limits, logical count relationships, outliers, identifiers and leakage. Preserve the source and write a separate cleaned table.

Treatment rules are explicit:

1. Trim surrounding whitespace, retaining source name changes and grouping by entity codes.
2. Derive a missing delayed-arrival count as **zero only if every flight was cancelled/diverted and every delay/cause counter is explicitly zero**.
3. Exclude rows still missing required outcomes or volume; do not pretend their unknown volume is zero.
4. Retain extreme observations and pandemic months; report IQR flags rather than deleting legitimate disruptions.
5. Preserve discrepancies between total and cause-attributed minutes as an unallocated gap.
6. Never fill absent carrier-airport-month combinations with zero flights.
''')
code('''df, audit = audit_and_clean()
display(pd.Series({k: v for k, v in audit.items()
                   if not isinstance(v, dict)}).to_frame('audit result'))
display(pd.Series(audit['missing_by_field']).to_frame('raw missing rows'))
display(pd.read_csv(ROOT / 'reports/outlier_profile.csv'))
display(pd.read_csv(ROOT / 'reports/missingness_segments.csv').query('missing_outcomes > 0').head(12))
print('Source remains unchanged:', verify_source()['requested_period'])
''')
md('''Missingness is systematic enough to inspect by year and carrier, not merely total count. A globally complete 96-month timeline does not imply a complete carrier-airport panel. Legitimate carrier and airport names may change while their grouping code remains stable. The detailed audit includes column cardinalities, negative checks, date coverage and source reconciliation gaps.

The selected schema contains no passenger names, contact details, free text or direct personal identifiers. Carrier/airport codes identify public entities. Same-month outcome fields are leakage risks for prediction, even though they are appropriate for descriptive charts.
''')
code('''display(Markdown((ROOT / 'docs/DATA_DICTIONARY.md').read_text()))
display(pd.read_csv(ROOT / 'reports/numeric_profile.csv').round(2))
''')
md('''## Phase 4 — Feature engineering and KPIs

Derived on-time count = reported flights − late arrivals − cancellations − diversions. Late means arrival at least 15 minutes behind schedule under BTS definitions. Each rate divides **summed numerators by summed denominators**; averaging row percentages would over-weight tiny operations.

For example, one delayed flight among 1 flight and one among 99 flights produce 2/100 = 2%, not an unweighted average of 100% and about 1%. Delay minutes per delayed arrival is different from delay burden per reported flight. A zero denominator produces missing, not a zero rate.
''')
code('''tables, metrics = kpi_tables(df)
display(pd.Series(metrics).to_frame('2018–2025 reporting scope'))
display(Markdown((ROOT / 'docs/KPI_DEFINITIONS.md').read_text()))
display(tables['annual'].round(2))
''')
md('''## Phase 5 — Exploratory and descriptive analysis

The following charts cover time trends, volume, carrier and airport differences, calendar segmentation, attributed causes and volume-risk trade-offs. Each states the population, denominator and period. Airport/carrier comparisons are descriptive and affected by mix. Reporting coverage is not all aviation.

Chart questions: Where are delay shares high? Does volume change the operational priority? Are disruption months seasonal? Which attributed minute categories dominate? Do rankings change when exposure is considered?
''')
code('''charts(df, tables)
for name in ['01_monthly_delay.png', '02_monthly_volume.png', '03_carrier_comparison.png',
             '04_airport_comparison.png', '05_seasonality_heatmap.png', '06_delay_causes.png',
             '10_volume_risk.png']:
    display(Image(filename=str(ROOT / 'reports/figures' / name)))
''')
md('''BTS cause counts are prorated when a delayed flight has several causes. The five cause groups are carrier, extreme weather, national aviation system (NAS), security and late aircraft. NAS can include non-extreme weather, so the extreme-weather field is not the complete weather impact. Cause attribution describes reporting categories; it is not an estimated avoidable benefit.

Use both high-volume hubs and high-rate segments when identifying review priorities. The 10,000-flight ranking threshold is a project display rule to reduce small-denominator volatility, not a statistical cutoff.
''')
code('''display(tables['carrier'].query('arr_flights >= 10000')
        .sort_values('delay_pct', ascending=False)[['arr_flights', 'delay_pct', 'cancel_pct']].round(2))
display(tables['airport'].nlargest(10, 'arr_flights')
        [['arr_flights', 'delay_pct', 'cancel_pct']].round(2))
''')
md('''## Phase 6 — Hypothesis testing

**Decision question:** Is the typical major airport's summer late-arrival share meaningfully different from its autumn share?

Select the 30 largest airports using **2018–2022 volume**, then compare **June–August versus September–November during 2023–2025**. Within each airport-season, aggregate counts to a rate. Pair the two rates for the same airport; each airport receives equal weight. This avoids treating every monthly or individual flight observation as independent.

- H₀: mean airport summer-minus-autumn late-arrival share = 0.
- H₁: that mean difference is nonzero (two-sided).
- α = 0.05. Practical planning threshold = 2 percentage points, an explicit project assumption.
- Method: paired t-test on airport differences; report a 95% interval and paired Cohen dz.
- Check the difference distribution with a Q-Q plot and Shapiro diagnostic; examine a seeded sign-flip sensitivity result.

Assumptions: paired measurements, approximately independent airport differences, and a reasonably behaved mean-difference distribution. Airports share network/weather shocks, so independence is approximate. This purposive top-airport sample is not a random national sample. Conclusions are exploratory associations; the p-value does not measure the probability that H₀ is true.
''')
code('''test, difference = seasonal_test(df)
display(pd.Series(test).to_frame('paired seasonal test'))
charts(df, tables, difference=difference)
display(Image(filename=str(ROOT / 'reports/figures/07_paired_seasons.png')))
display(Image(filename=str(ROOT / 'reports/figures/11_assumptions_qq.png')))
decision = 'Reject H₀' if test['p_value'] < test['alpha'] else 'Fail to reject H₀'
display(Markdown(f"**{decision}.** Summer minus autumn = **{test['difference_pp']:.2f} pp**, "
                 f"95% CI [{test['ci_low_pp']:.2f}, {test['ci_high_pp']:.2f}], p = {test['p_value']:.3g}. "
                 'This is an airport-average historical association, not a causal effect.'))
''')
md('''A percentage point is an absolute difference between percentages: 22% − 18% = 4 pp. Cohen dz divides the mean paired difference by the standard deviation of those differences. The confidence interval depends on assumptions and is not a guarantee for every airport.

No test is selected after inspecting significance. The sign-flip result is a sensitivity check, not a cure for dependence; symmetry and independent sign flips remain assumptions. Only one primary comparison is used, so no family of multiple primary tests is created.

**Core course checkpoint:** Phases 1–6 complete the workflow through hypothesis testing. The next phases address the full assignment's modelling and forecasting requirements.
''')
md('''## Phase 7 — Leakage-aware predictive modelling

At the start of target month t, predict the **carrier-airport-month late-arrival share**. Aggregate data cannot support individual flight classification or satisfaction prediction.

Only calendar sine/cosine features and **exact t-3/t-12** historical delay shares, t-3 cancellation share, t-3 delay burden and t-3 log flight volume enter the model. BTS normally releases monthly records after month end; a three-month information gap is deliberately conservative. Exact joins prevent a missing month from turning a row shift into a false calendar lag. Actual publication vintages/revisions are unavailable, so this remains a retrospective availability approximation.

Training: through September 2023; candidate selection: January–September 2024; refit: through September 2024; final test: 2025. All training and selection labels precede the test origin with a conservative publication gap. Two predeclared gradient-boosting configurations are compared on validation flight-weighted MAE. The baseline repeats the same segment's rate 12 months earlier. Never assume complexity wins.

Report MAE and RMSE in percentage points plus R². Both flight-weighted and equal-row errors are shown. Current-month flight volume is allowed for retrospective error weighting only; it is never a predictor. Training weights use historical volume. Cold-start segments lacking exact lag histories are excluded and coverage is reported.
''')
code('''features = build_features(df)
display(features[['date', 'carrier', 'airport', 'delay_rate', 'lag3_delay_rate', 'lag12_delay_rate']].tail())
prediction_metrics, predictions, prediction_design = prediction_analysis(df)
display(pd.Series(prediction_design).to_frame('prediction design'))
display(pd.read_csv(ROOT / 'reports/prediction_validation.csv'))
display(prediction_metrics)
display(pd.read_csv(ROOT / 'reports/prediction_importance.csv').sort_values('increase_mae_pp', ascending=False))
''')
md('''The 2025 test is a rolling historical-feature exercise: earlier 2025 outcomes may become t-3 information for later 2025 months, but no 2025 labels are used for fitting. The national forecast below uses a different, fixed-origin design. Feature permutation importance is a held-out diagnostic, not a causal driver estimate; correlated lag features can share importance. There are no individual binary classes here, so class imbalance is replaced by outcome-distribution, segment-volume and panel-coverage concerns.
''')
md('''## Phase 8 — Time-series forecasting

Forecast the national reported-scope **monthly late-arrival share**, a defensible rate supporting planning. There are 96 monthly timestamps, but only one final held-out year; uncertainty is substantial.

At 1 January 2025, assume only data through September 2024 are available. Forecast October 2024–December 2025 (15 steps), then evaluate January–December 2025. Compare a seasonal-naive baseline with additive seasonal exponential smoothing (ETS). Choose no-trend versus damped-trend ETS using a corresponding 2023 validation exercise trained only through September 2022. Both models respect the same publication gap.

The displayed band uses the 90th percentile of 12 absolute validation errors. It is illustrative and empirically checked on the test year; it is not a guaranteed 90% interval. COVID shocks, changing reporting mix and dependent errors limit extrapolation.
''')
code('''forecast_metrics, forecast_output, forecast_design = forecasting(tables['monthly'])
display(pd.Series(forecast_design).to_frame('forecast design'))
display(pd.read_csv(ROOT / 'reports/forecast_validation.csv'))
display(forecast_metrics)
display(forecast_output)
charts(df, tables, difference, prediction_metrics, predictions, forecast_output)
display(Image(filename=str(ROOT / 'reports/figures/08_prediction_comparison.png')))
display(Image(filename=str(ROOT / 'reports/figures/09_forecast.png')))
''')
md('''## Phase 9 — Business interpretation and decision analysis

Use validated evidence to propose investigation priorities, not unsupported causal promises. Prioritize a high delayed-flight count alongside its rate and volume, investigate the attribution mix, and test feasible interventions in a monitored pilot. Review the candidate model honestly against the baseline.

SQL is applicable to this tabular fact table. The next cell runs the supplied SQLite-compatible queries and reconciles their totals with Pandas. The priority table uses **2025** records and a 10,000-flight threshold. It is distinct from the all-period descriptive rankings.
''')
code('''sql_analysis(df)
print((ROOT / 'sql/analysis.sql').read_text())
display(pd.read_csv(ROOT / 'reports/sql_result_3.csv'))
write_reports(audit, metrics, test, tables, prediction_metrics, prediction_design,
              forecast_metrics, forecast_design)
display(Markdown((ROOT / 'reports/findings.md').read_text()))
''')
md('''## Phase 10 — Presentation and reproducibility

The generated executive HTML report embeds every chart and the audit, so it can be opened without Python. A separate dashboard specification defines data grain, filters, measures and guardrails for Power BI/Tableau. The submission includes original and cleaned data handling, dictionary, SQL, KPI tables, model/forecast outputs, assumptions, responsible-use notes, and automated checks.

Reproduce with `python -m src.analysis`, then `python -m unittest discover -s tests -v`. Execute and export this notebook with `python scripts/execute_notebook.py`. All statistical random resampling and model seeds are fixed at 42. No GitHub login is needed locally.
''')
code('''import unittest
suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful(), 'Resolve failed validation before submission.'
print('Generated chart count:', len(list((ROOT / 'reports/figures').glob('*.png'))))
print('All analyses completed. Open reports/executive_report.html for the presentation report.')
''')
md('''## What to explain in a viva

1. **Grain:** monthly carrier × arrival-airport summaries, not individual flights or customers.
2. **Cleaning:** structural zero evidence, excluded missing operational rows, retained outliers and source gaps.
3. **KPI:** a ratio of sums with an explicit denominator; a 15-minute arrival threshold.
4. **Inference:** paired airport differences, p-value, confidence interval, effect size, assumptions and practical threshold.
5. **Prediction:** exact historical features, publication lag, chronological train/validation/test, cold-start coverage and baseline comparison.
6. **Forecast:** fixed information cutoff, seasonal naive versus ETS, later-year error and uncertain bands.
7. **Action:** prioritize investigation, confirm causes locally, monitor a pilot, and avoid causal or satisfaction claims.

Read `docs/EXPLANATION_GUIDE.md` for a detailed plain-language walkthrough and answers to likely questions.
''')
nb = nbf.v4.new_notebook(cells=cells)
nb.metadata = {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
               'language_info': {'name': 'python'}}
nbf.write(nb, ROOT / 'notebooks/airline_delay_analysis.ipynb')
print(f'Built {len(cells)} notebook cells')
