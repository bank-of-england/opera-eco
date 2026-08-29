---
name: forecast-decomp
description: Use this skill when working with the `news_decomp` Python package for real-time nowcast decomposition analysis.
module-package: news_decomp
module-version: "0.0.7"
---

# news_decomp

`news_decomp` validates a long-format decomposition table and exposes one `NewsData` object. `NewsData` inherits `NewsAnalysis`, `NewsPlots`, and `NewsReport`.

## Package surface

The package root exports only the data container:

```python
__all__ = ["NewsData"]
from news_decomp import NewsData
from news_decomp.sample import (
    simulate,
    fit_ols,
    build_decompositions,
    build_vintages,
    snapshot,
    plot,
    plot_vintage,
)
from news_decomp.schema import REVISION_SOURCES, decomposition_schema
```

The sample and schema imports above are submodule imports. The root does not export the analysis, plotting, reporting, sample, or schema names.

## decompositions schema

`NewsData(df)` validates with the strict `decomposition_schema`. Extra columns are rejected. The table has exactly these fields:

| field | type | presence | contract |
| --- | --- | --- | --- |
| `variable` | str | required | Target variable name. |
| `date` | datetime64[ns] | required | Target period/date. |
| `forecast_horizon` | int | required | Horizon supplied by the forecaster. |
| `frequency` | str | required | `Q` or `M`. |
| `source` | str | required | Forecast source/model name. |
| `vintage_date` | datetime64[ns] | required | Information vintage. |
| `base_vintage_date` | datetime64[ns] | nullable | Null for level rows; previous vintage for revision rows. |
| `decomposition` | str | required | `level` or `revision`. |
| `component` | str | required | Indicator/component name. |
| `revision_source` | str | nullable | Null for level rows; `news`, `reestimation`, or `interaction` for revision rows. |
| `contribution` | float | required | Non-null contribution. |
| `weight` | float | nullable | Optional coefficient/factor. |
| `news` | float | nullable | Optional data surprise/factor. |
| `forecast_metric` | str | required | Metric label, such as `levels`. |

The schema rules are:

- `frequency` is restricted to `Q` and `M`; `decomposition` is restricted to
    `level` and `revision`.
- Level rows require `base_vintage_date` to be null and `revision_source` to
    be null. Revision rows require `base_vintage_date` to be set and
    `revision_source` to be set.
- `revision_source` values are `news`, `reestimation`, or `interaction`.
- `forecast_metric` is required; it is not optional.
- `contribution = weight * news` when both factors are present. Either factor
    may be null, in which case that identity is not checked for the row.

Level rows require `base_vintage_date` to be null. Revision rows require `base_vintage_date` to be set and `revision_source` to be set.

level rows require `base_vintage_date` to be null revision rows require `base_vintage_date` to be set revision rows require `revision_source` to be set level rows require `revision_source` to be null

`NewsData.validate(df) -> pd.DataFrame` returns the validated frame and raises `pandera.errors.SchemaError` for schema violations. `contribution` is non-null and cannot be null.

## NewsData and analysis

These are public methods on `NewsData`, including the inherited mixin methods. The standalone source signatures are:

`NewsData(df)` `validate(df) -> pd.DataFrame` `summary() -> None`

### Forecast accuracy

`forecasts(variable=None, source=None) -> pd.DataFrame` `rmse(realised, variable=None, source=None) -> float` `mae(realised, variable=None, source=None) -> float` `accuracy_over_time(realised, variable=None, source=None) -> pd.DataFrame`

`forecasts` sums level contributions by `variable`, `date`, `forecast_horizon`, `source`, and `vintage_date`, returning those keys plus `forecast`. `realised` may be a `pd.Series` indexed by date or a `pd.DataFrame` containing `date`, `value`, and optionally `variable`. `accuracy_over_time` returns `vintage_date`, `rmse`, and `mae`.

### Indicator metrics

`marginal_contributions(variable=None, source=None) -> pd.DataFrame` `signal_magnitude(variable=None, source=None) -> pd.Series` `hit_rate(realised, variable=None, source=None) -> pd.Series` `error_improvement(realised, variable=None, source=None) -> pd.Series`

`marginal_contributions` returns the forecast group keys, `component`, and `contribution` for level rows. `signal_magnitude` is the mean absolute level contribution. `hit_rate` is the percentage of observations where removing a component makes absolute error worse. `error_improvement` is the mean reduction in absolute error when the component is retained. The two Series are indexed by `component`.

### Timing and information density

`timing_decomposition(n_obs, variable=None, source=None) -> pd.DataFrame` `information_density(pub_delays, n_obs=None, variable=None, source=None) -> pd.DataFrame`

`n_obs` contains `component`, `vintage_date`, and `n`. The timing result has `component`, `alpha`, and `beta`, where `alpha` is intrinsic content and `beta` is the timing premium. `pub_delays` is a dict or Series mapping component to publication delay in weeks. Information density returns `component`, `v_abs`, `w`, and `density`; with `n_obs` it also returns `alpha` and `density_star`.

### Real-time and revision metrics

`revision_predictability(realised_vintages, variable=None, source=None) -> pd.DataFrame` `news_vs_noise_r2(realised_first, realised_final, variable=None, source=None) -> pd.Series` `realtime_error_improvement(realised_final, variable=None, source=None) -> pd.Series` `vintage_revision_contribution(variable=None, source=None) -> pd.DataFrame`

`realised_vintages` is an ordered mapping from labels to Series or DataFrames. `revision_predictability` returns one `component` column and one percentage column for each consecutive vintage pair. `news_vs_noise_r2` returns a Series of component partial R-squared values. `realtime_error_improvement` compares against the final realised target. `vintage_revision_contribution` returns `component`, `new_data_contribution`, and `revised_data_contribution`, using `news` versus `reestimation` plus `interaction` rows.

### Nowcast and release analysis

`nowcast_evolution(date=None, variable=None, source=None) -> pd.DataFrame` `raw_revision_contributions(date=None, variable=None, source=None) -> pd.DataFrame` `revision_evolution(date=None, variable=None, source=None) -> pd.DataFrame` `revision_impacts(date=None, vintage_date=None, variable=None, source=None) -> pd.DataFrame` `cumulative_revision_impacts(date=None, variable=None, source=None) -> pd.DataFrame` `release_table_data(date=None, variable=None, source=None) -> pd.DataFrame` `indicator_table(realised, n_obs=None, pub_delays=None, variable=None, source=None) -> pd.DataFrame` `indicator_table_over_time(realised, min_periods=4, variable=None, source=None) -> pd.DataFrame`

The result columns are:

- `nowcast_evolution`: `vintage_date`, `nowcast`.
- `raw_revision_contributions`: `base_vintage_date`, `vintage_date`,
    `component`, `contribution`. It first-differences level contributions, so
    components sum exactly to the change in the nowcast.
- `revision_evolution`: `vintage_date`, `cumulative_revision`, summing news
    contributions over vintages.
- `revision_impacts`: `component`, `impact`, `revision_source`, sorted by
    absolute impact. If news rows exist for the selection they are used;
    otherwise all revision sources are aggregated.
- `cumulative_revision_impacts`: `component`, `cumulative_impact`, excluding
    `intercept` and `residual`. With no revision rows it falls back to the latest
    level contributions.
- `release_table_data`: `vintage_date`, `component`, `news`, `weight`,
    `contribution`, `cumulative_nowcast`.
- `indicator_table`: component-indexed columns `Signal magnitude`,
    `Directional accuracy`, `Error improvement`, `Intrinsic content`,
    `Timing premium`, `Information density`, and `Information density*`.
    Missing optional inputs produce null values.
- `indicator_table_over_time`: `vintage_date`, `component`, `Signal magnitude`,
    `Directional accuracy`, and `Error improvement`, computed on an expanding
    vintage window.

For methods that validate a target date, `date=None` selects the maximum value of `df["date"]`; `variable=None` and `source=None` select the first available value for that target-specific view. Methods that aggregate metrics accept null selectors as an all-variable/all-source filter.

## NewsPlots

The public plotting methods are also methods of `NewsData`:

`plot_accuracy(realised, variable=None, source=None, show=True)` `plot_contributions(variable=None, source=None, vintage_date=None, show=True)` `plot_signal_magnitude(variable=None, source=None, show=True)` `plot_hit_rate(realised, variable=None, source=None, show=True)` `plot_error_improvement(realised, variable=None, source=None, show=True)` `plot_timing_decomposition(n_obs, variable=None, source=None, show=True)` `plot_indicators_over_time(realised, min_periods=4, variable=None, source=None, show=True)` `plot_nowcast_evolution(date=None, variable=None, source=None, ax=None, show=True, figsize=(10, 5)) -> tuple[Any, Any]` `plot_contributions_by_vintage(date=None, variable=None, source=None, ax=None, show=True, figsize=(10, 5)) -> tuple[Any, Any]` `plot_revision_evolution(date=None, variable=None, source=None, ax=None, show=True, figsize=(10, 5)) -> tuple[Any, Any]` `plot_revision_contributions_by_vintage(date=None, variable=None, source=None, ax=None, show=True, figsize=(10, 5)) -> tuple[Any, Any]` `plot_raw_revision_contributions(date=None, variable=None, source=None, ax=None, show=True, figsize=(10, 5), x_order=None) -> tuple[Any, Any]` `plot_nowcast_contributions(date=None, variable=None, source=None, ax=None, show=True, figsize=(10, 5), x_order=None) -> tuple[Any, Any]` `plot_revision_by_source(date=None, variable=None, source=None, ax=None, show=True, figsize=(10, 5)) -> tuple[Any, Any]` `plot_revision_impacts(date=None, variable=None, source=None, ax=None, show=True, figsize=(10, 5)) -> tuple[Any, Any]` `plot_contribution_decomposition(variable=None, source=None, ax=None, show=True, figsize=(12, 6), n_dates=10) -> tuple[Any, Any]`

Every public plot method returns `(fig, ax)` on normal data; the basic methods return an axes array when they draw multiple panels. `plot_indicators_over_time` returns `(None, None)` for an empty history. `ax=` embeds a plot and `show=False` suppresses display. The nowcast panels use integer positions for uneven vintage dates.

`ax=` embeds the plot and `show=False` suppresses display.

## Reporting

`data_flow_table(n_dates=None, variable=None, source=None) -> pd.DataFrame` `summary_table(variable=None, source=None, target_date=None) -> pd.DataFrame` `report(variable=None, source=None, target_date=None, show=True, figsize=(12, 12)) -> tuple[Any, dict[str, Any]]`

`data_flow_table` returns columns `Model Update`, `Data Release`, `Target Quarter`, `Series`, `Data Revision`, `Impact (pp)`, and `Nowcast (%)`. `summary_table` returns `Indicator`, `Total Impact (pp)`, `Avg |Impact|`, `Releases`, and `Direction`. `data_flow_table` validates `variable` and `source` but currently does not filter its level and revision frames by those selectors; this implementation caveat remains in the current source.

data_flow_table validates `variable` and `source` but currently does not filter

`report` returns a figure and an axes dictionary with exactly these two panel keys: `nowcast_contributions` and `revision_contributions`. It also prints the nowcast summary, indicator summary, and data flow table. Its default figure size is `(12, 12)`.

## Sample API

The sample submodule provides these public functions:

`simulate(seed=SEED, sigma_y=SIGMA_Y, x_imputation=None) -> dict[str, pd.DataFrame]` `fit_ols(truth) -> pd.Series` `build_decompositions(data, source='ols_nowcast') -> pd.DataFrame` `build_vintages(data, source='ols_nowcast') -> dict[str, pd.DataFrame]` `snapshot(data, vintage_date, window=12) -> pd.DataFrame` `plot(data, show=True, savepath=None)` `plot_vintage(data, vintage_date, window=12, show=True, savepath=None)`

`simulate` returns keys `truth`, `releases`, `nowcasts`, `coefficients`, `fitted_coefficients`, `decompositions`, and `vintages`. `fitted_coefficients` contains the full-truth OLS fit. The nested `vintages` mapping contains `result["vintages"]["outturns"]` and `result["vintages"]["forecasts"]`. The mapping keys are "truth", "releases", "nowcasts", "coefficients", "fitted_coefficients", "decompositions", and "vintages". `decompositions` is schema-valid, while `build_vintages` returns the two evaluation tables. `snapshot` returns `date`, `X1`, `X2`, `y`, and `y_nowcast`.

The simulation uses target `y` with quarterly X1/X2 signals, real-time release rows, and coefficient re-estimation. `x_imputation` accepts `None`, `"zero"`, or `"last"` for an unavailable current-quarter regressor.

## Architecture and usage notes

`NewsData` stores the validated frame as `data.df`. The analysis methods use level rows for forecasts and indicator metrics, and revision rows for revision-specific metrics. Revision sources distinguish new data, coefficient re-estimation, and their interaction. `raw_revision_contributions` is the reconciling level-difference view; `revision_impacts` is the source-attributed revision view and need not have the same sum.

Use the exact local package APIs above. Legacy styling and vintage-signal helpers are not part of the current package surface.

<!-- BEGIN GENERATED API -->
## API

```json
{
  "exports": {
    "news_decomp": [
      "NewsData"
    ]
  },
  "package": "news_decomp",
  "signatures": {
    "news_decomp.NewsData": "(df: pandas.DataFrame)"
  },
  "version": "0.0.7"
}
```
<!-- END GENERATED API -->
