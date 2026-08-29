---
name: forecast-evaluation
description: Use this skill when working with the `forecast_evaluation` Python package.
module-package: forecast_evaluation
module-version: "0.1.13"
---

# forecast_evaluation

`forecast_evaluation` evaluates real-time point and density economic forecasts across forecast vintages. It supports quarterly (`Q`) and monthly (`M`) data, vintage-aware outturn revisions, and intra-period nowcasts.

## Imports and public boundary

The package root exports the following public API:

```python
import forecast_evaluation as fe

from forecast_evaluation import (
    create_outturn_revisions,
    add_random_walk_forecasts,
    add_ar_p_forecasts,
    ForecastData,
    NowcastData,
    DensityForecastData,
    create_sample_forecasts,
    create_sample_nowcast_forecasts,
    create_sample_nowcast_outturns,
    create_sample_outturns,
    bias_analysis,
    blanchard_leigh_horizon_analysis,
    compare_to_benchmark,
    compute_accuracy_statistics,
    compute_intra_period_accuracy,
    compute_intra_period_bias,
    create_comparison_table,
    diebold_mariano_table,
    fluctuation_tests,
    forecast_errors_correlation_analysis,
    revisions_errors_correlation_analysis,
    revision_predictability_analysis,
    rolling_analysis,
    strong_efficiency_analysis,
    weak_efficiency_analysis,
    plot_accuracy,
    plot_average_revision_by_period,
    plot_blanchard_leigh_ratios,
    plot_compare_to_benchmark,
    plot_correlation_heatmap,
    plot_strong_efficiency,
    plot_forecast_error_density,
    plot_forecast_errors,
    plot_forecast_errors_by_horizon,
    plot_hedgehog,
    plot_intra_period_accuracy,
    plot_intra_period_bias,
    plot_outturn_revisions,
    plot_outturns,
    plot_radar,
    plot_rolling_bias,
    plot_rolling_correlation,
    plot_rolling_relative_accuracy,
    plot_bias_by_horizon,
    plot_nowcasts,
    plot_vintage,
    plot_errors_across_time,
    covid_filter,
    filter_fer_variables,
    filter_k,
    reconstruct_id_cols_from_unique_id,
)
```

These are canonical subpackage exports, not root-package imports:

```python
from forecast_evaluation.tests import TestResult, diebold_mariano_test
from forecast_evaluation.visualisations import apply_theme, create_themed_figure
from forecast_evaluation.core import build_main_table, create_revision_dataframe
```

The `forecast_evaluation.tests` package also exports the high-level analysis functions. The `visualisations` package owns plotting helpers and the `core` package owns table-building helpers.

## Input data

Point outturn records require `date`, `vintage_date`, `variable`, `frequency`, and `value` in the usual vintage-aware mode. Point forecast records in the canonical post-compatibility schema require `source` and the forecaster-supplied `forecast_horizon`. Legacy records missing `forecast_horizon` may have it derived from `target_minus_vintage` under deprecated compatibility behavior; new inputs should provide it explicitly. `metric` is optional and defaults to `levels`; supported metrics are `levels`, `pop`, and `yoy`. Extra forecast identifiers are supplied through `extra_ids`.

`target_minus_vintage` is derived from target date and forecast vintage. It is the calendar or vintage distance used by most evaluation tables. Internal tables use `unique_id` for the concatenated source and extra identifiers. A `ForecastData` instance should contain one frequency.

The required ordering is outturns before forecasts. Add outturns first, either in the constructor or with `add_outturns()`, and then call `add_forecasts()`. Both methods copy caller-provided DataFrames. With `data_check=True`, forecast consistency checks emit warnings rather than rejecting the data.

## ForecastData

```text
`ForecastData(outturns_data=None, forecasts_data=None, load_fer=False, *, extra_ids=None, metric='levels', compute_levels=True, data_check=True, outturn_vintages=True, default_k=None, first_forecast_horizon=None)`
```

`load_fer=True` loads the package's bundled Forecast Evaluation Report data. `compute_levels=True` derives level forecasts where the available history supports the requested transformations. `default_k` supplies the maturity when an evaluation call receives `k=None`; the class default is `data.default_k == 12`.

Common methods and properties include:

```text
data.add_outturns(df, metric="levels")
data.add_forecasts(
    df,
    extra_ids=None,
    metric="levels",
    compute_levels=True,
    data_check=True,
)
data.add_fer_data()
data.add_fer_outturns()
data.add_fer_forecasts()
data.filter_fer()
data.add_benchmarks(
    models="AR",
    variables=None,
    metric="levels",
    frequency=None,
    forecast_periods=13,
    max_lag=2,
    estimation_start_date=None,
    show_progress=False,
)
data.create_pseudo_vintages(fill_to, vintage_frequency="Q", publication_lags=None)
data.merge(other, compute_levels=True)
data.copy()
data.summary()
data.df
data.forecasts
data.outturns
data.id_columns
data.outturn_vintages
data.uses_intra_period_vintages
data.supports_outturn_revision_analysis
```

`add_forecasts()` uses an internal `_UNSET` sentinel when `first_forecast_horizon` is omitted. Omission preserves any previously stored compatibility value, while explicitly passing `None` clears the stored compatibility value. When `forecast_horizon` is present, `first_forecast_horizon` is ignored. The argument is deprecated; provide `forecast_horizon` explicitly for new data.

```text
`data.filter(start_date=None, end_date=None, start_vintage=None, end_vintage=None, variables=None, metrics=None, sources=None, frequencies=None, custom_filter=None)`
`data.run_dashboard(from_jupyter=False, host='127.0.0.1', port=8000)`
```

`filter() mutates` the stored filtered tables and returns `None`; use `data.copy()` first when the original data must be preserved.

### Outturns without vintages

`outturn_vintages=False` represents one final outturn per target date. In this mode, outturn `vintage_date` may be absent, the main table uses `k=0`, and `latest_vintage` is `NaT`. Revision-dependent operations such as `create_outturn_revisions()` and `plot_outturn_revisions()` raise an error. `plot_outturns` raises `ValueError` when `outturn_vintages=False` because vintage selection is unavailable. This setting does not mean that outturn records are always required to carry vintage information.

## Horizons, maturity, and filtering

Keep these related fields distinct:

- `forecast_horizon` is the forecaster-supplied information horizon. It is
    retained in forecast data and used by regression-based lag logic.
- `target_minus_vintage` is the derived calendar distance from forecast vintage
    to target. It can be negative for backcasts or publication-lag geometry.
- The analysis `horizon` is the calendar or vintage distance represented in
    result tables. `TestResult` metadata records its default measure as
    `target_minus_vintage`.

Evaluation functions with `k=None` resolve maturity through `data.default_k`. `filter_k() returns a DataFrame` and selects the requested maturity when available, otherwise the largest available maturity at or below it, or the earliest later maturity when necessary. It does not mutate the input frame.

```text
`filter_k(df, k=12, fill_k=True) -> pd.DataFrame`
```

The `horizon` argument in intra-period analysis is the analysis horizon filter; use `horizon`, not `forecast_horizon`, for those calls. The `forecast_horizon` keyword is a deprecated compatibility alias accepted by decorated legacy calls and should not be used for new code.

`first_forecast_horizon` is deprecated. New forecast inputs should provide an explicit `forecast_horizon` column. If it is missing, compatibility behavior derives a horizon from `target_minus_vintage` and emits a `FutureWarning`.

## NowcastData

`NowcastData` is a `ForecastData` subclass for multiple intra-period vintages, such as weekly forecasts for a quarterly target.

```text
`NowcastData(outturns_data=None, forecasts_data=None, *, extra_ids=None, metric='levels', compute_levels=True, data_check=True, default_k=None, first_forecast_horizon=None)`
```

The `NowcastData` default maturity is `0`. When forecasts are added, available outturn snapshots are aligned to each forecast vintage and a dense revision index `k` is created: post-release observations use `0, 1, 2, ...`, while pre-release snapshots use `-1, -2, ...`.

The main table includes `days_to_publication`, the distance from forecast vintage to selected outturn release. Intra-period functions also derive `days_to_period_end`; these axes differ when a publication lag exists and are rounded to the nearest seven days for grouping.

FER loaders, FER filtering, pseudo-vintage creation, and benchmark methods are unsupported for `NowcastData` and raise `NotImplementedError`. Efficiency and conventional outturn-revision analyses raise `ValueError` when the required vintage geometry is unavailable.

```text
`compute_intra_period_accuracy(data, variable, metric='levels', frequency='Q', horizon=None, statistic='rmse', k=None, axis='period_end') -> pd.DataFrame`
`compute_intra_period_bias(data, variable, metric='levels', frequency='Q', horizon=None, k=None, axis='period_end') -> pd.DataFrame`
```

`axis="period_end"` groups by `days_to_period_end`; `axis="publication"` groups by `days_to_publication`. These functions return DataFrames containing identifiers, the selected axis, `value`, and `se`.

## DensityForecastData

Density forecasts require a `quantile` column with values in `[0, 1]`.

```text
`DensityForecastData(outturns_data=None, forecasts_data=None, load_fer=False, extra_ids=None, compute_levels=True)`
```

```text
density = fe.DensityForecastData(outturns_data=outturns, forecasts_data=density_df)
density.add_density_forecasts(df, extra_ids=None)
density.density_forecasts
density.sample_from_density(n_samples=10000, random_state=None)
density.to_point_forecast(method="median")
density.plot_density_vintage(variable="gdpkp", vintage_date="2020-01-01")
```

`sample_from_density()` returns a DataFrame of sampled values. In `to_point_forecast()`, `median` uses the 0.5 quantile and a numeric string selects the nearest available quantile. The mean path is not implemented: mean is currently `NotImplementedError`, so `method="mean"` raises that exception rather than estimating a mean. Median and numeric conversion paths currently mutate through `add_forecasts()` without explicitly returning the object; this is a known source/runtime ambiguity.

## Statistical analysis

Except for the tabular functions listed below, analysis functions return `TestResult`.

```text
`compute_accuracy_statistics(data, source=None, variable=None, k=None, same_date_range=True) -> TestResult`
`compare_to_benchmark(df, benchmark_model, statistic='rmse') -> pd.DataFrame`
`create_comparison_table(df, variable, metric, benchmark_model, frequency=None, statistic='rmse', horizons=[0, 1, 2, 4, 8, 12]) -> pd.DataFrame`
`diebold_mariano_table(data, benchmark_model, k=None, loss_function='mse', horizons=None) -> TestResult`
`compute_intra_period_accuracy(data, variable, metric='levels', frequency='Q', horizon=None, statistic='rmse', k=None, axis='period_end') -> pd.DataFrame`
`compute_intra_period_bias(data, variable, metric='levels', frequency='Q', horizon=None, k=None, axis='period_end') -> pd.DataFrame`
`rolling_analysis(data, window_size, analysis_func, analysis_args, start_vintage=None, end_vintage=None) -> TestResult`
`fluctuation_tests(data, window_size, test_func, test_args={}, start_vintage=None, end_vintage=None) -> TestResult`
```

`compare_to_benchmark` and `create_comparison_table` return `pd.DataFrame`. `compute_intra_period_accuracy` and `compute_intra_period_bias` return `pd.DataFrame`. The low-level `diebold_mariano_test` returns a `pd.Series` at runtime, despite its source annotation saying `dict`.

Analysis families include accuracy, bias, weak and strong efficiency, Blanchard-Leigh horizon tests, Diebold-Mariano comparisons, forecast-error and revision correlations, revision predictability, rolling analyses, and fluctuation tests. Regression-based analyses apply their documented minimum observation and HAC requirements.

### TestResult

`TestResult` stores a copy of a result DataFrame and metadata such as test name, parameters, filters, date range, and `horizon_measure`.

```text
result.to_df()
result.summary()
result.describe()
result.to_csv(path=None)
result.filter(variable="gdpkp", source="mpr", horizon=0)
result.plot(**plot_options)
```

`TestResult.plot` routes supported result metadata to plotting helpers. `TestResult.filter` returns a new `TestResult` and does not mutate the original. It accepts `variable`, `source`, `horizon`, and result-column filters. `to_df()` also returns a copy. Its plot router supports accuracy, bias, efficiency, correlation, rolling, and fluctuation results; unsupported test metadata raises `NotImplementedError` or `ValueError` as appropriate.

## Plotting and dashboards

Plot methods conventionally use `return_plot=False` and display the figure. `return_plot=False` returns `None`. `return_plot=True` returns `(fig, ax)` or the corresponding axes array for a multi-panel plot. `plot_radar` supports `metrics`, `variables`, and `tests` modes. The canonical intra-period filter argument is `horizon`; `forecast_horizon` is a deprecated compatibility alias.

```text
`plot_accuracy(df, variable, metric, frequency=None, statistic='rmse', convert_to_percentage=False, return_plot=False)`
`plot_compare_to_benchmark(df, variable, metric, benchmark_model, frequency=None, statistic='rmse', return_plot=False)`
`plot_rolling_relative_accuracy(df, variable, horizons, return_plot=False)`
`plot_bias_by_horizon(df, variable, source, metric, frequency=None, convert_to_percentage=False, return_plot=False)`
`plot_rolling_bias(df, horizons, variable=None, source=None, convert_to_percentage=False, return_plot=False)`
`plot_blanchard_leigh_ratios(results, return_plot=False)`
`plot_strong_efficiency(results, return_plot=False)`
`plot_correlation_heatmap(df, variable, metric, horizon, frequency=None, cmap='RdBu_r', annotate=True, return_plot=False)`
`plot_rolling_correlation(df, variable, anchor_source, horizons, metric=None, frequency=None, return_plot=False)`
`plot_vintage(data, variable, vintage_date, forecast_source=None, outturn_start_date=None, frequency=None, metric='levels', k=12, convert_to_percentage=False, return_plot=False)`
`plot_hedgehog(data, variable, forecast_source, metric, frequency=None, k=12, date_start=None, convert_to_percentage=False, return_plot=False, releases=None)`
`plot_nowcasts(data, variable, target_date, forecast_source=None, frequency='Q', metric='levels', k=12, convert_to_percentage=False, return_plot=False)`
`plot_forecast_errors(data, variable, metric, source, vintage_date_forecast, frequency=None, k=12, convert_to_percentage=False, return_plot=False)`
`plot_forecast_errors_by_horizon(data, variable, source, metric, frequency=None, k=12, convert_to_percentage=False, return_plot=False)`
`plot_forecast_error_density(data, variable, horizon, metric, source, frequency=None, k=12, highlight_dates=None, highlight_vintages=None, return_plot=False)`
`plot_errors_across_time(data, variable, metric, error='raw', horizons=None, sources=None, frequency=None, k=12, ma_window=1, show_mean=True, convert_to_percentage=False, return_plot=False, custom_labels=None, existing_plot=None)`
`plot_outturn_revisions(data, variable, metric, frequency=None, k=12, fill_k=False, ma_window=1, start_date=None, end_date=None, convert_to_percentage=False, return_plot=False)`
`plot_outturns(data, variable, metric, frequency=None, k=12, fill_k=True, start_date=None, end_date=None, convert_to_percentage=False, return_plot=False)`
`plot_average_revision_by_period(data, source, variable, metric, frequency=None, return_plot=False)`
`plot_intra_period_accuracy(data, variable, metric='levels', frequency='Q', horizon=None, statistic='rmse', k=None, axis='period_end', convert_to_percentage=False, confidence_level=None, return_plot=False)`
`plot_intra_period_bias(data, variable, metric='levels', frequency='Q', horizon=None, k=None, axis='period_end', convert_to_percentage=False, confidence_level=None, return_plot=False)`
`plot_radar(df, mode, *, variable=None, variables=None, metric=None, horizon=None, frequency=None, statistic='rmse', k=12, test_type='accuracy', bias_type='mean', efficiency_type='revision_predictability', anchor_source=None, normalise=True, individual_scales=False, return_plot=False)`
```

The visualisation-only helpers are imported from their canonical package:

The nowcast plotting functions include `plot_intra_period_accuracy`, `plot_intra_period_bias`, and `plot_nowcasts`.

```python
from forecast_evaluation.visualisations import apply_theme, create_themed_figure
```

`matplotlib` and `shiny` are base dependencies of `forecast_evaluation`, not optional extras. Plotting uses `matplotlib`; `run_dashboard()` uses `shiny` and accepts `from_jupyter`, `host`, and `port`.

## FER data and benchmarks

```text
data = fe.ForecastData(load_fer=True)
data.filter_fer()
```

The bundled FER data is local to the package and does not fetch data at runtime. Typical variables include `gdpkp`, `cpisa`, `unemp`, and `aweagg`; typical sources include `mpr`, Compass, and BVAR series. Use `filter_fer_variables()` for DataFrame-level selection.

```text
data.add_benchmarks(
    models="AR",
    variables=None,
    metric="levels",
    frequency=None,
    forecast_periods=13,
    max_lag=2,
    estimation_start_date=None,
    show_progress=False,
)
```

`add_benchmarks()` adds rolling-origin AR(p) and random-walk sources. `max_lag` accepts `1` or `2`; `max_lag=1` skips BIC lag selection. The direct helpers `add_random_walk_forecasts()` and `add_ar_p_forecasts()` add the same baseline families to a `ForecastData` instance.

## Core helpers and utilities

```text
from forecast_evaluation.core import build_main_table, create_revision_dataframe
```

```text
`create_revision_dataframe(main_df, forecasts, k=12) -> pd.DataFrame`
```

`build_main_table()` joins forecasts to outturns, computes errors and maturity, and supports `outturn_vintages=False`. `create_outturn_revisions()` creates a revision table and requires vintage-aware outturns. Other root utilities are `covid_filter`, `filter_fer_variables`, `filter_k`, and `reconstruct_id_cols_from_unique_id`.

## Minimal workflows

```python
# skill-test: skip (requires full FER data and expensive evaluation workflows)
import forecast_evaluation as fe

data = fe.ForecastData(load_fer=True)
data.filter(variables=["gdpkp", "cpisa"])

accuracy = fe.compute_accuracy_statistics(data, k=None)
accuracy.plot(variable="cpisa", metric="yoy", statistic="rmse")

bias = fe.bias_analysis(data, source="mpr", k=None)
print(bias.to_df())
```

For custom data, add outturns before forecasts and supply explicit forecast horizons:

```text
data = fe.ForecastData(outturn_vintages=True)
data.add_outturns(outturns_df)
data.add_forecasts(forecasts_df, extra_ids=["model_family"])
```

For nowcasts, use the sample helpers or aligned outturn and forecast vintages:

```python
import forecast_evaluation as fe

now = fe.NowcastData(
    fe.create_sample_nowcast_outturns(),
    fe.create_sample_nowcast_forecasts(),
)
accuracy = fe.compute_intra_period_accuracy(now, "gdp", axis="period_end")
bias = fe.compute_intra_period_bias(now, "gdp", axis="publication")
```

<!-- BEGIN GENERATED API -->
## API

```json
{
  "exports": {
    "forecast_evaluation": [
      "DensityForecastData",
      "ForecastData",
      "NowcastData",
      "add_ar_p_forecasts",
      "add_random_walk_forecasts",
      "bias_analysis",
      "blanchard_leigh_horizon_analysis",
      "compare_to_benchmark",
      "compute_accuracy_statistics",
      "compute_intra_period_accuracy",
      "compute_intra_period_bias",
      "covid_filter",
      "create_comparison_table",
      "create_outturn_revisions",
      "create_sample_forecasts",
      "create_sample_nowcast_forecasts",
      "create_sample_nowcast_outturns",
      "create_sample_outturns",
      "diebold_mariano_table",
      "filter_fer_variables",
      "filter_k",
      "fluctuation_tests",
      "forecast_errors_correlation_analysis",
      "plot_accuracy",
      "plot_average_revision_by_period",
      "plot_bias_by_horizon",
      "plot_blanchard_leigh_ratios",
      "plot_compare_to_benchmark",
      "plot_correlation_heatmap",
      "plot_errors_across_time",
      "plot_forecast_error_density",
      "plot_forecast_errors",
      "plot_forecast_errors_by_horizon",
      "plot_hedgehog",
      "plot_intra_period_accuracy",
      "plot_intra_period_bias",
      "plot_nowcasts",
      "plot_outturn_revisions",
      "plot_outturns",
      "plot_radar",
      "plot_rolling_bias",
      "plot_rolling_correlation",
      "plot_rolling_relative_accuracy",
      "plot_strong_efficiency",
      "plot_vintage",
      "reconstruct_id_cols_from_unique_id",
      "revision_predictability_analysis",
      "revisions_errors_correlation_analysis",
      "rolling_analysis",
      "strong_efficiency_analysis",
      "weak_efficiency_analysis"
    ],
    "forecast_evaluation.core": [
      "add_ar_p_forecasts",
      "add_random_walk_forecasts",
      "build_main_table",
      "create_outturn_revisions",
      "create_revision_dataframe"
    ],
    "forecast_evaluation.tests": [
      "TestResult",
      "bias_analysis",
      "blanchard_leigh_horizon_analysis",
      "compare_to_benchmark",
      "compute_accuracy_statistics",
      "compute_intra_period_accuracy",
      "compute_intra_period_bias",
      "create_comparison_table",
      "diebold_mariano_table",
      "diebold_mariano_test",
      "fluctuation_tests",
      "forecast_errors_correlation_analysis",
      "revision_predictability_analysis",
      "revisions_errors_correlation_analysis",
      "rolling_analysis",
      "strong_efficiency_analysis",
      "weak_efficiency_analysis"
    ],
    "forecast_evaluation.visualisations": [
      "apply_theme",
      "create_themed_figure",
      "plot_accuracy",
      "plot_average_revision_by_period",
      "plot_bias_by_horizon",
      "plot_blanchard_leigh_ratios",
      "plot_compare_to_benchmark",
      "plot_correlation_heatmap",
      "plot_errors_across_time",
      "plot_forecast_error_density",
      "plot_forecast_errors",
      "plot_forecast_errors_by_horizon",
      "plot_hedgehog",
      "plot_intra_period_accuracy",
      "plot_intra_period_bias",
      "plot_nowcasts",
      "plot_outturn_revisions",
      "plot_outturns",
      "plot_radar",
      "plot_rolling_bias",
      "plot_rolling_correlation",
      "plot_rolling_relative_accuracy",
      "plot_strong_efficiency",
      "plot_vintage"
    ]
  },
  "package": "forecast_evaluation",
  "signatures": {
    "forecast_evaluation.DensityForecastData": "(outturns_data: pandas.DataFrame | None = None, forecasts_data: pandas.DataFrame | None = None, load_fer: bool | None = False, extra_ids: list[str] | None = None, compute_levels: bool = True)",
    "forecast_evaluation.ForecastData": "(outturns_data: pandas.DataFrame | None = None, forecasts_data: pandas.DataFrame | None = None, load_fer: bool | None = False, *, extra_ids: list[str] | None = None, metric: Literal['levels', 'pop', 'yoy'] = 'levels', compute_levels: bool = True, data_check: bool = True, outturn_vintages: bool = True, default_k: int | None = None, first_forecast_horizon: dict[str, int] | int | None = None)",
    "forecast_evaluation.NowcastData": "(outturns_data: pandas.DataFrame | None = None, forecasts_data: pandas.DataFrame | None = None, *, extra_ids: list[str] | None = None, metric: Literal['levels', 'pop', 'yoy'] = 'levels', compute_levels: bool = True, data_check: bool = True, default_k: int | None = None, first_forecast_horizon: dict[str, int] | int | None = None)",
    "forecast_evaluation.add_ar_p_forecasts": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str | collections.abc.Iterable[str] | None = None, metric: Literal['levels', 'diff', 'pop', 'yoy'] = 'levels', frequency: Literal['Q', 'M'] | collections.abc.Iterable[Literal['Q', 'M']] | None = None, forecast_periods: int = 13, max_lag: Literal[1, 2] = 2, *, estimation_start_date: pandas.Timestamp = Timestamp('1997-07-01 00:00:00'), show_progress: bool = False)",
    "forecast_evaluation.add_random_walk_forecasts": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str | collections.abc.Iterable[str] | None = None, metric: Literal['levels', 'pop', 'yoy'] = 'levels', frequency: Literal['Q', 'M'] | collections.abc.Iterable[Literal['Q', 'M']] | None = None, forecast_periods: int = 13, show_progress: bool = False) -> None",
    "forecast_evaluation.bias_analysis": "(data: forecast_evaluation.data.ForecastData.ForecastData, source: list[str] | str | None = None, variable: list[str] | str | None = None, k: int | None = None, same_date_range: bool = True, verbose: bool = False) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.blanchard_leigh_horizon_analysis": "(data: forecast_evaluation.data.ForecastData.ForecastData, source: str, outcome_variable: str, outcome_metric: Literal['levels', 'pop', 'yoy'], instrument_variable: str, instrument_metric: Literal['levels', 'pop', 'yoy'], horizons: numpy.ndarray = array([ 0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12]), j: int = 2, frequency: Literal['Q', 'M'] | None = None, k: int | None = None, alpha: float = 0.05) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.compare_to_benchmark": "(df: pandas.DataFrame, benchmark_model: str, statistic: Literal['rmse', 'rmedse', 'mean_abs_error'] = 'rmse') -> pandas.DataFrame",
    "forecast_evaluation.compute_accuracy_statistics": "(data: forecast_evaluation.data.ForecastData.ForecastData, source: list[str] | str | None = None, variable: list[str] | str | None = None, k: int | None = None, same_date_range: bool = True) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.compute_intra_period_accuracy": "(data: forecast_evaluation.data.ForecastData.ForecastData | pandas.DataFrame, variable: str, metric: Literal['levels', 'pop', 'yoy'] = 'levels', frequency: Literal['Q', 'M'] = 'Q', horizon: int | None = None, statistic: Literal['rmse', 'mae'] = 'rmse', k: int | None = None, axis: Literal['period_end', 'publication'] = 'period_end') -> pandas.DataFrame",
    "forecast_evaluation.compute_intra_period_bias": "(data: forecast_evaluation.data.ForecastData.ForecastData | pandas.DataFrame, variable: str, metric: Literal['levels', 'pop', 'yoy'] = 'levels', frequency: Literal['Q', 'M'] = 'Q', horizon: int | None = None, k: int | None = None, axis: Literal['period_end', 'publication'] = 'period_end') -> pandas.DataFrame",
    "forecast_evaluation.core.add_ar_p_forecasts": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str | collections.abc.Iterable[str] | None = None, metric: Literal['levels', 'diff', 'pop', 'yoy'] = 'levels', frequency: Literal['Q', 'M'] | collections.abc.Iterable[Literal['Q', 'M']] | None = None, forecast_periods: int = 13, max_lag: Literal[1, 2] = 2, *, estimation_start_date: pandas.Timestamp = Timestamp('1997-07-01 00:00:00'), show_progress: bool = False)",
    "forecast_evaluation.core.add_random_walk_forecasts": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str | collections.abc.Iterable[str] | None = None, metric: Literal['levels', 'pop', 'yoy'] = 'levels', frequency: Literal['Q', 'M'] | collections.abc.Iterable[Literal['Q', 'M']] | None = None, forecast_periods: int = 13, show_progress: bool = False) -> None",
    "forecast_evaluation.core.build_main_table": "(forecasts: pandas.DataFrame, outturns: pandas.DataFrame, id_columns: list[str], variables: list[str] | str | None = None, forecast_ids: list[str] | str | None = None, frequency: Literal['Q', 'M'] = 'Q', *, outturn_vintages: bool = True) -> pandas.DataFrame",
    "forecast_evaluation.core.create_outturn_revisions": "(data: forecast_evaluation.data.ForecastData.ForecastData) -> pandas.DataFrame",
    "forecast_evaluation.core.create_revision_dataframe": "(main_df: pandas.DataFrame, forecasts: pandas.DataFrame, k: int = 12) -> pandas.DataFrame",
    "forecast_evaluation.covid_filter": "(df: pandas.DataFrame) -> pandas.DataFrame",
    "forecast_evaluation.create_comparison_table": "(df: pandas.DataFrame, variable: str, metric: Literal['levels', 'pop', 'yoy'], benchmark_model: str, frequency: Literal['Q', 'M'] | None = None, statistic: Literal['rmse', 'rmedse', 'mse', 'mean_abs_error'] = 'rmse', horizons: list[int] = [0, 1, 2, 4, 8, 12]) -> pandas.DataFrame",
    "forecast_evaluation.create_outturn_revisions": "(data: forecast_evaluation.data.ForecastData.ForecastData) -> pandas.DataFrame",
    "forecast_evaluation.create_sample_forecasts": "() -> pandas.DataFrame",
    "forecast_evaluation.create_sample_nowcast_forecasts": "() -> pandas.DataFrame",
    "forecast_evaluation.create_sample_nowcast_outturns": "() -> pandas.DataFrame",
    "forecast_evaluation.create_sample_outturns": "() -> pandas.DataFrame",
    "forecast_evaluation.diebold_mariano_table": "(data, benchmark_model: str, k: int | None = None, loss_function: Literal['mse', 'mae'] = 'mse', horizons: list[int] | None = None) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.filter_fer_variables": "(df: pandas.DataFrame) -> pandas.DataFrame",
    "forecast_evaluation.filter_k": "(df: pandas.DataFrame, k: int = 12, fill_k: bool = True) -> pandas.DataFrame",
    "forecast_evaluation.fluctuation_tests": "(data: forecast_evaluation.data.ForecastData.ForecastData, window_size: int, test_func: <built-in function callable>, test_args: dict = {}, start_vintage: str | None = None, end_vintage: str | None = None) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.forecast_errors_correlation_analysis": "(data: forecast_evaluation.data.ForecastData.ForecastData, source: list[str] | str | None = None, variable: list[str] | str | None = None, k: int | None = None, same_date_range: bool = True, min_observations: int = 5) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.plot_accuracy": "(df: ForwardRef('TestResult') | pandas.DataFrame, variable: str, metric: Literal['levels', 'pop', 'yoy'], frequency: Literal['Q', 'M'] | None = None, statistic: Literal['rmse', 'rmedse', 'mse', 'mean_abs_error'] = 'rmse', convert_to_percentage: bool = False, return_plot: bool = False)",
    "forecast_evaluation.plot_average_revision_by_period": "(data, source, variable, metric, frequency=None, return_plot: bool = False)",
    "forecast_evaluation.plot_bias_by_horizon": "(df: ForwardRef('TestResult') | pandas.DataFrame, variable: str, source: str, metric: Literal['levels', 'pop', 'yoy'], frequency: Literal['Q', 'M'] | None = None, convert_to_percentage: bool = False, return_plot: bool = False)",
    "forecast_evaluation.plot_blanchard_leigh_ratios": "(results: ForwardRef('TestResult') | pandas.DataFrame, return_plot: bool = False)",
    "forecast_evaluation.plot_compare_to_benchmark": "(df: pandas.DataFrame, variable: str, metric: Literal['levels', 'pop', 'yoy'], benchmark_model: str, frequency: Literal['Q', 'M'] | None = None, statistic: Literal['rmse', 'rmedse', 'mean_abs_error'] = 'rmse', return_plot: bool = False)",
    "forecast_evaluation.plot_correlation_heatmap": "(df: ForwardRef('TestResult') | pandas.DataFrame, variable: str, metric: Literal['levels', 'pop', 'yoy'], horizon: int, frequency: Literal['Q', 'M'] | None = None, cmap: str = 'RdBu_r', annotate: bool = True, return_plot: bool = False)",
    "forecast_evaluation.plot_errors_across_time": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, metric: Literal['levels', 'pop', 'yoy'], error: Literal['raw', 'absolute', 'squared'] = 'raw', horizons: int | list[int] | None = None, sources: list[str] | str | None = None, frequency: Literal['Q', 'M'] | None = None, k: int = 12, ma_window: int = 1, show_mean: bool = True, convert_to_percentage: bool = False, return_plot: bool = False, custom_labels: dict | None = None, existing_plot: tuple | None = None) -> tuple | None",
    "forecast_evaluation.plot_forecast_error_density": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, horizon: int, metric: Literal['levels', 'pop', 'yoy'], source: str, frequency: Literal['Q', 'M'] | None = None, k: int = 12, highlight_dates: list[str] | str | None = None, highlight_vintages: list[str] | str | None = None, return_plot: bool = False)",
    "forecast_evaluation.plot_forecast_errors": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, metric: Literal['levels', 'pop', 'yoy'], source: str, vintage_date_forecast: str, frequency: Literal['Q', 'M'] | None = None, k: int = 12, convert_to_percentage: bool = False, return_plot: bool = False)",
    "forecast_evaluation.plot_forecast_errors_by_horizon": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, source: list[str] | str, metric: Literal['levels', 'pop', 'yoy'], frequency: Literal['Q', 'M'] | None = None, k: int = 12, convert_to_percentage: bool = False, return_plot: bool = False)",
    "forecast_evaluation.plot_hedgehog": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, forecast_source: str, metric: Literal['levels', 'pop', 'yoy'], frequency: Literal['Q', 'M'] | None = None, k: int = 12, date_start: datetime.date | str | None = None, convert_to_percentage: bool = False, return_plot: bool = False, releases: list[int] | None = None) -> tuple[matplotlib.figure.Figure, matplotlib.axes._axes.Axes] | None",
    "forecast_evaluation.plot_intra_period_accuracy": "(data: ForwardRef('ForecastData') | pandas.DataFrame, variable: str, metric: Literal['levels', 'pop', 'yoy'] = 'levels', frequency: Literal['Q', 'M'] = 'Q', horizon: int | None = None, statistic: Literal['rmse', 'mae'] = 'rmse', k: int | None = None, axis: Literal['period_end', 'publication'] = 'period_end', convert_to_percentage: bool = False, confidence_level: int | None = None, return_plot: bool = False)",
    "forecast_evaluation.plot_intra_period_bias": "(data: ForwardRef('ForecastData') | pandas.DataFrame, variable: str, metric: Literal['levels', 'pop', 'yoy'] = 'levels', frequency: Literal['Q', 'M'] = 'Q', horizon: int | None = None, k: int | None = None, axis: Literal['period_end', 'publication'] = 'period_end', convert_to_percentage: bool = False, confidence_level: int | None = None, return_plot: bool = False)",
    "forecast_evaluation.plot_nowcasts": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, target_date: str | pandas.Timestamp, forecast_source: list[str] = None, frequency: Literal['Q', 'M'] = 'Q', metric: Literal['levels', 'pop', 'yoy'] = 'levels', k: int = 12, convert_to_percentage: bool = False, return_plot: bool = False) -> None",
    "forecast_evaluation.plot_outturn_revisions": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, metric: Literal['levels', 'pop', 'yoy'], frequency: Literal['Q', 'M'] | None = None, k: int | list[int] = 12, fill_k: bool = False, ma_window: int = 1, start_date: datetime.date | str | None = None, end_date: datetime.date | str | None = None, convert_to_percentage: bool = False, return_plot: bool = False)",
    "forecast_evaluation.plot_outturns": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, metric: Literal['levels', 'pop', 'yoy'], frequency: Literal['Q', 'M'] | None = None, k: int | list[int] = 12, fill_k: bool = True, start_date: datetime.date | str | None = None, end_date: datetime.date | str | None = None, convert_to_percentage: bool = False, return_plot: bool = False)",
    "forecast_evaluation.plot_radar": "(df: ForwardRef('ForecastData') | ForwardRef('TestResult') | pandas.DataFrame, mode: Literal['metrics', 'variables', 'tests'], *, variable: str | None = None, variables: list[str] | None = None, metric: str | None = None, horizon: int | None = None, frequency: Literal['Q', 'M'] | None = None, statistic: Literal['rmse', 'rmedse', 'mean_abs_error'] = 'rmse', k: int = 12, test_type: Literal['accuracy', 'bias', 'efficiency', 'correlation'] = 'accuracy', bias_type: Literal['mean', 'mz'] = 'mean', efficiency_type: Literal['revision_predictability', 'revisions_errors'] = 'revision_predictability', anchor_source: str | None = None, normalise: bool = True, individual_scales: bool = False, return_plot: bool = False)",
    "forecast_evaluation.plot_rolling_bias": "(df: pandas.DataFrame, horizons: collections.abc.Sequence[int], variable: str = None, source: str = None, convert_to_percentage: bool = False, return_plot: bool = False)",
    "forecast_evaluation.plot_rolling_correlation": "(df: ForwardRef('TestResult') | pandas.DataFrame, variable: str, anchor_source: str, horizons: int | list[int], metric: Literal['levels', 'pop', 'yoy'] | None = None, frequency: Literal['Q', 'M'] | None = None, return_plot: bool = False)",
    "forecast_evaluation.plot_rolling_relative_accuracy": "(df: pandas.DataFrame, variable: str, horizons: list[int], return_plot: bool = False)",
    "forecast_evaluation.plot_strong_efficiency": "(results: ForwardRef('TestResult') | pandas.DataFrame, return_plot: bool = False)",
    "forecast_evaluation.plot_vintage": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, vintage_date: str | pandas.Timestamp, forecast_source: list[str] | None = None, outturn_start_date: str | pandas.Timestamp | None = None, frequency: Literal['Q', 'M'] | None = None, metric: Literal['levels', 'pop', 'yoy'] = 'levels', k: int = 12, convert_to_percentage: bool = False, return_plot: bool = False) -> tuple[matplotlib.figure.Figure, matplotlib.axes._axes.Axes] | None",
    "forecast_evaluation.reconstruct_id_cols_from_unique_id": "(df: pandas.DataFrame, id_columns: list[str]) -> pandas.DataFrame",
    "forecast_evaluation.revision_predictability_analysis": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: list[str] | str | None = None, source: list[str] | str | None = None, frequency: Literal['Q', 'M'] | None = None, n_revisions: Annotated[int, Gt(gt=0)] = 5, same_date_range: bool = True) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.revisions_errors_correlation_analysis": "(data: forecast_evaluation.data.ForecastData.ForecastData, source: list[str] | str | None = None, variable: list[str] | str | None = None, k: int | None = None, same_date_range: bool = True) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.rolling_analysis": "(data: forecast_evaluation.data.ForecastData.ForecastData, window_size: int, analysis_func: <built-in function callable>, analysis_args: dict, start_vintage: str | None = None, end_vintage: str | None = None)",
    "forecast_evaluation.strong_efficiency_analysis": "(data: forecast_evaluation.data.ForecastData.ForecastData, source: str, outcome_variable: str, outcome_metric: Literal['levels', 'pop', 'yoy'], instrument_variable: str, instrument_metric: Literal['levels', 'pop', 'yoy'], horizons: numpy.ndarray = array([ 0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12]), j: int = 2, frequency: Literal['Q', 'M'] | None = None, k: int | None = None, alpha: float = 0.05) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.tests.TestResult": "(df: pandas.DataFrame, id_columns: list[str] | None = None, metadata: dict | None = None)",
    "forecast_evaluation.tests.bias_analysis": "(data: forecast_evaluation.data.ForecastData.ForecastData, source: list[str] | str | None = None, variable: list[str] | str | None = None, k: int | None = None, same_date_range: bool = True, verbose: bool = False) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.tests.blanchard_leigh_horizon_analysis": "(data: forecast_evaluation.data.ForecastData.ForecastData, source: str, outcome_variable: str, outcome_metric: Literal['levels', 'pop', 'yoy'], instrument_variable: str, instrument_metric: Literal['levels', 'pop', 'yoy'], horizons: numpy.ndarray = array([ 0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12]), j: int = 2, frequency: Literal['Q', 'M'] | None = None, k: int | None = None, alpha: float = 0.05) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.tests.compare_to_benchmark": "(df: pandas.DataFrame, benchmark_model: str, statistic: Literal['rmse', 'rmedse', 'mean_abs_error'] = 'rmse') -> pandas.DataFrame",
    "forecast_evaluation.tests.compute_accuracy_statistics": "(data: forecast_evaluation.data.ForecastData.ForecastData, source: list[str] | str | None = None, variable: list[str] | str | None = None, k: int | None = None, same_date_range: bool = True) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.tests.compute_intra_period_accuracy": "(data: forecast_evaluation.data.ForecastData.ForecastData | pandas.DataFrame, variable: str, metric: Literal['levels', 'pop', 'yoy'] = 'levels', frequency: Literal['Q', 'M'] = 'Q', horizon: int | None = None, statistic: Literal['rmse', 'mae'] = 'rmse', k: int | None = None, axis: Literal['period_end', 'publication'] = 'period_end') -> pandas.DataFrame",
    "forecast_evaluation.tests.compute_intra_period_bias": "(data: forecast_evaluation.data.ForecastData.ForecastData | pandas.DataFrame, variable: str, metric: Literal['levels', 'pop', 'yoy'] = 'levels', frequency: Literal['Q', 'M'] = 'Q', horizon: int | None = None, k: int | None = None, axis: Literal['period_end', 'publication'] = 'period_end') -> pandas.DataFrame",
    "forecast_evaluation.tests.create_comparison_table": "(df: pandas.DataFrame, variable: str, metric: Literal['levels', 'pop', 'yoy'], benchmark_model: str, frequency: Literal['Q', 'M'] | None = None, statistic: Literal['rmse', 'rmedse', 'mse', 'mean_abs_error'] = 'rmse', horizons: list[int] = [0, 1, 2, 4, 8, 12]) -> pandas.DataFrame",
    "forecast_evaluation.tests.diebold_mariano_table": "(data, benchmark_model: str, k: int | None = None, loss_function: Literal['mse', 'mae'] = 'mse', horizons: list[int] | None = None) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.tests.diebold_mariano_test": "(error_difference: pandas.Series, horizon: int) -> dict",
    "forecast_evaluation.tests.fluctuation_tests": "(data: forecast_evaluation.data.ForecastData.ForecastData, window_size: int, test_func: <built-in function callable>, test_args: dict = {}, start_vintage: str | None = None, end_vintage: str | None = None) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.tests.forecast_errors_correlation_analysis": "(data: forecast_evaluation.data.ForecastData.ForecastData, source: list[str] | str | None = None, variable: list[str] | str | None = None, k: int | None = None, same_date_range: bool = True, min_observations: int = 5) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.tests.revision_predictability_analysis": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: list[str] | str | None = None, source: list[str] | str | None = None, frequency: Literal['Q', 'M'] | None = None, n_revisions: Annotated[int, Gt(gt=0)] = 5, same_date_range: bool = True) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.tests.revisions_errors_correlation_analysis": "(data: forecast_evaluation.data.ForecastData.ForecastData, source: list[str] | str | None = None, variable: list[str] | str | None = None, k: int | None = None, same_date_range: bool = True) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.tests.rolling_analysis": "(data: forecast_evaluation.data.ForecastData.ForecastData, window_size: int, analysis_func: <built-in function callable>, analysis_args: dict, start_vintage: str | None = None, end_vintage: str | None = None)",
    "forecast_evaluation.tests.strong_efficiency_analysis": "(data: forecast_evaluation.data.ForecastData.ForecastData, source: str, outcome_variable: str, outcome_metric: Literal['levels', 'pop', 'yoy'], instrument_variable: str, instrument_metric: Literal['levels', 'pop', 'yoy'], horizons: numpy.ndarray = array([ 0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12]), j: int = 2, frequency: Literal['Q', 'M'] | None = None, k: int | None = None, alpha: float = 0.05) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.tests.weak_efficiency_analysis": "(data: forecast_evaluation.data.ForecastData.ForecastData, source: list[str] | str | None = None, variable: list[str] | str | None = None, k: int | None = None, same_date_range: bool = True, verbose: bool = False) -> forecast_evaluation.tests.results.TestResult",
    "forecast_evaluation.visualisations.apply_theme": "(fig, ax)",
    "forecast_evaluation.visualisations.create_themed_figure": "(nrows=1, ncols=1, **kwargs)",
    "forecast_evaluation.visualisations.plot_accuracy": "(df: ForwardRef('TestResult') | pandas.DataFrame, variable: str, metric: Literal['levels', 'pop', 'yoy'], frequency: Literal['Q', 'M'] | None = None, statistic: Literal['rmse', 'rmedse', 'mse', 'mean_abs_error'] = 'rmse', convert_to_percentage: bool = False, return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_average_revision_by_period": "(data, source, variable, metric, frequency=None, return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_bias_by_horizon": "(df: ForwardRef('TestResult') | pandas.DataFrame, variable: str, source: str, metric: Literal['levels', 'pop', 'yoy'], frequency: Literal['Q', 'M'] | None = None, convert_to_percentage: bool = False, return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_blanchard_leigh_ratios": "(results: ForwardRef('TestResult') | pandas.DataFrame, return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_compare_to_benchmark": "(df: pandas.DataFrame, variable: str, metric: Literal['levels', 'pop', 'yoy'], benchmark_model: str, frequency: Literal['Q', 'M'] | None = None, statistic: Literal['rmse', 'rmedse', 'mean_abs_error'] = 'rmse', return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_correlation_heatmap": "(df: ForwardRef('TestResult') | pandas.DataFrame, variable: str, metric: Literal['levels', 'pop', 'yoy'], horizon: int, frequency: Literal['Q', 'M'] | None = None, cmap: str = 'RdBu_r', annotate: bool = True, return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_errors_across_time": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, metric: Literal['levels', 'pop', 'yoy'], error: Literal['raw', 'absolute', 'squared'] = 'raw', horizons: int | list[int] | None = None, sources: list[str] | str | None = None, frequency: Literal['Q', 'M'] | None = None, k: int = 12, ma_window: int = 1, show_mean: bool = True, convert_to_percentage: bool = False, return_plot: bool = False, custom_labels: dict | None = None, existing_plot: tuple | None = None) -> tuple | None",
    "forecast_evaluation.visualisations.plot_forecast_error_density": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, horizon: int, metric: Literal['levels', 'pop', 'yoy'], source: str, frequency: Literal['Q', 'M'] | None = None, k: int = 12, highlight_dates: list[str] | str | None = None, highlight_vintages: list[str] | str | None = None, return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_forecast_errors": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, metric: Literal['levels', 'pop', 'yoy'], source: str, vintage_date_forecast: str, frequency: Literal['Q', 'M'] | None = None, k: int = 12, convert_to_percentage: bool = False, return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_forecast_errors_by_horizon": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, source: list[str] | str, metric: Literal['levels', 'pop', 'yoy'], frequency: Literal['Q', 'M'] | None = None, k: int = 12, convert_to_percentage: bool = False, return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_hedgehog": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, forecast_source: str, metric: Literal['levels', 'pop', 'yoy'], frequency: Literal['Q', 'M'] | None = None, k: int = 12, date_start: datetime.date | str | None = None, convert_to_percentage: bool = False, return_plot: bool = False, releases: list[int] | None = None) -> tuple[matplotlib.figure.Figure, matplotlib.axes._axes.Axes] | None",
    "forecast_evaluation.visualisations.plot_intra_period_accuracy": "(data: ForwardRef('ForecastData') | pandas.DataFrame, variable: str, metric: Literal['levels', 'pop', 'yoy'] = 'levels', frequency: Literal['Q', 'M'] = 'Q', horizon: int | None = None, statistic: Literal['rmse', 'mae'] = 'rmse', k: int | None = None, axis: Literal['period_end', 'publication'] = 'period_end', convert_to_percentage: bool = False, confidence_level: int | None = None, return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_intra_period_bias": "(data: ForwardRef('ForecastData') | pandas.DataFrame, variable: str, metric: Literal['levels', 'pop', 'yoy'] = 'levels', frequency: Literal['Q', 'M'] = 'Q', horizon: int | None = None, k: int | None = None, axis: Literal['period_end', 'publication'] = 'period_end', convert_to_percentage: bool = False, confidence_level: int | None = None, return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_nowcasts": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, target_date: str | pandas.Timestamp, forecast_source: list[str] = None, frequency: Literal['Q', 'M'] = 'Q', metric: Literal['levels', 'pop', 'yoy'] = 'levels', k: int = 12, convert_to_percentage: bool = False, return_plot: bool = False) -> None",
    "forecast_evaluation.visualisations.plot_outturn_revisions": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, metric: Literal['levels', 'pop', 'yoy'], frequency: Literal['Q', 'M'] | None = None, k: int | list[int] = 12, fill_k: bool = False, ma_window: int = 1, start_date: datetime.date | str | None = None, end_date: datetime.date | str | None = None, convert_to_percentage: bool = False, return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_outturns": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, metric: Literal['levels', 'pop', 'yoy'], frequency: Literal['Q', 'M'] | None = None, k: int | list[int] = 12, fill_k: bool = True, start_date: datetime.date | str | None = None, end_date: datetime.date | str | None = None, convert_to_percentage: bool = False, return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_radar": "(df: ForwardRef('ForecastData') | ForwardRef('TestResult') | pandas.DataFrame, mode: Literal['metrics', 'variables', 'tests'], *, variable: str | None = None, variables: list[str] | None = None, metric: str | None = None, horizon: int | None = None, frequency: Literal['Q', 'M'] | None = None, statistic: Literal['rmse', 'rmedse', 'mean_abs_error'] = 'rmse', k: int = 12, test_type: Literal['accuracy', 'bias', 'efficiency', 'correlation'] = 'accuracy', bias_type: Literal['mean', 'mz'] = 'mean', efficiency_type: Literal['revision_predictability', 'revisions_errors'] = 'revision_predictability', anchor_source: str | None = None, normalise: bool = True, individual_scales: bool = False, return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_rolling_bias": "(df: pandas.DataFrame, horizons: collections.abc.Sequence[int], variable: str = None, source: str = None, convert_to_percentage: bool = False, return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_rolling_correlation": "(df: ForwardRef('TestResult') | pandas.DataFrame, variable: str, anchor_source: str, horizons: int | list[int], metric: Literal['levels', 'pop', 'yoy'] | None = None, frequency: Literal['Q', 'M'] | None = None, return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_rolling_relative_accuracy": "(df: pandas.DataFrame, variable: str, horizons: list[int], return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_strong_efficiency": "(results: ForwardRef('TestResult') | pandas.DataFrame, return_plot: bool = False)",
    "forecast_evaluation.visualisations.plot_vintage": "(data: forecast_evaluation.data.ForecastData.ForecastData, variable: str, vintage_date: str | pandas.Timestamp, forecast_source: list[str] | None = None, outturn_start_date: str | pandas.Timestamp | None = None, frequency: Literal['Q', 'M'] | None = None, metric: Literal['levels', 'pop', 'yoy'] = 'levels', k: int = 12, convert_to_percentage: bool = False, return_plot: bool = False) -> tuple[matplotlib.figure.Figure, matplotlib.axes._axes.Axes] | None",
    "forecast_evaluation.weak_efficiency_analysis": "(data: forecast_evaluation.data.ForecastData.ForecastData, source: list[str] | str | None = None, variable: list[str] | str | None = None, k: int | None = None, same_date_range: bool = True, verbose: bool = False) -> forecast_evaluation.tests.results.TestResult"
  },
  "version": "0.1.13"
}
```
<!-- END GENERATED API -->
