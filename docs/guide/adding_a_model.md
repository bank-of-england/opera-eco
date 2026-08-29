# Adding a New Model

This guide shows how to integrate a forecasting model with OPERA. Integrate models through `forecast_realtime`, which provides the base class, orchestration, and caching infrastructure.

---

This guide targets `forecast_realtime` version 0.5.2.


## Interface Requirements

Every ecosystem model subclasses `ForecastModel` and provides three methods.

### `__init__(...)` — Configuration

Store the hyperparameters and settings that `_fit` and `_forecast` need. Accept user-facing arguments here, such as regularisation strength, window size, and number of estimators. Initialise fitted-state placeholders, such as `self.model = None`, so the object is fully described before it sees data.

Call `super().__init__(label=label, formula=formula)` to register the model label and optional formula:

```python
def __init__(self, my_param=1.0, label=None, formula=None):
    super().__init__(label=label, formula=formula)
    self.my_param = my_param
```

- **`label`**: String tag attached to forecasts from this instance. It defaults
    to the class name; `RealTimeModel.forecast(label=...)` can override it.
- **`formula`**: R-style formula, such as `"cpisa ~ gdpkp + unemp"` or
    `"cpisa ~ ."`, that selects `y` and `X` columns after lag augmentation.
    `None` uses every column.

**Lag features are not constructor parameters.** Pass `y_lags` and `X_lags` to `ForecastModel.fit()` or `RealTimeModel.forecast()`. Those methods build the lagged design matrix before calling `_fit()`. Do not build lags in `__init__` or `_fit()`.

After `fit()`, the base class exposes `y_lags`, `X_lags`, `y_name`, `X_names`, the final `y` and `X` design matrix, `dummies`/`_dummy_cols`, and `last_y_fit_date`. `y_name` supplies the target prefix for lag columns.

### `_fit(y, X=None, **kwargs)` — Estimation

Estimate the model from historical `y` data. For example, fit regression coefficients, train tree splits, or calculate time-series summary statistics. After this method returns, the model must be ready to forecast.

`_fit()` receives the processed design matrix. When callers specify `y_lags` or `X_lags`, `ForecastModel.fit()` has already appended lag columns to `X` and dropped incomplete rows. Do not call `build_lagged_design` or build lags in `_fit()`.

**Inputs:**

| Argument | Type | Description |
|----------|------|-------------|
| `y` | `pd.DataFrame` | Target variable(s). **Index:** `DatetimeIndex`. **Values:** already transformed (e.g. growth rates). When lags are used this is the NaN-dropped aligned target; otherwise the full training history. |
| `X` | `pd.DataFrame` or `None` | Design matrix, potentially augmented with lag columns. Column order: base X cols, then `<y_name>_lag1…<y_name>_lagk`, then `col_lag1…col_lagk` per X column. `None` if no regressors and `y_lags=0`. |
| `**kwargs` | | Extra keyword arguments forwarded from `RealTimeModel.forecast(..., **kwargs)`. `y_lags` and `X_lags` are **not** present here — they are consumed by `ForecastModel.fit()`. |

**Example `y` (quarterly, single variable, `data_transformation={"cpisa": "pop"}`):**

```text
              cpisa
date
2014-03-31    0.6
2014-06-30    0.8
2014-09-30    0.5
2014-12-31    0.9
2015-03-31    0.7
```

**Example `y` (quarterly, multivariate):**

```text
              cpisa    gdpkp
date
2014-03-31    0.6      0.4
2014-06-30    0.8      0.3
2014-09-30    0.5      0.7
2014-12-31    0.9      0.2
```

**Must return** `self`.

---

### `_forecast(steps, X=None, y=None, **kwargs)` — Forecasting

Use the fitted model to forecast the next `steps` periods. Each output row is a forecast horizon: row 0 is the current-period nowcast, row 1 is one period ahead, and so on.

**Inputs:**

| Argument | Type | Description |
|----------|------|-------------|
| `steps` | `int` | Number of periods ahead to forecast (always ≥ 1). |
| `X` | `pd.DataFrame`, `np.ndarray` or `None` | Design matrix over the forecast horizon, column order matching the `X` passed to `_fit`. **When `y_lags` or `X_lags` are set, `forecast()` rebuilds the lagged design over the full history *plus* the horizon rows**, so `_forecast` must slice out the last `steps` rows itself. Without lags it contains only the future regressors, shape `(steps, n_X_variables)`. `None` if no `X_variables` (or no `X_cond_variables`) were specified. |
| `y` | `np.ndarray` or `None` | Conditioning paths for the target variables. Shape: `(steps, n_y_variables)`, column order matches the `y` passed to `_fit`. Entries set to `NaN` are unconstrained; non-NaN entries pin that variable/horizon to an externally supplied value (e.g. MPR projections). `None` if no `y_cond_variables` were specified. |
| `**kwargs` | | Additional keyword arguments. |

**Output:**

Must return a `pd.DataFrame` of shape `(steps, n_y_variables)`:
- **Index:** a `pd.DatetimeIndex` (name `"date"`) of length `steps`, one date per horizon. The subclass owns this. AR-style models can call `self._wrap_forecast(arr, steps)` to wrap an `(steps, n_vars)` ndarray with dates inferred from `self.y.index`; mixed-frequency models (e.g. MIDAS) build the DataFrame with their own anchor dates.
- **Rows** correspond to forecast horizons 0, 1, …, steps−1 (horizon 0 = nowcast of the current period).
- **Columns** must match the order and count of columns in the `y` DataFrame that was passed to `_fit()`.
- Values must be in the **same transformed space** as the training `y` (e.g. if the model was estimated on growth rates, return growth rate forecasts). `RealTimeModel` handles back-transformation to levels automatically.

**Example output for `steps=4`, 1 variable:**

```python
pd.DataFrame(
    [[0.7], [0.6], [0.5], [0.4]],
    index=pd.date_range("2024-03-31", periods=4, freq="QE"),
    columns=["cpisa"],
)  # The result has shape (4, 1).
```

**Example output for `steps=4`, 2 variables:**

```python
pd.DataFrame(
    [[0.7, 0.3], [0.6, 0.4], [0.5, 0.5], [0.4, 0.6]],
    index=pd.date_range("2024-03-31", periods=4, freq="QE"),
    columns=["cpisa", "gdpkp"],
)  # The result has shape (4, 2).
```

The base class requires a `DataFrame` with a `DatetimeIndex`, exactly `steps` rows, and the same number of columns as the fitted `y`.

---

### `_forecast_decomp(steps, X=None, y=None, **kwargs)` — Forecast Decomposition (Optional)

Use this optional method to break forecast revisions into components. Between data vintages, a revision can contain:

- **News**: revision from new data released
- **Reestimation**: revision from model refit (parameter changes, not new data)
- **Interaction**: cross-term combining both effects

This method is optional. Return `None` when the model does not support decomposition.

**Inputs:**

| Argument | Type | Description |
|----------|------|-------------|
| `steps` | `int` | Number of periods ahead to forecast (same as `_forecast`). |
| `X` | `pd.DataFrame` or `None` | Full augmented design matrix (same object as passed to `_forecast`: history plus horizon rows when lags are used). |
| `y` | `pd.DataFrame` or `None` | Conditioning paths (same as passed to `_forecast`). |
| `**kwargs` | | Additional keyword arguments. |

**Output (minimal contract):**

Return `pd.DataFrame` or `None`:

- If decomposition not supported: return `None`
- If decomposition computed, one row per component per horizon:
  - `forecast_horizon` (int): 0-based horizon index
  - `component` (str): name of the component (e.g. `'intercept'`, `'gdpkp'`, `'cpisa_lag1'`)
  - `contribution` (float): additive effect — values must sum to the total forecast for each horizon
  - `weight` (float or NaN): model coefficient (NaN if not applicable, e.g. black-box models)

`RealTimeModel` augments these rows with metadata (`variable`, `date`, `vintage_date`, `frequency`, `source`, `forecast_metric`, `decomposition`, `revision_source`, `base_vintage_date`) before storing in `rt_model.decompositions`. The model does **not** need to return these columns.

**Example output (OLS with 2 regressors + intercept, `steps=4`):**

```python
pd.DataFrame(
    {
        "forecast_horizon": [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3],
        "component": ["intercept", "payrolls", "ip"] * 4,
        "contribution": [-0.9, 0.5, 0.06] * 4,
        "weight": [np.nan, 0.5, 0.1] * 4,
    }
)  # 12 rows × 4 cols; each horizon has 3 components
```

**Gotchas:**

- `forecast_horizon` is 0-based (0 = nowcast)
- `contribution` values **must sum to the total forecast** for each horizon
- `weight` can be `NaN` for non-parametric or black-box models
- Simple models (e.g. moving average) can return `None` and skip decomposition
- Do **not** include `news`, `revision_source`, `vintage_date`, or other metadata — `RealTimeModel` adds those

---

The model need not use Python; see [Language Interoperability](#language-interoperability).

---

## Example: Moving Average in Python

A moving-average model forecasts each horizon with the mean of the previous `window_size` observations. It provides the smallest useful implementation of the interface.

### Step 1: Subclass `ForecastModel`

```python
import numpy as np
import pandas as pd
from forecast_realtime import ForecastModel


class MovingAverage(ForecastModel):
    def __init__(self, window_size: int = 4, label=None):
        super().__init__(label=label)
        self.window_size = window_size
        self.window_mean = None

    def _fit(self, y: pd.DataFrame, X: pd.DataFrame = None, **kwargs):
        data_window = y.iloc[-self.window_size :]
        self.window_mean = data_window.mean().values
        return self

    def _forecast(
        self,
        steps: int,
        X: np.ndarray = None,
        y: np.ndarray = None,
        **kwargs,
    ) -> pd.DataFrame:
        forecast = np.tile(self.window_mean, (steps, 1))
        return self._wrap_forecast(forecast, steps)
```

### Step 2: Run Real-time Forecasts

```python
import forecast_evaluation as fe
import forecast_realtime as rt

forecast_data = fe.ForecastData(load_fer=True)

ma_model = MovingAverage(window_size=4)
rt_model = rt.RealTimeModel(data=forecast_data, models=ma_model)

# Run forecasts, optionally including decomposition.
rt_model.forecast(
    y_variables=["cpisa"],
    data_transformation={"cpisa": "pop"},
    step_frequency="Q",
    steps=8,
    label="MA(4)",
    first_vintage="2015-01-01",
    decomp=False,  # Set to True to enable decomposition.
)

rt_model.data.run_dashboard()

# With decomp=True, inspect the decomposition:
# print(rt_model.decompositions)  # DataFrame of component contributions.
```

---

## Example: OLS with Decomposition

Ordinary Least Squares (OLS) forecasts with interpretable component decomposition. This example shows how `_forecast_decomp()` breaks down forecast revisions into data news, parameter reestimation, and interaction effects.

### Step 1: Subclass `ForecastModel` with decomposition support

```python
import numpy as np
import pandas as pd
from forecast_realtime import ForecastModel
from sklearn.linear_model import LinearRegression


class SimpleOLS(ForecastModel):
    """OLS regression with forecast decomposition support.

    Parameters
    ----------
    fit_intercept : bool
        Whether to include an intercept term.
    """

    def __init__(self, fit_intercept: bool = True, label=None, formula=None):
        super().__init__(label=label, formula=formula)
        self.fit_intercept = fit_intercept
        self.model = None
        self.intercept_ = None
        self.coef_ = None

    def _fit(self, y: pd.DataFrame, X: pd.DataFrame = None, **kwargs):
        """Fit OLS to y and X."""
        if X is None or X.shape[1] == 0:
            raise ValueError("SimpleOLS requires X_variables")

        self.model = LinearRegression(fit_intercept=self.fit_intercept)
        self.model.fit(X, y.values)
        self.intercept_ = self.model.intercept_
        self.coef_ = self.model.coef_
        return self

    def _forecast(self, steps: int, X=None, y=None, **kwargs) -> pd.DataFrame:
        """Forecast using OLS: y = intercept + X @ coef."""
        if X is None:
            raise ValueError("SimpleOLS requires X (future regressors)")

        # X has shape (steps, n_X).
        forecasts = X @ self.coef_.T + self.intercept_
        return self._wrap_forecast(forecasts, steps)

    def _forecast_decomp(self, steps: int, X=None, y=None, **kwargs) -> pd.DataFrame:
        """Decompose forecast into intercept + regressor components.

        Returns one row per component per horizon with columns:
        forecast_horizon, component, contribution, weight.
        """
        if X is None:
            return None

        components = []
        X_cols = list(self.X.columns)

        for h in range(steps):
            # Add the intercept contribution.
            components.append(
                {
                    "forecast_horizon": h,
                    "component": "intercept",
                    "contribution": float(self.intercept_),
                    "weight": np.nan,
                }
            )

            # Add each regressor contribution.
            for col_idx, col_name in enumerate(X_cols):
                x_value = (
                    X[h, col_idx] if hasattr(X, "__getitem__") else X.iloc[h, col_idx]
                )
                contribution = float(self.coef_[col_idx]) * x_value
                components.append(
                    {
                        "forecast_horizon": h,
                        "component": col_name,
                        "contribution": contribution,
                        "weight": float(self.coef_[col_idx]),
                    }
                )

        return pd.DataFrame(components)
```

### Step 2: Run OLS with decomposition enabled

```python
import forecast_evaluation as fe
import forecast_realtime as rt

forecast_data = fe.ForecastData(load_fer=True)

ols_model = SimpleOLS(fit_intercept=True)
rt_model = rt.RealTimeModel(data=forecast_data, models=ols_model)

rt_model.forecast(
    y_variables=["cpisa"],
    X_variables=["oil_prices", "fx_rate"],
    data_transformation={"cpisa": "pop", "oil_prices": "pop", "fx_rate": "levels"},
    step_frequency="Q",
    steps=12,
    label="OLS",
    first_vintage="2015-01-01",
    decomp=True,  # Enable decomposition.
)

# Inspect the decomposition results.
print(rt_model.decompositions)
# The output includes these columns:
#   horizon, component, contribution, weight, news, vintage_date, revision_source, decomposition
# These columns show each regressor's and the intercept's contribution at each horizon.
```

---

## Language Interoperability

Use the provided `forecast_realtime` classes to integrate models written in R, Julia, MATLAB, or another language:

| Language | Class          | CLI executable |
|----------|----------------|----------------|
| R        | `RModel`       | `Rscript`      |
| MATLAB   | `MATLABModel`  | `matlab`       |
| Julia    | `JuliaModel`   | `julia`        |

All three inherit from `ExternalModel`. It manages temporary directories, Parquet I/O, parameter deserialisation, CLI dispatch, subprocess execution, and forecast output. You supply only the model logic.

Implement two functions: `fit(y, params)`, which returns a model object, and `forecast(model, y, steps, params)`, which returns a data frame or matrix.

### What the Package Handles for You

1. `fit()` writes `y.parquet` (and optionally `X.parquet`) to a temporary directory, loads `y` into a data frame, deserialises your keyword arguments into `params`, calls your `fit(y, params)` function, and **saves the returned model object** to disk (`model.rds` / `model.mat` / `model.jls`).
2. `forecast()` loads `y` and **deserialises the saved model**, calls your `forecast(model, y, steps, params)` function, takes the returned data frame / matrix and **writes it to `forecasts.parquet`**, then returns the result as a `pd.DataFrame` (the base class wraps it with the standard inferred-date `DatetimeIndex`).
3. The temporary directory is **automatically deleted** when the model object is garbage-collected.

Do not use `cache_dir`, `saveRDS`, `write_parquet`, or other file I/O in these functions. The runner scripts handle it.

### Function Signatures Your Script Must Define

| Language | `fit` | `forecast` |
|----------|-------|------------|
| R | `fit(y, params)` → returns a model object (e.g. a list) | `forecast(model, y, steps, params)` → returns a `data.frame` |
| MATLAB | `result = my_model('fit', y, params)` → returns a struct | `result = my_model('forecast', model, y, steps, params)` → returns a table |
| Julia | `fit(y, params)` → returns any serialisable object | `forecast(model, y, steps, params)` → returns a `DataFrame` |

---

## Example: Moving Average in R

`RModel` takes the path to your `.R` script plus any keyword arguments you want forwarded as parameters:

```python
from forecast_realtime import RModel

# The Python argument "window_size=4" becomes params$window_size in the R script.
model = RModel("ma_model.R", window_size=4)
rt_model = rt.RealTimeModel(data=forecast_data, models=model)
rt_model.forecast(
    y_variables=["cpisa"],
    data_transformation={"cpisa": "pop"},
    step_frequency="Q",
    steps=8,
    label="MA(4) R",
    first_vintage="2015-01-01",
)
```

The R script `ma_model.R` looks like:

```r
# ma_model.R defines only fit() and forecast().

fit <- function(y, params) {
  window_size <- as.integer(params$window_size)

  n       <- nrow(y)
  tail_df <- y[max(1, n - window_size + 1):n, , drop = FALSE]

  window_mean <- sapply(tail_df, mean)

    # Return a model object; the runner saves it to model.rds.
  list(window_mean = window_mean, col_names = colnames(y))
}

forecast <- function(model, y, steps, params) {
  window_mean <- model$window_mean
  n_vars         <- length(window_mean)

  fcst <- matrix(rep(window_mean, each = steps), nrow = steps, ncol = n_vars)

  out <- as.data.frame(fcst)
  colnames(out) <- model$col_names
    # Return a data.frame; the runner writes it to forecasts.parquet.
  out
}
```

---

## Example: Moving Average in MATLAB

`MATLABModel` takes the path to your `.m` file. The file's stem is called as a MATLAB function:

```python
from forecast_realtime import MATLABModel

# The Python argument "window_size=4" becomes params.window_size in MATLAB.
model = MATLABModel("ma_model.m", window_size=4)
rt_model = rt.RealTimeModel(data=forecast_data, models=model)
rt_model.forecast(
    y_variables=["cpisa"],
    data_transformation={"cpisa": "pop"},
    step_frequency="Q",
    steps=8,
    label="MA(4) MATLAB",
    first_vintage="2015-01-01",
)
```

The MATLAB function `ma_model.m` looks like:

```matlab
function result = ma_model(action, varargin)
    % fit:      result = ma_model('fit', y, params)
    % forecast: result = ma_model('forecast', model, y, steps, params)

    if strcmp(action, 'fit')
        y      = varargin{1};
        params = varargin{2};
        window_size = params.window_size;

        y_arr = table2array(y);
        n     = size(y_arr, 1);

        tail_y         = y_arr(max(1, n - window_size + 1):n, :);
        window_mean = mean(tail_y, 1);

        % Return a model struct — the runner saves it to model.mat
        result.window_mean = window_mean;
        result.col_names      = y.Properties.VariableNames;

    elseif strcmp(action, 'forecast')
        model = varargin{1};
        y     = varargin{2};
        steps = varargin{3};

        fcst = repmat(model.window_mean, steps, 1);

        % Return a table — the runner writes it to forecasts.parquet
        result = array2table(fcst, 'VariableNames', model.col_names);
    end
end
```

---

## Example: Moving Average in Julia

`JuliaModel` takes the path to your `.jl` script:

```python
from forecast_realtime import JuliaModel

# The Python argument "window_size=4" becomes params["window_size"] in Julia.
model = JuliaModel("ma_model.jl", window_size=4)
rt_model = rt.RealTimeModel(data=forecast_data, models=model)
rt_model.forecast(
    y_variables=["cpisa"],
    data_transformation={"cpisa": "pop"},
    step_frequency="Q",
    steps=8,
    label="MA(4) Julia",
    first_vintage="2015-01-01",
)
```

The Julia script `ma_model.jl` looks like:

```julia
# ma_model.jl defines only fit() and forecast().

using Statistics

function fit(y, params)
    window_size = Int(params[:window_size])

    col_names = names(y)
    n         = nrow(y)

    tail_start     = max(1, n - window_size + 1)
    window_mean = [mean(Float64.(y[tail_start:n, c])) for c in col_names]

    # Return a model object; the runner serialises it to model.jls.
    Dict("window_mean" => window_mean,
         "col_names" => col_names)
end

function forecast(model, y, steps, params)
    window_mean = model["window_mean"]

    fcst = repeat(transpose(window_mean), steps, 1)

    # Return a DataFrame; the runner writes it to forecasts.parquet.
    DataFrame(fcst, model["col_names"])
end
```

---

## Testing

Every wrapper needs a test in `tests/models/` that compares its output directly with the native package's output. This proves that the wrapper remains a transparent pass-through. See `tests/models/test_midas.py` and `tests/models/test_bvar.py` for examples.

---

## Debugging External Models

External-model classes provide an interactive debug mode. It starts the target language's REPL with `y` and `params` loaded and calls `fit()` or `forecast()`.

Pass `debug="fit"` or `debug="forecast"` when creating the model:

```python
model = RModel("ma_model.R", debug="fit", window_size=4)
model.fit(y)  # Open an interactive R REPL and call fit().

model = RModel("ma_model.R", debug="forecast", window_size=4)
model.fit(y)  # Run fit() normally.
model.forecast(4)  # Open an interactive R REPL and call forecast().
```

Add breakpoints in your script before running:

| Language | Breakpoint command             | Notes                                    |
|----------|--------------------------------|------------------------------------------|
| R        | `browser()`                    | Pause and inspect; `n` to step, `c` to continue, `Q` to quit |
| MATLAB   | Set breakpoints in the editor  | `debug="fit"` opens the MATLAB desktop   |
| Julia    | `@bp` or `@infiltrate`         | Requires `Debugger.jl` or `Infiltrator.jl` |
