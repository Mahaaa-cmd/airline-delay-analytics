# Assignment coverage

The supplied problem statement allows the analysis to stay within the entities actually represented in the selected official dataset. This project chooses monthly delay operations; no passenger satisfaction or route/aircraft fields are invented.

| Required phase / deliverable | Implementation / evidence |
|---|---|
| Business understanding and success criteria | Notebook Phase 1; BUSINESS_UNDERSTANDING.md |
| Official source, exact file, date, version | Notebook Phase 2; raw/provenance.json, original CSV and ZIP, hashes; no immutable version supplied |
| Data dictionary and grain | DATA_DICTIONARY.md; monthly carrier-arrival-airport grain |
| Complete audit | Notebook Phase 3; reports/audit.md, audit.json, missingness_segments.csv, numeric_profile.csv, outlier_profile.csv |
| Cleaning and original/clean handling | audit_and_clean(); separate data/processed file; unchanged raw hashes |
| KPI definitions | Notebook Phase 4; KPI_DEFINITIONS.md; five aggregation tables |
| At least six meaningful visualizations | Notebook Phase 5 and later; reports/figures contains 11 PNGs |
| Relationships and segmentation | Carrier, airport, year/month, seasonal, volume-risk and cause composition views |
| One justified statistical test | Notebook Phase 6; paired airport seasonal comparison, assumptions, interval, effect size and sensitivity |
| Baseline and candidate prediction | Notebook Phase 7; historical-only regression, chronological selection/test, two error weightings, coverage |
| Time-series baseline and later-period evaluation | Notebook Phase 8; seasonal naive versus ETS, fixed-origin 2025 test and illustrative uncertainty |
| Decision analysis and executive recommendations | Notebook Phase 9; reports/findings.md; scenario arithmetic and monitoring measures |
| SQL where applicable | sql/analysis.sql; reports/sql_result_1–3.csv; SQL/Pandas totals reconciliation |
| Power BI or equivalent dashboard specification | DASHBOARD_SPECIFICATION.md; executive HTML analytical report |
| Responsible use, uncertainty, privacy, leakage | Notebook throughout; audit, business framing, findings, dictionary and README |
| Testing and reproducibility | Notebook Phase 10; tests; complete CLI pipeline; executed notebook and HTML export |
| Explanation and presentation | EXPLANATION_GUIDE.md; executive report; notebook interpretations |
| GitHub-ready documentation | README, code license, dependency ranges and exact environment record; publishing deferred at user's request |

Unsupported concepts are explicitly bounded: no passenger satisfaction target, route origin, aircraft identifier, individual flight schedule, cost or revenue data. Aggregate continuous prediction has no binary class imbalance; outcome distributions, segment exposure, missingness and coverage are reported instead. Passenger demographic fairness cannot be measured without passenger attributes; network and volume comparisons still require careful interpretation.
