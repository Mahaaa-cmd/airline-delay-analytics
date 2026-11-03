"""Auditable monthly airline operations analysis using an unchanged BTS snapshot."""
from pathlib import Path
import hashlib
import json
import sqlite3
import zipfile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from statsmodels.tsa.holtwinters import ExponentialSmoothing

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'
SEED = 42
KEYS = ['year', 'month', 'carrier', 'airport']
COUNTS = ['arr_flights', 'arr_del15', 'arr_cancelled', 'arr_diverted', 'arr_delay']
CAUSES = ['carrier_delay', 'weather_delay', 'nas_delay', 'security_delay', 'late_aircraft_delay']
FEATURES = ['month_sin', 'month_cos', 'lag3_delay_rate', 'lag12_delay_rate',
            'lag3_cancel_rate', 'lag3_delay_burden', 'lag3_log_volume']


def verify_source():
    manifest = json.loads((ROOT / 'data/raw/provenance.json').read_text())
    # Restore the exact original CSV from the bundled ZIP on a fresh GitHub clone.
    csv_path = ROOT / 'data/raw/Airline_Delay_Cause.csv'
    if not csv_path.exists():
        archive_path = ROOT / 'data/raw/bts_delay_causes_2018_2025.zip'
        expected_archive = manifest['files'][archive_path.name]['sha256']
        if hashlib.sha256(archive_path.read_bytes()).hexdigest() != expected_archive:
            raise ValueError('Source archive checksum mismatch')
        with zipfile.ZipFile(archive_path) as archive:
            original = archive.read(csv_path.name)
        if hashlib.sha256(original).hexdigest() != manifest['files'][csv_path.name]['sha256']:
            raise ValueError('Archived CSV checksum mismatch')
        csv_path.write_bytes(original)
    for name, meta in manifest['files'].items():
        path = ROOT / 'data/raw' / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != meta['sha256']:
            raise ValueError(f'Source checksum mismatch: {name}')
    return manifest


def audit_and_clean():
    """Leave raw bytes untouched; derive only defensible structural zeroes."""
    verify_source()
    raw = pd.read_csv(ROOT / 'data/raw/Airline_Delay_Cause.csv')
    numeric = raw.select_dtypes('number').columns.tolist()
    audit = dict(raw_rows=len(raw), raw_columns=len(raw.columns),
                 exact_duplicates=int(raw.duplicated().sum()),
                 business_key_duplicates=int(raw.duplicated(KEYS).sum()),
                 missing_by_field={k: int(v) for k, v in raw.isna().sum().items()},
                 dtypes={k: str(v) for k, v in raw.dtypes.items()},
                 unique_by_field={k: int(v) for k, v in raw.nunique().items()},
                 negative_by_field={k: int(v) for k, v in (raw[numeric] < 0).sum().items()})
    if audit['exact_duplicates'] or audit['business_key_duplicates']:
        raise ValueError('Unexpected duplicate rows: investigate before proceeding')
    df = raw.copy()
    strip_changes = {}
    for column in ['carrier', 'carrier_name', 'airport', 'airport_name']:
        before = df[column].copy()
        df[column] = df[column].str.strip()
        strip_changes[column] = int(before.ne(df[column]).sum())
    invalid_date = ~df.month.between(1, 12) | ~df.year.between(2018, 2025)
    date = pd.to_datetime(dict(year=df.year, month=df.month, day=1), errors='coerce')
    audit['invalid_date_rows'] = int((invalid_date | date.isna()).sum())
    audit['invalid_airport_codes'] = int((~df.airport.str.fullmatch('[A-Z]{3}')).sum())
    audit['trimmed_strings'] = strip_changes
    if audit['invalid_date_rows'] or audit['invalid_airport_codes'] or any(audit['negative_by_field'].values()):
        raise ValueError('Unexpected invalid records: investigate before proceeding')
    df['date'] = date
    # A missing delayed count is logically zero only when every flight was cancelled/diverted,
    # and all recorded delay-minute/cause counters are explicitly zero (not missing).
    zero_evidence = ['arr_delay', *CAUSES, 'carrier_ct', 'weather_ct', 'nas_ct', 'security_ct', 'late_aircraft_ct']
    structural = (df.arr_del15.isna() & df.arr_flights.notna()
                  & df.arr_flights.eq(df.arr_cancelled + df.arr_diverted)
                  & df[zero_evidence].eq(0).all(axis=1))
    audit['structural_zero_delayed_count_rows'] = int(structural.sum())
    df.loc[structural, 'arr_del15'] = 0.0
    exclude = df[COUNTS + CAUSES].isna().any(axis=1) | df.arr_flights.le(0)
    audit['excluded_rows_missing_or_nonpositive_volume'] = int(exclude.sum())
    audit['excluded_known_flight_volume'] = float(df.loc[exclude, 'arr_flights'].sum())
    audit['excluded_by_year'] = {str(k): int(v) for k, v in df.loc[exclude].groupby('year').size().items()}
    df = df.loc[~exclude].copy()
    df['on_time'] = df.arr_flights - df.arr_del15 - df.arr_cancelled - df.arr_diverted
    if df.on_time.lt(-.01).any():
        raise ValueError('Outcome counts exceed reported flights')
    df['delay_rate'] = df.arr_del15 / df.arr_flights
    df['cancel_rate'] = df.arr_cancelled / df.arr_flights
    df['delay_burden'] = df.arr_delay / df.arr_flights
    df['cause_minutes_gap'] = df.arr_delay - df[CAUSES].sum(axis=1)
    audit['rows_cause_minutes_not_reconciled'] = int(df.cause_minutes_gap.abs().gt(.01).sum())
    audit['unallocated_delay_minutes'] = float(df.cause_minutes_gap.sum())
    audit['clean_rows'] = len(df)
    audit['date_min'] = str(df.date.min().date())
    audit['date_max'] = str(df.date.max().date())
    audit['observed_months'] = int(df.date.nunique())
    audit['global_missing_months'] = [str(x.date()) for x in pd.date_range(df.date.min(), df.date.max(), freq='MS').difference(df.date.unique())]
    audit['carriers'] = int(df.carrier.nunique())
    audit['airports'] = int(df.airport.nunique())
    audit['personal_fields'] = 'None in the selected 21-column operational aggregate schema.'
    audit['carrier_codes_with_multiple_names'] = int(df.groupby('carrier').carrier_name.nunique().gt(1).sum())
    audit['airport_codes_with_multiple_names'] = int(df.groupby('airport').airport_name.nunique().gt(1).sum())
    # Retain name changes and outliers; group by codes, not names. Profile IQR tails.
    outliers = []
    for col in COUNTS:
        q1, q3 = df[col].quantile([.25, .75])
        lower, upper = q1 - 1.5 * (q3-q1), q3 + 1.5 * (q3-q1)
        outliers.append({'field': col, 'iqr_low': lower, 'iqr_high': upper,
                         'flagged_rows': int((df[col].lt(lower) | df[col].gt(upper)).sum()), 'treatment': 'Retained'})
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / 'audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    pd.DataFrame(outliers).to_csv(REPORTS / 'outlier_profile.csv', index=False)
    raw[numeric].describe().T.to_csv(REPORTS / 'numeric_profile.csv')
    raw.assign(missing_outcomes=raw.arr_del15.isna()).groupby(['year', 'carrier']).agg(
        rows=('carrier', 'size'), missing_outcomes=('missing_outcomes', 'sum')).to_csv(REPORTS / 'missingness_segments.csv')
    df = df.sort_values(['date', 'carrier', 'airport']).reset_index(drop=True)
    df.to_csv(ROOT / 'data/processed/cleaned_delays.csv', index=False)
    return df, audit


def aggregate(df, groups):
    result = df.groupby(groups, observed=True)[COUNTS + CAUSES + ['on_time', 'cause_minutes_gap']].sum(min_count=1)
    result['delay_pct'] = 100 * result.arr_del15 / result.arr_flights
    result['cancel_pct'] = 100 * result.arr_cancelled / result.arr_flights
    result['divert_pct'] = 100 * result.arr_diverted / result.arr_flights
    result['on_time_pct'] = 100 * result.on_time / result.arr_flights
    result['minutes_per_delayed'] = result.arr_delay / result.arr_del15.replace(0, np.nan)
    return result


def kpi_tables(df):
    tables = {name: aggregate(df, keys) for name, keys in [
        ('monthly', ['date']), ('carrier', ['carrier']), ('airport', ['airport']),
        ('carrier_airport', ['carrier', 'airport']), ('annual', ['year'])]}
    for name, table in tables.items():
        table.to_csv(REPORTS / f'{name}_kpis.csv')
    metrics = {
        'reported_flights': float(df.arr_flights.sum()),
        'late_arrival_pct': float(df.arr_del15.sum() / df.arr_flights.sum() * 100),
        'cancellation_pct': float(df.arr_cancelled.sum() / df.arr_flights.sum() * 100),
        'diversion_pct': float(df.arr_diverted.sum() / df.arr_flights.sum() * 100),
        'minutes_per_delayed_arrival': float(df.arr_delay.sum() / df.arr_del15.sum()),
        'unallocated_delay_minutes_pct': float(df.cause_minutes_gap.sum() / df.arr_delay.sum() * 100)}
    (REPORTS / 'metrics.json').write_text(json.dumps(metrics, indent=2)+'\n')
    return tables, metrics


def seasonal_test(df):
    """Paired airport-level summer-minus-autumn rates, analysis years 2023–2025."""
    prior = df[df.year.le(2022)].groupby('airport').arr_flights.sum()
    airports = prior.nlargest(30).index
    sample = df[df.year.between(2023, 2025) & df.airport.isin(airports) & df.month.isin([6, 7, 8, 9, 10, 11])].copy()
    sample['season'] = np.where(sample.month.isin([6, 7, 8]), 'Summer', 'Autumn')
    paired = aggregate(sample, ['airport', 'season'])['delay_pct'].unstack().dropna()
    difference = paired.Summer - paired.Autumn
    n = len(difference)
    result = stats.ttest_rel(paired.Summer, paired.Autumn)
    ci = result.confidence_interval(confidence_level=.95)
    rng = np.random.default_rng(SEED)
    signed = rng.choice([-1, 1], size=(20000, n)) * difference.to_numpy()
    permutation_p = (np.abs(signed.mean(axis=1)).__ge__(abs(difference.mean())).sum() + 1) / 20001
    output = dict(null='Mean airport summer-minus-autumn late-arrival share = 0',
                  alternative='Two-sided mean difference != 0', alpha=.05,
                  analysis_years='2023–2025', selection='30 largest airports by reported 2018–2022 volume',
                  paired_airports=n, mean_summer_pct=float(paired.Summer.mean()),
                  mean_autumn_pct=float(paired.Autumn.mean()), difference_pp=float(difference.mean()),
                  ci_low_pp=float(ci.low), ci_high_pp=float(ci.high),
                  t_statistic=float(result.statistic), p_value=float(result.pvalue),
                  paired_cohen_dz=float(difference.mean()/difference.std(ddof=1)),
                  shapiro_difference_p=float(stats.shapiro(difference).pvalue),
                  signflip_sensitivity_p=float(permutation_p),
                  positive_difference_airports=int(difference.gt(0).sum()),
                  practical_threshold_pp=2.0,
                  assumption_note='Airports share disruption shocks; independence is approximate. Purposive top-airport sample; inference is exploratory, not causal or nationally representative.')
    paired.assign(difference_pp=difference).to_csv(REPORTS / 'paired_airport_seasons.csv')
    (REPORTS / 'hypothesis_test.json').write_text(json.dumps(output, indent=2)+'\n')
    return output, difference


def build_features(df):
    """Exact calendar joins prevent gaps from silently changing lag meaning."""
    data = df.copy()
    data['month_sin'] = np.sin(2*np.pi*data.month/12)
    data['month_cos'] = np.cos(2*np.pi*data.month/12)
    data['log_volume'] = np.log1p(data.arr_flights)
    for lag, columns in [(3, ['delay_rate', 'cancel_rate', 'delay_burden', 'log_volume']), (12, ['delay_rate'])]:
        history = data[['date', 'carrier', 'airport', *columns]].copy()
        history['date'] = history.date + pd.DateOffset(months=lag)
        history = history.rename(columns={col: f'lag{lag}_{col}' for col in columns})
        data = data.merge(history, on=['date', 'carrier', 'airport'], how='left', validate='one_to_one')
    return data


def regression_metrics(actual, prediction, weights=None):
    return {'mae_pp': float(mean_absolute_error(actual, prediction, sample_weight=weights)*100),
            'rmse_pp': float(np.sqrt(mean_squared_error(actual, prediction, sample_weight=weights))*100),
            'r2': float(r2_score(actual, prediction, sample_weight=weights))}


def prediction_analysis(df):
    features = build_features(df)
    usable = features.dropna(subset=FEATURES).copy()
    train = usable[usable.date.le('2023-09-01')]
    validation = usable[usable.year.eq(2024) & usable.month.le(9)]
    test = usable[usable.year.eq(2025)]
    trials = []
    for leaves in [7, 15]:
        model = HistGradientBoostingRegressor(max_iter=120, max_leaf_nodes=leaves,
                    learning_rate=.08, l2_regularization=10, early_stopping=False, random_state=SEED)
        # Historical volume weights are available at decision time; target-month volume is not a feature.
        model.fit(train[FEATURES], train.delay_rate, sample_weight=np.expm1(train.lag3_log_volume).clip(1, 10000))
        pred = np.clip(model.predict(validation[FEATURES]), 0, 1)
        trials.append({'max_leaf_nodes': leaves, **regression_metrics(validation.delay_rate, pred, validation.arr_flights)})
    chosen = min(trials, key=lambda row: row['mae_pp'])['max_leaf_nodes']
    development = usable[usable.date.le('2024-09-01')]
    model = HistGradientBoostingRegressor(max_iter=120, max_leaf_nodes=chosen,
                learning_rate=.08, l2_regularization=10, early_stopping=False, random_state=SEED)
    model.fit(development[FEATURES], development.delay_rate,
              sample_weight=np.expm1(development.lag3_log_volume).clip(1, 10000))
    prediction = np.clip(model.predict(test[FEATURES]), 0, 1)
    rows = []
    for name, pred in [('Seasonal lag-12 baseline', test.lag12_delay_rate), ('Gradient boosting candidate', prediction)]:
        rows.append({'model': name, 'weighting': 'target-month flight volume (evaluation only)',
                     **regression_metrics(test.delay_rate, pred, test.arr_flights)})
        rows.append({'model': name, 'weighting': 'equal carrier-airport-month weight',
                     **regression_metrics(test.delay_rate, pred)})
    performance = pd.DataFrame(rows)
    performance.to_csv(REPORTS / 'prediction_metrics.csv', index=False)
    pd.DataFrame(trials).to_csv(REPORTS / 'prediction_validation.csv', index=False)
    output = test[['date', 'carrier', 'airport', 'arr_flights', 'delay_rate']].copy()
    output['baseline'] = test.lag12_delay_rate
    output['candidate'] = prediction
    output.to_csv(REPORTS / 'prediction_test_rows.csv', index=False)
    coverage = dict(train_rows=len(train), validation_rows=len(validation), test_rows=len(test),
                    test_all_clean_rows=int(df.year.eq(2025).sum()),
                    test_row_coverage_pct=float(100*len(test)/df.year.eq(2025).sum()),
                    test_flight_coverage_pct=float(100*test.arr_flights.sum()/df.loc[df.year.eq(2025), 'arr_flights'].sum()),
                    features=FEATURES, chosen_max_leaf_nodes=chosen,
                    target='Carrier-airport-month late-arrival share; not individual flight classification',
                    training_cutoff='2023-09; validation January–September 2024; refit through 2024-09; final test 2025',
                    initial_training_max_date=str(train.date.max().date()),
                    validation_max_date=str(validation.date.max().date()),
                    refit_max_date=str(development.date.max().date()),
                    availability='Only exact t-3, t-12 lags and calendar month. Rolling test features may use earlier 2025 observations once three months old. No test labels used for fitting.',
                    asof_limit='Publication-vintage data unavailable; retrospective as-of approximation; production requires actual release dates/revisions.')
    (REPORTS / 'prediction_design.json').write_text(json.dumps(coverage, indent=2)+'\n')
    # Descriptive held-out permutation importance (diagnostic only, never used to select model).
    reference = mean_absolute_error(test.delay_rate, prediction, sample_weight=test.arr_flights)
    rng = np.random.default_rng(SEED)
    importance = []
    for col in FEATURES:
        shuffled = test[FEATURES].copy()
        shuffled[col] = rng.permutation(shuffled[col].to_numpy())
        error = mean_absolute_error(test.delay_rate, np.clip(model.predict(shuffled), 0, 1), sample_weight=test.arr_flights)
        importance.append({'feature': col, 'increase_mae_pp': float((error-reference)*100)})
    pd.DataFrame(importance).to_csv(REPORTS / 'prediction_importance.csv', index=False)
    return performance, output, coverage


def seasonal_naive(train, steps):
    history = list(train)
    values = []
    for _ in range(steps):
        next_value = history[-12]
        history.append(next_value)
        values.append(next_value)
    return np.array(values)


def ets_forecast(train, steps, trend):
    model = ExponentialSmoothing(train, trend=trend, damped_trend=trend is not None,
                seasonal='add', seasonal_periods=12, initialization_method='estimated')
    fit = model.fit(optimized=True)
    return np.clip(np.asarray(fit.forecast(steps)), 0, 1)


def forecasting(monthly):
    series = (monthly.arr_del15/monthly.arr_flights).asfreq('MS')
    if series.isna().any():
        raise ValueError('Monthly series contains gaps')
    # At 1 Jan 2025, use observations only through Sep 2024; forecast Oct 2024–Dec 2025,
    # then evaluate the final 12 values. This explicitly respects the publication gap.
    # Select hyperparameters and calibrate bands on 2023: all those labels are available
    # before the Jan 2025 test origin. Using full-year 2024 validation would leak late releases.
    validation_train = series.loc[:'2022-09-01']
    validation_actual = series.loc['2023-01-01':'2023-12-01']
    trials = []
    for trend in [None, 'add']:
        pred = ets_forecast(validation_train, 15, trend)[3:]
        trials.append({'trend': trend or 'none', **regression_metrics(validation_actual, pred)})
    chosen = min(trials, key=lambda row: row['rmse_pp'])['trend']
    trend = None if chosen == 'none' else chosen
    train = series.loc[:'2024-09-01']
    actual = series.loc['2025-01-01':'2025-12-01']
    baseline = np.clip(seasonal_naive(train, 15)[3:], 0, 1)
    pred = ets_forecast(train, 15, trend)[3:]
    calibration = np.abs(validation_actual.to_numpy() - ets_forecast(validation_train, 15, trend)[3:])
    radius = float(np.quantile(calibration, .9, method='higher'))
    output = pd.DataFrame({'actual': actual, 'seasonal_naive': baseline, 'ets': pred,
                          'ets_lower': np.maximum(0, pred-radius), 'ets_upper': np.minimum(1, pred+radius)})
    performance = pd.DataFrame([{'model': name, **regression_metrics(actual, prediction)}
                               for name, prediction in [('Seasonal naive', baseline), ('ETS candidate', pred)]])
    output.to_csv(REPORTS / 'forecast_test_months.csv')
    performance.to_csv(REPORTS / 'forecast_metrics.csv', index=False)
    pd.DataFrame(trials).to_csv(REPORTS / 'forecast_validation.csv', index=False)
    design = dict(target='National reported-scope monthly late-arrival share',
                  validation='Forecast 2023 from observations through September 2022; selection completed before 2025 origin',
                  final_test='Forecast 2025 from observations through September 2024',
                  information_cutoff='Conservative three-month publication gap; fixed-origin 15-step forecast, final 12 months evaluated',
                  chosen_ets_trend=chosen, band='Symmetric 90th percentile absolute validation-year forecast error; illustrative, not a calibrated coverage guarantee',
                  band_radius_pp=radius*100,
                  test_band_coverage_pct=float(100*((output.actual>=output.ets_lower)&(output.actual<=output.ets_upper)).mean()),
                  limitations='Only 12 validation and 12 test months; dependent errors; COVID structural break; no actual release-vintage data; no extrapolation of causal benefits.')
    (REPORTS / 'forecast_design.json').write_text(json.dumps(design, indent=2)+'\n')
    return performance, output, design


def charts(df, tables, difference=None, prediction_metrics=None, predictions=None, forecast_output=None):
    out = REPORTS / 'figures'
    out.mkdir(exist_ok=True)
    sns.set_theme(style='whitegrid', palette=['#0d7484', '#f09256', '#405580'])
    plt.rcParams.update({'figure.dpi': 130, 'axes.spines.top': False, 'axes.spines.right': False})
    def save(name, title, xlabel, ylabel, draw, size=(11, 5)):
        fig, ax = plt.subplots(figsize=size, layout='constrained')
        draw(ax)
        ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
        fig.savefig(out / name, bbox_inches='tight')
        plt.close(fig)
    monthly = tables['monthly']
    save('01_monthly_delay.png', 'Reported US domestic scope | monthly late-arrival share, 2018–2025', '', 'Late arrivals / reported flights (%)',
         lambda ax: ax.plot(monthly.index, monthly.delay_pct, color='#0d7484'))
    save('02_monthly_volume.png', 'Reported flight volume | 2018–2025 (COVID disruption visible)', '', 'Reported flights (millions)',
         lambda ax: ax.fill_between(monthly.index, monthly.arr_flights/1e6, color='#0d7484', alpha=.75))
    carrier = tables['carrier'].query('arr_flights >= 10000').sort_values('delay_pct')
    save('03_carrier_comparison.png', 'Carrier late-arrival shares | 2018–2025, minimum 10,000 flights', 'Late arrivals / reported flights (%)', 'Carrier code (airport mix differs)',
         lambda ax: ax.barh(carrier.index, carrier.delay_pct, color='#0d7484'), size=(11, 8))
    airport = tables['airport'].nlargest(20, 'arr_flights').sort_values('delay_pct')
    save('04_airport_comparison.png', '20 largest airports by reported volume | 2018–2025', 'Late arrivals / reported flights (%)', 'Arrival airport code',
         lambda ax: ax.barh(airport.index, airport.delay_pct, color='#405580'), size=(11, 7))
    heat = aggregate(df, ['year', 'month']).delay_pct.unstack()
    save('05_seasonality_heatmap.png', 'Late-arrival share by year and month | reported scope', 'Month', 'Year',
         lambda ax: sns.heatmap(heat, ax=ax, cmap='YlOrRd', annot=True, fmt='.1f', cbar_kws={'label': '% of reported flights'}), size=(13, 6))
    causes = df[CAUSES].sum()
    causes.index = ['Carrier', 'Extreme weather', 'National aviation system', 'Security', 'Late aircraft']
    if df.cause_minutes_gap.sum() > 0:
        causes.loc['Unallocated / source gap'] = df.cause_minutes_gap.sum()
    save('06_delay_causes.png', 'Attributed delay-minute composition | 2018–2025 (association, not intervention effect)', 'Share of total recorded delay minutes (%)', '',
         lambda ax: ax.barh(causes.sort_values().index, causes.sort_values()/df.arr_delay.sum()*100, color='#0d7484'))
    if difference is not None:
        save('07_paired_seasons.png', 'Matched airports | summer minus autumn late share, 2023–2025', 'Percentage-point difference (equal airport weighting)', 'Airport (top 30 by 2018–2022 volume)',
             lambda ax: (ax.barh(difference.sort_values().index, difference.sort_values(), color='#f09256'), ax.axvline(0, color='black', lw=1)), size=(11, 9))
        save('11_assumptions_qq.png', 'Paired-test assumption diagnostic | airport seasonal differences', 'Theoretical normal quantiles', 'Ordered percentage-point differences',
             lambda ax: stats.probplot(difference, dist='norm', plot=ax))
    if prediction_metrics is not None:
        p = prediction_metrics[prediction_metrics.weighting.str.startswith('target')]
        save('08_prediction_comparison.png', '2025 held-out carrier-airport-month prediction | volume-weighted error', '', 'Mean absolute error (percentage points)',
             lambda ax: ax.bar(p.model, p.mae_pp, color=['#405580', '#0d7484']))
    def forecast_plot(ax):
        for col, name, color in [('actual', 'Actual', '#202c39'), ('seasonal_naive', 'Seasonal naive', '#f09256'), ('ets', 'ETS candidate', '#0d7484')]:
            ax.plot(forecast_output.index, forecast_output[col]*100, marker='o', label=name, color=color)
        ax.fill_between(forecast_output.index, forecast_output.ets_lower*100, forecast_output.ets_upper*100, alpha=.12, color='#0d7484', label='Illustrative validation-error band')
        ax.legend(fontsize=8)
    if forecast_output is not None:
        save('09_forecast.png', 'Fixed-origin forecast for 2025 | observations only through September 2024', '', 'National late-arrival share (%)', forecast_plot, size=(12, 6))
    save('10_volume_risk.png', 'Airport exposure | 2018–2025, airports with ≥10,000 reported flights', 'Reported flights (log scale)', 'Late arrivals / reported flights (%)',
         lambda ax: (ax.scatter(tables['airport'].query('arr_flights >= 10000').arr_flights,
                               tables['airport'].query('arr_flights >= 10000').delay_pct, alpha=.6, color='#0d7484'), ax.set_xscale('log')))


def sql_analysis(df):
    with sqlite3.connect(':memory:') as connection:
        df.to_sql('delays', connection, index=False)
        sql = (ROOT / 'sql/analysis.sql').read_text()
        queries = [statement.strip() for statement in sql.split(';') if statement.strip()]
        for i, query in enumerate(queries, 1):
            pd.read_sql_query(query, connection).to_csv(REPORTS / f'sql_result_{i}.csv', index=False)
        total = connection.execute('SELECT SUM(arr_flights), SUM(arr_del15) FROM delays').fetchone()
    if not np.allclose(total, [df.arr_flights.sum(), df.arr_del15.sum()]):
        raise ValueError('SQL / Pandas totals mismatch')


def run():
    df, audit = audit_and_clean()
    tables, metrics = kpi_tables(df)
    test, difference = seasonal_test(df)
    prediction_metrics, predictions, prediction_design = prediction_analysis(df)
    forecast_metrics, forecast_output, forecast_design = forecasting(tables['monthly'])
    charts(df, tables, difference, prediction_metrics, predictions, forecast_output)
    sql_analysis(df)
    # Imported late to keep statistical functions independently usable.
    from src.reporting import write_reports
    write_reports(audit, metrics, test, tables, prediction_metrics, prediction_design,
                  forecast_metrics, forecast_design)
    print(json.dumps({'audit_rows': audit['raw_rows'], 'clean_rows': len(df), 'metrics': metrics,
                      'seasonal_difference_pp': test['difference_pp']}, indent=2))
    print(prediction_metrics.to_string(index=False))
    print(forecast_metrics.to_string(index=False))
    return df, tables


if __name__ == '__main__':
    run()
