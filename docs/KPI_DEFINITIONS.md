# KPI definitions

All rates use sums of counts, never an unweighted average of row percentages. The grain can be the full analysis period, month, carrier, or airport, and every output states its scope.

| KPI | Numerator | Denominator | Unit / interpretation |
|---|---|---|---|
| Reported flight volume | sum(arr_flights) | None | Flight records in selected BTS reporting scope |
| Late-arrival share | sum(arr_del15) | sum(arr_flights) | Percent; arrival delay at least 15 minutes |
| Cancellation share | sum(arr_cancelled) | sum(arr_flights) | Percent of reported flights |
| Diversion share | sum(arr_diverted) | sum(arr_flights) | Percent of reported flights |
| Derived on-time share | flights − delayed − cancelled − diverted | flights | Percent; mutually exclusive BTS outcome categories assumed and validated non-negative |
| Mean delay per delayed arrival | sum(arr_delay) | sum(arr_del15) | Minutes per late arrival; not mean delay across all flights |
| Delay burden per reported flight | sum(arr_delay) | sum(arr_flights) | Minutes per reported flight |
| Cause share of delay minutes | sum(selected *_delay) | sum(arr_delay) | Percent; source categories are operational attribution, not causal estimates |

Zero denominators produce missing rates, not zeros. `arr_del15` and cause-attributed flight counts can contain decimals because of source attribution/rounding; they are not forcibly cast to integers. Ranking tables apply a minimum of 10,000 reported flights over the chosen period; exploratory carrier-airport priority tables use the same threshold. This is a fixed display-stability rule, not a significance threshold.

Counts represent the downloaded reporting scope. The 2018 onward reporting structure includes reporting operating/marketing/codeshare arrangements described by BTS; these aggregates do not let us independently deduplicate individual flights. Results do not claim complete worldwide or all-US aviation coverage.
