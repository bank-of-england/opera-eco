---
name: forecast-combo
description: Use this skill when working with the `forecast_combo` Python package.
module-package: forecast_combo
module-version: "0.1.1"
---

# forecast_combo

`forecast_combo` combines point forecasts from multiple sources. It wraps a `ForecastData` instance from `forecast_evaluation`, estimates weights over real-time vintages, writes combined forecasts to its own data copy, and provides optional matplotlib plots and shiny dashboards.

## Install and quickstart

```sh
pip install forecast-combo
```

```python
# skill-test: skip (requires full FER data and expensive combination estimation)
import forecast_evaluation as fe
import forecast_combo as fc

data = fe.ForecastData(load_fer=True)
combo = fc.ForecastCombo(data)
combo.fit(
    sources=["mpr", "bvar unconditional"],
    variables=["gdpkp", "cpisa"],
    method=["average", "constrained_least_squares"],
    training_start="2016-01-01",
)
```

## Public API

The package root exports these names:

```python
from forecast_combo import (
    ForecastCombo,
    ComboSpec,
    get_weights,
    validate_spec_graph,
    SUPPORTED_METHODS,
    create_period_filter,
    heatmap_by_vintage,
    heatmap_by_horizon,
    line_plot_by_vintage,
    line_plot_by_horizon,
    bar_plot_by_vintage,
    bar_plot_by_horizon,
)
```

Combination functions are imported from `forecast_combo.combinations`:

```python
from forecast_combo.combinations import (
    average,
    least_squares,
    constrained_least_squares,
    rmse_weights,
    mse_weights,
    mae_weights,
    huber_weights,
)
```

`SUPPORTED_METHODS` is the tuple containing `average`, `least_squares`, `constrained_least_squares`, `rmse`, `mse`, `mae`, and `huber`.

These are standalone summaries of the public call signatures:

```text
`ForecastCombo(forecast_data)`
`ForecastCombo.fit(sources, variables, method='average', training_start=None, training_end=None, metric='pop', k=0, period_filter=None, window_size=None, discount_param=1.0, label=None, automatic_labelling=False, allow_partial_sources=True, print_warning=True) -> ForecastCombo`
`ForecastCombo.fit_hierarchical(specs, variables) -> ForecastCombo`
`ForecastCombo.run_combo_dashboard(host='127.0.0.1', port=8000) -> None`
`ForecastCombo.run_forecast_dashboard(host='127.0.0.1', port=8000) -> None`
`ComboSpec(name, sources, method='average', training_start=None, training_end=None, metric='pop', k=0, period_filter=None, window_size=None, discount_param=1.0, allow_partial_sources=True, print_warning=True)`
`ComboSpec.flatten_and_validate(raw_sources=None) -> list[ComboSpec]`
`validate_spec_graph(roots, raw_sources=None) -> list[ComboSpec]`
`get_weights(X, y, method, window_size=None, discount_param=1.0) -> tuple[np.ndarray, np.ndarray]`
`create_period_filter(start_period, end_period, freq) -> list[pd.Period]`
`average(X) -> np.ndarray`
`least_squares(X, y, window_size=None) -> tuple[np.ndarray, np.ndarray]`
`constrained_least_squares(X, y, window_size=None) -> np.ndarray`
`rmse_weights(X, y, window_size, discount_param=1.0) -> tuple[np.ndarray, np.ndarray]`
`mse_weights(X, y, window_size, discount_param=1.0) -> tuple[np.ndarray, np.ndarray]`
`mae_weights(X, y, window_size, discount_param=1.0) -> tuple[np.ndarray, np.ndarray]`
`huber_weights(X, y, window_size) -> np.ndarray`
```

## ForecastCombo

`ForecastCombo(forecast_data)` requires a `ForecastData` instance and calls `copy()` during construction. `combo.forecast_data` is the working copy, so a fit writes back to that copy rather than mutating the caller's data.

```text
combo.forecast_data
combo.weights
combo.supported_methods
```

`fit()` accepts a list of raw source names, one `ComboSpec`, or a mixed list of raw names and nested specifications. A method string fits one method; a list fits every requested method. It returns `self` for chaining.

`combo.weights` accumulates rows across each repeated fit call. `combo_label` identifies the complete fit configuration and is separate from the combined forecast `source`. With an explicit `label`, the combined forecast `source` uses that label. Without an explicit `label`, the source remains the method name (for example, `average`), while `combo_label` gets a deterministic configuration label. `automatic_labelling=True` writes metadata such as `combo_sources`, `discount_param`, `estimation_window_size`, and `period_filter` to combined forecasts.

The combined forecast write back stores `forecast_horizon` as the computed information horizon. The weight table uses `horizon` for vintage distance, so `forecast_horizon` is not a weight column. A repeated fit with a different configuration for the same forecast identity raises `ValueError` instead of silently merging results.

### Source availability

`allow_partial_sources=True` is the default. If a requested source is missing for a variable or target horizon, the fit uses the available subset and emits a warning when `print_warning=True`. With `allow_partial_sources=False`, a missing source raises `ValueError`. At least one source and enough usable observations are still required for a selected method. If a partial source is unavailable, the fit follows this same availability rule for the affected variable or target horizon.

### Outturn maturity and training options

For target period $t$, `k` requests the outturn release at $t + (k + 1)$ periods. Thus `k=0` is the first post-target release. Exact maturity is used when published; recent targets fall back to the most mature earlier release available at the estimation vintage. Later releases are never used.

`training_start` and `training_end` select estimation vintages. `period_filter` removes selected periods from the training sample. Use `create_period_filter("2020Q1", "2021Q4", freq="Q")` to create a list of `pandas.Period` values. `window_size` keeps the most recent observations and `None` uses an expanding sample.

## ComboSpec and hierarchical combinations

```text
from forecast_combo import ComboSpec

leaf = ComboSpec(
    name="benchmark_combo",
    sources=["mpr", "baseline ar(p) model"],
    method="average",
)
root = ComboSpec(
    name="conditional combo",
    sources=[leaf, "compass unconditional"],
    method="rmse",
    window_size=20,
)

combo.fit(sources=root, variables=["gdpkp"])
```

`source_names` resolves nested specifications to their names. `flatten_and_validate()` and `validate_spec_graph()` order nodes leaves first, then parents, and return shared nodes once. Validation rejects a cycle, duplicate names on distinct specifications, empty or invalid sources, and a specification name that collides with a raw forecast source. These checks raise `ValueError` or `TypeError` before a hierarchical fit changes data.

Each specification has one method. A plain `fit()` call may use a method list, but a `ComboSpec` has one method for an unambiguous output name. A mixed list fits nested nodes first and then the top-level conditional combo using the options passed to `fit()`.

`fit_hierarchical(specs, variables)` remains available for an ordered list, but it is deprecated. Prefer passing a nested root `ComboSpec` to `fit()`.

## Combination methods

| Method | Key | Constraints | Notes |
|---|---|---|---|
| Average | `average` | `w_i = 1/m` | No training |
| Inverse RMSE | `rmse` | `w_i >= 0`, sum = 1 | Discount and window support |
| Inverse MSE | `mse` | `w_i >= 0`, sum = 1 | Penalises large errors |
| Inverse MAE | `mae` | `w_i >= 0`, sum = 1 | Robust to outliers |
| Huber loss | `huber` | `w_i >= 0`, sum = 1 | Quadratic small, linear large |
| OLS | `least_squares` | none | Needs `T >= m` |
| Constrained LS | `constrained_least_squares` | `w_i >= 0`, sum = 1 | SciPy SLSQP |

`get_weights()` returns `(weights, std_error)`. `least_squares`, `rmse`, `mse`, and `mae` estimate weight standard errors when their requirements are met. `average`, `constrained_least_squares`, and `huber` do not estimate uncertainty and store `NaN` in `std_error`. OLS standard errors are also `NaN` for a rank-deficient design or a sample that is not larger than the number of sources.

`discount_param` applies exponential discounting to `rmse`, `mse`, and `mae`. It is ignored by `average`, `least_squares`, `constrained_least_squares`, and `huber`. With `discount_param=1.0`, all observations have equal weight.

## Weight visualisations

Plotting is optional and requires `matplotlib`. Every plot accepts `combo.weights`, filters by `model`, `method`, `variable`, and `combo_label`, and returns a `(Figure, np.ndarray)` pair. `y_axis` must be `model`, `method`, or `variable`. Vintage plots can also filter `horizon`.

```text
`heatmap_by_vintage(weights_df, y_axis='model', model=None, method=None, variable=None, horizon=None, combo_label=None) -> tuple[Figure, np.ndarray]`
`heatmap_by_horizon(weights_df, y_axis='model', model=None, method=None, variable=None, combo_label=None) -> tuple[Figure, np.ndarray]`
`line_plot_by_vintage(weights_df, y_axis='model', model=None, method=None, variable=None, horizon=None, combo_label=None) -> tuple[Figure, np.ndarray]`
`line_plot_by_horizon(weights_df, y_axis='model', model=None, method=None, variable=None, combo_label=None) -> tuple[Figure, np.ndarray]`
`bar_plot_by_vintage(weights_df, y_axis='model', model=None, method=None, variable=None, horizon=None, combo_label=None) -> tuple[Figure, np.ndarray]`
`bar_plot_by_horizon(weights_df, y_axis='model', model=None, method=None, variable=None, combo_label=None) -> tuple[Figure, np.ndarray]`
```

Plots facet across non-`y_axis` dimensions and raise a clear `ValueError` when selected filters leave no data. The same six functions are exported by `forecast_combo.visualisations`.

## Dashboards

Dashboard support is optional and uses `shiny` at runtime. Install the dashboard extra before using either dashboard:

```sh
pip install "forecast-combo[dashboard]"
```

The combination dashboard explores fitted weights; the forecast dashboard delegates to the `forecast_evaluation` dashboard for original and combined forecasts.

```text
combo.run_combo_dashboard(host="127.0.0.1", port=8000)
combo.run_forecast_dashboard(host="127.0.0.1", port=8000)
```

**Combination dashboard**: Interactive weight exploration by horizon and vintage.

**Forecast dashboard**: Combines with `forecast_evaluation` dashboard.

Both dashboard methods return `None` after starting their server. Missing dashboard dependencies raise an installation-oriented `ImportError`.

---

## Utilities

```text
fc.create_period_filter(start_period, end_period, freq)
# e.g., create_period_filter("2020Q1", "2021Q4", "Q") → list[pd.Period]
```

---

## Common patterns

**Simple equal-weight**:
```python
# skill-test: skip (requires full FER data and expensive combination estimation)
import forecast_evaluation as fe
import forecast_combo as fc

data = fe.ForecastData(load_fer=True)
combo = fc.ForecastCombo(forecast_data=data)
combo.fit(sources=["mpr", "bvar unconditional"], variables=["gdpkp"], method="average")
```

**Multiple methods**:
```text
combo.fit(
    sources=["mpr", "compass conditional", "bvar unconditional"],
    variables=["gdpkp", "cpisa"],
    method=["average", "rmse", "constrained_least_squares"],
    training_start="2016-01-01",
)
```

<!-- BEGIN GENERATED API -->
## API

```json
{
  "exports": {
    "forecast_combo": [
      "ComboSpec",
      "ForecastCombo",
      "SUPPORTED_METHODS",
      "bar_plot_by_horizon",
      "bar_plot_by_vintage",
      "create_period_filter",
      "get_weights",
      "heatmap_by_horizon",
      "heatmap_by_vintage",
      "line_plot_by_horizon",
      "line_plot_by_vintage",
      "validate_spec_graph"
    ],
    "forecast_combo.combinations": [
      "average",
      "constrained_least_squares",
      "huber_weights",
      "least_squares",
      "mae_weights",
      "mse_weights",
      "rmse_weights"
    ]
  },
  "package": "forecast_combo",
  "signatures": {
    "forecast_combo.ComboSpec": "(name: str, sources: list, method: str = 'average', training_start: str | None = None, training_end: str | None = None, metric: str = 'pop', k: int = 0, period_filter: list | None = None, window_size: int | None = None, discount_param: float = 1.0, allow_partial_sources: bool = True, print_warning: bool = True) -> None",
    "forecast_combo.ForecastCombo": "(forecast_data: Any) -> None",
    "forecast_combo.bar_plot_by_horizon": "(weights_df: pandas.DataFrame, y_axis: str = 'model', model: str | list[str] | None = None, method: str | list[str] | None = None, variable: str | list[str] | None = None, combo_label: str | list[str] | None = None) -> tuple[matplotlib.figure.Figure, numpy.ndarray]",
    "forecast_combo.bar_plot_by_vintage": "(weights_df: pandas.DataFrame, y_axis: str = 'model', model: str | list[str] | None = None, method: str | list[str] | None = None, variable: str | list[str] | None = None, horizon: int | str | list[int | str] | None = None, combo_label: str | list[str] | None = None) -> tuple[matplotlib.figure.Figure, numpy.ndarray]",
    "forecast_combo.combinations.average": "(X: numpy.ndarray) -> numpy.ndarray",
    "forecast_combo.combinations.constrained_least_squares": "(X: numpy.ndarray, y: numpy.ndarray, window_size: int | None = None) -> numpy.ndarray",
    "forecast_combo.combinations.huber_weights": "(X: numpy.ndarray, y: numpy.ndarray, window_size: int | None) -> numpy.ndarray",
    "forecast_combo.combinations.least_squares": "(X: numpy.ndarray, y: numpy.ndarray, window_size: int | None = None) -> tuple[numpy.ndarray, numpy.ndarray]",
    "forecast_combo.combinations.mae_weights": "(X: numpy.ndarray, y: numpy.ndarray, window_size: int | None, discount_param: float = 1.0) -> tuple[numpy.ndarray, numpy.ndarray]",
    "forecast_combo.combinations.mse_weights": "(X: numpy.ndarray, y: numpy.ndarray, window_size: int | None, discount_param: float = 1.0) -> tuple[numpy.ndarray, numpy.ndarray]",
    "forecast_combo.combinations.rmse_weights": "(X: numpy.ndarray, y: numpy.ndarray, window_size: int | None, discount_param: float = 1.0) -> tuple[numpy.ndarray, numpy.ndarray]",
    "forecast_combo.create_period_filter": "(start_period: str | pandas.Period | pandas.Timestamp, end_period: str | pandas.Period | pandas.Timestamp, freq: str) -> list[pandas.Period]",
    "forecast_combo.get_weights": "(X: numpy.ndarray, y: numpy.ndarray, method: str, window_size: int | None = None, discount_param: float = 1.0) -> tuple[numpy.ndarray, numpy.ndarray]",
    "forecast_combo.heatmap_by_horizon": "(weights_df: pandas.DataFrame, y_axis: str = 'model', model: str | list[str] | None = None, method: str | list[str] | None = None, variable: str | list[str] | None = None, combo_label: str | list[str] | None = None) -> tuple[matplotlib.figure.Figure, numpy.ndarray]",
    "forecast_combo.heatmap_by_vintage": "(weights_df: pandas.DataFrame, y_axis: str = 'model', model: str | list[str] | None = None, method: str | list[str] | None = None, variable: str | list[str] | None = None, horizon: int | str | list[int | str] | None = None, combo_label: str | list[str] | None = None) -> tuple[matplotlib.figure.Figure, numpy.ndarray]",
    "forecast_combo.line_plot_by_horizon": "(weights_df: pandas.DataFrame, y_axis: str = 'model', model: str | list[str] | None = None, method: str | list[str] | None = None, variable: str | list[str] | None = None, combo_label: str | list[str] | None = None) -> tuple[matplotlib.figure.Figure, numpy.ndarray]",
    "forecast_combo.line_plot_by_vintage": "(weights_df: pandas.DataFrame, y_axis: str = 'model', model: str | list[str] | None = None, method: str | list[str] | None = None, variable: str | list[str] | None = None, horizon: int | str | list[int | str] | None = None, combo_label: str | list[str] | None = None) -> tuple[matplotlib.figure.Figure, numpy.ndarray]",
    "forecast_combo.validate_spec_graph": "(roots: 'list[ComboSpec]', raw_sources: 'set[str] | None' = None) -> list['ComboSpec']"
  },
  "version": "0.1.1"
}
```
<!-- END GENERATED API -->
