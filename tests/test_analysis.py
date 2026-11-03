"""Check data contracts, KPI denominators, and exact historical alignment."""
import unittest
import json
import numpy as np
import pandas as pd
from src.analysis import verify_source, build_features, aggregate, seasonal_naive, ROOT


class AnalyticsTests(unittest.TestCase):
    def test_unchanged_source_and_business_keys(self):
        verify_source()
        raw = pd.read_csv(ROOT / 'data/raw/Airline_Delay_Cause.csv')
        self.assertEqual(raw.shape, (186371, 21))
        self.assertFalse(raw.duplicated(['year', 'month', 'carrier', 'airport']).any())

    def test_kpi_is_ratio_of_sums(self):
        rows = []
        for volume in [1, 99]:
            row = {name: 0 for name in ['carrier_delay', 'weather_delay', 'nas_delay', 'security_delay', 'late_aircraft_delay', 'on_time', 'cause_minutes_gap', 'arr_cancelled', 'arr_diverted', 'arr_delay']}
            row.update(carrier='AA', arr_flights=volume, arr_del15=1)
            rows.append(row)
        self.assertAlmostEqual(aggregate(pd.DataFrame(rows), ['carrier']).loc['AA', 'delay_pct'], 2.0)

    def test_calendar_lag_with_missing_months(self):
        # A lag must refer to exactly three months ago, not the previous observed row.
        data = pd.DataFrame({'date': pd.to_datetime(['2024-01-01', '2024-03-01', '2024-04-01', '2024-05-01']),
                             'carrier': 'AA', 'airport': 'JFK', 'month': [1, 3, 4, 5],
                             'delay_rate': [.1, .3, .4, .5], 'cancel_rate': .01,
                             'delay_burden': 3, 'arr_flights': 100})
        result = build_features(data).set_index('date')
        self.assertAlmostEqual(result.loc['2024-04-01', 'lag3_delay_rate'], .1)
        self.assertTrue(np.isnan(result.loc['2024-05-01', 'lag3_delay_rate']))

    def test_forecast_baseline_recurses_without_future_actuals(self):
        history = np.arange(24, dtype=float)
        original = history.copy()
        prediction = seasonal_naive(history, 15)
        np.testing.assert_array_equal(prediction[:12], np.arange(12, 24))
        np.testing.assert_array_equal(prediction[12:], np.arange(12, 15))
        np.testing.assert_array_equal(history, original)

    def test_generated_results_reconcile(self):
        data = pd.read_csv(ROOT / 'data/processed/cleaned_delays.csv')
        monthly = pd.read_csv(ROOT / 'reports/monthly_kpis.csv')
        self.assertAlmostEqual(data.arr_flights.sum(), monthly.arr_flights.sum())
        self.assertFalse(data[['arr_flights', 'arr_del15', 'arr_delay']].isna().any().any())
        self.assertTrue(data.delay_rate.between(0, 1).all())
        self.assertTrue((data.on_time >= 0).all())
        predictions = pd.read_csv(ROOT / 'reports/prediction_test_rows.csv')
        self.assertTrue(pd.to_datetime(predictions.date).dt.year.eq(2025).all())
        self.assertTrue(predictions.candidate.between(0, 1).all())
        design = json.loads((ROOT / 'reports/prediction_design.json').read_text())
        self.assertLessEqual(design['initial_training_max_date'], '2023-09-01')
        self.assertLessEqual(design['validation_max_date'], '2024-09-01')
        self.assertLessEqual(design['refit_max_date'], '2024-09-01')


if __name__ == '__main__':
    unittest.main()
