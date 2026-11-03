# Business understanding

## Decision and stakeholders

Airline operations managers, airport coordinators, and analysts need to identify concentrations of arrival disruption and plan review capacity. The project measures historical delay and cancellation exposure, examines a seasonal comparison, and evaluates whether historical monthly information can help anticipate future delay rates.

The primary decision is which carrier-airport segments merit operational investigation, with volume and uncertainty considered together. This analysis cannot prescribe staffing levels, individual flight interventions, or financial returns because capacity, costs, schedules, and intervention outcomes are absent.

## Scope

Official BTS monthly airline delay-cause data, all reporting carriers and airports returned for January 2018 through December 2025. Each row is a **year-month × carrier × arrival airport** summary. The chosen complete calendar years avoid a partial 2026 comparison. The download is a dated snapshot, not an immutable BTS release. No other dataset is substituted or joined.

The available data describe aggregate operations. They contain no passenger satisfaction labels, route origins, individual aircraft identifiers, passenger characteristics, or individual flight timestamps. Accordingly, satisfaction prediction, route comparisons, aircraft-level explanations, and passenger fairness analysis are out of scope. Carrier and airport codes are entity identifiers, not personal identifiers.

## Success criteria

1. Reconcile counts, identify missingness and invalid records, and define denominators precisely.
2. Produce at least six reproducible visualizations and one justified statistical comparison.
3. Evaluate a historical-information prediction model against a lag baseline on a later year, reporting honestly if it fails to improve.
4. Evaluate national monthly delay-rate forecasts against seasonal naive forecasts on a held-out later year.
5. Turn findings into specific investigation priorities with monitoring measures and limitations.

## Prediction decision time

At the start of month t, predict the **monthly carrier-airport late-arrival share**, not an individual flight's outcome. Use calendar month, carrier, airport, and outcomes from t-3 and t-12 only. BTS indicates monthly data are generally released about 30 days after month end; the three-month gap is deliberately conservative. Historical publication timestamps and revisions are unavailable, so the exercise is a retrospective as-of approximation. Production use would need actual release-vintage data.

## Recommended operating process

Review high-volume, high-delay segments monthly. Investigate causes with local managers before assigning resources; use a limited pilot and compare outcomes over comparable months. Monitor late-arrival share, cancellation share, flight volume, prediction error, and missing-data alerts. Avoid treating a carrier ranking as a causal measure of carrier quality: airport mix, weather, season, and schedules differ.
