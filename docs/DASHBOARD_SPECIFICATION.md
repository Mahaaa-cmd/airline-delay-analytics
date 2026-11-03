# Dashboard specification

The project includes a browser-readable executed notebook and a generated executive HTML report as an equivalent analytical presentation. This specification supports a future Power BI/Tableau implementation without requiring those applications.

## Data model

One fact table: `cleaned_delays.csv`, grain month × carrier × airport. Use a unique calendar table at month grain and distinct carrier and airport dimensions; join each dimension one-to-many to the fact table. Do not join a day calendar directly to monthly records or duplicate flight volume. Preserve original missing outcomes. KPI DAX/SQL must divide aggregated numerators by aggregated denominators.

## Pages

1. **Executive overview:** reported flights, late share, cancellation share, minutes per delayed arrival, monthly trend, and cause-minute composition. Filters: month range, carrier, airport. Show denominator and source snapshot date.
2. **Operational priorities:** airport and carrier comparisons, volume versus delay-rate scatter, high-volume carrier-airport priority table. Default minimum 10,000 flights; include a visible low-volume warning and an exportable denominator column.
3. **Statistical evidence:** matched summer versus autumn airport comparison; effect in percentage points, confidence interval, p-value, sign agreement, and assumptions.
4. **Validation and planning:** baseline versus candidate prediction errors; forecast actuals versus seasonal naive and candidate forecasts; split dates, uncertainty caveat, and model winner.
5. **Data quality:** missingness, exact/business-key duplicates, invalid-value checks, exclusions, raw/clean row counts, and last verified hash.

## Interactions and guardrails

Cross-filter descriptive views; retain fixed chronological model evaluation and visibly label it as fixed scope. No filtering can turn full-sample retrospective outcomes into pre-decision predictors. Blank denominators remain blank. Ranking titles show reporting population and dates. Do not interpret cause shares, carrier ranks, or statistical significance as intervention effects. No personal data or aircraft/person tracking is supported.
