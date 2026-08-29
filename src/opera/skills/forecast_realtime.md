---
name: forecast-realtime
description: Use when working with the `forecast_realtime` Python package.
module-package: forecast_realtime
module-version: "0.5.3"
---

# forecast_realtime

`forecast_realtime` fits forecast models on vintage data and stores forecasts through `forecast_evaluation.ForecastData`. The package separates the low-level `ForecastModel` contract from `RealTimeModel`, which runs that contract over vintages. Optional model implementations are loaded lazily.

## Canonical imports

```python
import forecast_realtime as rt
from forecast_realtime import (
    RealTimeModel,
    ForecastModel,
    ForecastContext,
    ForecastResult,
    ForecastTree,
    TreeNode,
    ExternalModel,
    Formula,
    RModel,
    MATLABModel,
    JuliaModel,
    generate_synthetic_data,
    ModelInputRequirements,
    InputMetricMapping,
    ResolvedTransformationPlan,
    RawInputBundle,
    PreparedModelInputs,
    models,
)
import forecast_realtime.models as models
from forecast_realtime.models import (
    ForecastRidge,
    ForecastLasso,
    ForecastElasticNet,
    ForecastBVAR,
    RandomForest,
    XGBoost,
    ForecastRlm,
    RFableModel,
    RFableETS,
    RFableARIMA,
    ForecastMIDAS,
    ForecastMIDASCombo,
    ForecastMultiMIDAS,
    ForecastOLS,
    ForecastBridgeOLS,
)
from forecast_realtime.data_transformation import (
    DataTransformationPipeline,
    FittedDataTransformation,
)
from forecast_realtime.linear_regression import LinearRegression
from forecast_realtime.tree_regression import TreeRegression
```

The root exports above match `forecast_realtime.__all__`; `models` is the lazy model module. `LinearRegression`, `TreeRegression`, `DataTransformationPipeline`, and `FittedDataTransformation` are imported from their submodules rather than re-exported at the package root.

## ForecastModel

Constructor and public methods:

`ForecastModel(label=None, formula=None, data_transformation=None, align_start_dates=False)`

`fit(y, X=None, y_lags=0, X_lags=0, dummies=None, data_transformation=None, frequency=None, X_imputation=None, input_frequencies=None, y_input_metrics=None, X_input_metrics=None, drop_transformation_nans=True, **kwargs)`

`forecast(steps=1, X=None, y=None, decomp=False, data_transformation=None, frequency=None, X_imputation=None, context=None, **kwargs)`

`predict(context, steps=1, decomp=False, data_transformation=None, frequency=None, X_imputation=None, **kwargs)`

`ForecastModel` is abstract: subclasses implement `_fit(y, X, **kwargs)` and `_forecast(steps, X, y, **kwargs)`. `fit()` validates and copies datetime-indexed frames, resolves transformations, constructs lags and dummies, applies a formula, and returns `self`. The `frequency` argument here is lower-level target-frequency metadata; realtime orchestration uses `step_frequency`.

`y` is a target DataFrame. `X` is an optional regressor DataFrame. With lags, the design contains the base columns followed by `y_lags` columns named `<target>_lag1` through `<target>_lagk` and `X_lags` columns named `<regressor>_lag1` through `<regressor>_lagk`. `X_lags` may be an integer for all columns or a `{column: count}` mapping. `dummies` is a list of dates or a `{name: date}` mapping for deterministic point dummies. `formula` uses the R-style forms `"y ~ x1 + x2"` and `"y ~ ."` after the design is augmented.

`_forecast()` may return an array of shape `(steps, n_targets)` or a DataFrame. Arrays are wrapped with future dates after the fitted origin. A DataFrame must have a `DatetimeIndex` and the fitted target columns. `forecast()` returns a `ForecastResult`, a DataFrame-compatible object whose index is named `date`. Ordinary forecast dates are strictly after the fitted origin. Models that own their date convention may include the origin and set `_forecast_dates_include_origin=True`.

`fit()` and `forecast()` operate on copied candidate state and publish it only after success. A model's own `data_transformation` takes precedence over a call-level fallback mapping. `fitted_values` exposes the subclass's in-sample values after fitting.

## ForecastContext and ForecastResult

`ForecastContext(y_history, X_history, y_conditioning=None, X_conditioning=None, forecast_origin=None, y_conditioning_input_metrics=None, X_conditioning_input_metrics=None)`

`ForecastResult(forecast, decomposition=None, forecast_origin=None, steps=None, expected_columns=None, forecast_dates_include_origin=False)`

`ForecastContext` is an immutable request containing raw fitted history, optional raw conditioning/future paths, the forecast origin, and source metric metadata. Pass it to `predict()` when a model must evaluate a request without changing its fitted state. `forecast()` creates one when `context` is omitted.

`ForecastResult.forecast` returns the values as a plain DataFrame; `ForecastResult.decomposition` contains optional model-local components, and `forecast_origin` records the anchor. When validation arguments are supplied, the result requires exactly `steps` rows, fitted target columns, a sorted unique non-missing datetime index, and dates after the origin. A decomposition must reconcile every target and horizon.

## RealTimeModel

Constructor and orchestration signature:

`RealTimeModel(data, models)`

`models` is one `ForecastModel` or a list of them. Labels must be unique and become the forecast `source`. `data` must be a `forecast_evaluation.ForecastData` instance.

`forecast(y_variables, step_frequency=None, data_transformation=None, label=None, steps=1, first_forecast_horizon=None, X_variables=None, y_steps_ahead=None, y_sources=None, X_steps_ahead=None, X_sources=None, y_lags=0, X_lags=0, dummies=None, first_vintage=None, last_vintage=None, reconstruct_levels=True, parallel=False, batch_size=None, max_workers=None, decomp=False, X_imputation=None, drop_transformation_nans=True, **kwargs)`

Example:

```python
# skill-test: skip (requires full FER data and realtime estimation)
import forecast_evaluation as fe
import forecast_realtime as rt

data = fe.ForecastData(load_fer=True)
forecast_model = rt.models.ForecastOLS(label="ols")
runner = rt.RealTimeModel(data=data, models=forecast_model)
runner.forecast(
    y_variables=["cpisa"],
    X_variables=["gdpkp"],
    data_transformation={"cpisa": "pop", "gdpkp": "pop"},
    step_frequency="Q",
    steps=4,
    first_vintage="2024-01-01",
)
```

`forecast()` returns `self`, deep-copies each model for every vintage, and updates `runner.data` with forecasts. If `decomp=True`, it also populates `runner.decompositions`; when reconstruction is disabled, native transformed rows are retained in `runner.native_forecasts`.

`y_variables` and `X_variables` select variables in the outturn panel. `data_transformation` maps each selected variable to a metric and is a fallback for models without a model-owned pipeline. `step_frequency` is the frequency of forecast steps, usually `"M"` or `"Q"`; it is inferred only when the selected targets have one unambiguous frequency. Do not pass the lower-level `frequency` spelling to this orchestration method.

`first_vintage` and `last_vintage` bound the vintage loop. The deprecated `first_forecast_horizon` option is only for an explicit calendar-relative cutoff; omitting it fits through the latest usable target period and starts in the next period. `parallel=True` distributes model and vintage batches, so extra `kwargs` must be pickleable. `decomp=True` cannot run in parallel.

Conditioning and future regressors use matching pairs:

| Inputs | Meaning |
| --- | --- |
| `y_steps_ahead` and `y_sources` | Target conditioning paths, used by models such as `ForecastBVAR`. |
| `X_steps_ahead` and `X_sources` | Forecast regressor paths for models with exogenous inputs. |
| `y_lags` | Number of target autoregressive lags. |
| `X_lags` | Common integer or per-column regressor lag mapping. |
| `dummies` | Date list or named date mapping for point dummies. |

Conditioning horizons are zero-based integers in `0..steps-1` or `None`. Sources must have exactly the same keys as their horizon mapping. `y` and `X` conditioning values are combined with raw history by date before each model's transformation; a supplied value wins on overlapping dates.

## Model registry

The lazy `forecast_realtime.models` registry contains exactly these names:

```python
from forecast_realtime.models import (
    ForecastRidge,
    ForecastLasso,
    ForecastElasticNet,
    ForecastBVAR,
    RandomForest,
    XGBoost,
    ForecastRlm,
    RFableModel,
    RFableETS,
    RFableARIMA,
    ForecastMIDAS,
    ForecastMIDASCombo,
    ForecastMultiMIDAS,
    ForecastOLS,
    ForecastBridgeOLS,
)
```

Attribute access imports the implementation on demand. Missing optional dependencies raise a model-specific `ModuleNotFoundError`. The registry has scikit-learn models, XGBoost, the BVAR wrapper, R/Fable wrappers, and the MIDAS wrappers listed above. A name not in this list is not a registered forecast model.

The framework `fit()`/`forecast()` arguments are `y_lags` and `X_lags`; they control the target and regressor lagged design for that call. `n_lags` remains a constructor parameter for `ForecastBVAR`, `ForecastMIDAS`, and `ForecastMultiMIDAS`, and `lags` remains a constructor parameter for `ForecastRlm`. These model-specific parameters configure the model itself and are distinct from the framework lag arguments. Linear models use `forecast_strategy="recursive"` by default; `"direct"` fits one model per horizon and requires `steps`. Linear `scale=True` standardises the target and regressors and maps predictions back. Tree `standardise=True` has the corresponding behaviour. `formula` is supported where shown by the constructor and is applied after lags and dummies.

### Linear models

`ForecastOLS(fit_intercept=True, forecast_strategy="recursive", steps=None, scale=False, label=None, formula=None, data_transformation=None, drop_nans=False, align_start_dates=True)`

`ForecastRidge(fit_intercept=True, forecast_strategy="recursive", steps=None, scale=False, alpha=None, cv=None, label=None, alphas=None, alpha_scaling="mean", formula=None, data_transformation=None, drop_nans=False, align_start_dates=True)`

`ForecastLasso(fit_intercept=True, forecast_strategy="recursive", steps=None, scale=False, alpha=None, cv=None, label=None, alphas=None, formula=None, data_transformation=None, drop_nans=False, align_start_dates=True)`

`ForecastElasticNet(fit_intercept=True, forecast_strategy="recursive", steps=None, scale=False, alpha=None, l1_ratio=0.5, cv=None, label=None, alphas=None, formula=None, data_transformation=None, drop_nans=False, align_start_dates=True)`

`ForecastOLS` uses `numpy.linalg.lstsq`. Ridge, Lasso, and ElasticNet use scikit-learn; `cv` selects a penalty by cross-validation. Ridge accepts `alpha_scaling="mean"` or `"sum"`; `alphas` is used with cross-validation. All four are single-target models. Complete-case fitting is controlled by `drop_nans`; `align_start_dates=True` aligns the first complete target and regressor date.

### Tree and BVAR models

`RandomForest(n_estimators=100, max_depth=None, min_samples_leaf=1, max_features=1.0, random_state=42, standardise=False, forecast_strategy="recursive", steps=None, label=None, formula=None, data_transformation=None)`

`XGBoost(n_estimators=100, max_depth=6, learning_rate=0.1, subsample=1.0, colsample_bytree=1.0, random_state=42, standardise=False, forecast_strategy="recursive", steps=None, label=None, formula=None, data_transformation=None)`

`ForecastBVAR(stationary=True, forecasts_type="mean", n_lags=1, model="natural_conjugate", minnesota=True, soc=True, sur=True, covid=False, covid_dates=None, optimisation_method="ml", cv_options=None, nb_restart=5, n_samples=1000, progressbar=True, mode_only=False, label=None, formula=None, data_transformation=None, method="andersson_et_al", N_draws=5000, N_burn=None, base_value=None, optim_random_state=42, sampling_random_state=42, forecast_random_state=42)`

`ForecastRlm(lags=1, **kwargs)`

`RandomForest` and `XGBoost` inherit the tree regression contract and require at least one feature from `X` or target lags. `ForecastBVAR` is a realtime wrapper around `bvar.BVAR`; its wrapper parameter is intentionally `mode_only`, while direct `bvar.BVAR.sample()` uses `point_only`. It supports unconditional and conditional forecasts through `y_steps_ahead` and `y_sources`. `ForecastRlm` calls R's `lm()` and requires R plus the runtime dependencies described by its own script.

### Mixed-frequency and Fable models

`ForecastBridgeOLS(aggregation="mean", fit_intercept=True, forecast_strategy="recursive", steps=None, scale=False, label=None, formula=None, data_transformation=None, drop_nans=False, align_start_dates=True)`

`ForecastMIDAS(method="almon", n_lags=6, n_pars_weights=2, estimator=None, horizons=None, start_lag=0, dummy_periods=None, n_ar_lags=0, label=None, formula=None, data_transformation=None)`

`ForecastMultiMIDAS(variables, method="almon", n_lags=3, n_pars_weights=2, estimator=None, horizons=None, start_lag=0, dummy_periods=None, n_ar_lags=0, label=None, formula=None, data_transformation=None)`

`ForecastMIDASCombo(combo_specs, horizons=3, regressor_frequencies=None, label=None, formula=None, aggregate_decomp=False, data_transformation=None)`

`RFableModel(spec, index="auto", allow_xreg=True, label=None, formula=None, data_transformation=None, **params)`

`RFableETS(error=None, trend=None, season="N", period=None, index="auto", label=None, formula=None, **kwargs)`

`RFableARIMA(p=None, d=None, q=None, seasonal=False, P=None, D=None, Q=None, period=None, xreg=None, index="auto", label=None, formula=None, **kwargs)`

`ForecastBridgeOLS` accepts a quarterly target and monthly or quarterly regressors. Monthly regressors are aggregated by complete-quarter means; partial quarters remain missing. `ForecastMIDAS` uses one monthly regressor, `ForecastMultiMIDAS` uses named variables and can mix monthly and quarterly specifications, and `ForecastMIDASCombo` consumes a root `ComboSpec` tree. MIDAS wrappers own their ragged-edge handling and use the nowcast-midas weighting schemes `almon`, `exp_almon`, `beta`, and `unrestricted`.

`RFableModel` evaluates a trusted Fable R expression such as `ARIMA(value ~ 1 + pdq(1, 0, 0))`. `RFableETS` builds an ETS specification from error, trend, season, and period. `RFableARIMA` builds non-seasonal and, when `seasonal=True`, seasonal `pdq`/`PDQ` terms; `P`, `D`, `Q`, and `period` require seasonal mode. These wrappers require the R/Fable runtime.

## Data transformations

`DataTransformationPipeline(data_transformation)` is the reusable pipeline for raw wide and long-form inputs. Its public methods are:

`apply(outturns, forecasts, y_variables, X_variables)`

`filter(data, variables)`

`reconstruct_levels(forecasts, outturns, y_variables, frequency=None)`

`transform_fit_inputs(y, X=None, y_variables, X_variables=None, frequency=None, frequencies=None, y_input_metrics=None, X_input_metrics=None)`

`transform_forecast_inputs(y_history, y_conditioning=None, X_history=None, X_future=None, y_variables, X_variables=None, frequency=None, frequencies=None, y_input_metrics=None, X_input_metrics=None, y_conditioning_input_metrics=None, X_conditioning_input_metrics=None)`

`ResolvedTransformationPlan` is the root-exported alias for the fitted `FittedDataTransformation` record. `ModelInputRequirements` describes a model's requested metrics and exposes `y_mapping` and `X_mapping`. `InputMetricMapping` freezes one role's source mapping and exposes `mapping`. `RawInputBundle` carries raw history and conditioning frames with role-specific metric provenance. `PreparedModelInputs` carries transformed `y`, `X`, and their selected metrics.

Supported metrics are `levels`, `logs`, `log diff`, `diff`, `pop`, and `yoy`. The transformation mapping is variable to metric. `logs` is the natural log; `diff` is a first difference; `log diff` differences logs; `pop` is period-on-period percentage growth; and `yoy` uses 12 monthly or 4 quarterly periods. Frequencies are inferred per raw column as `M` or `Q`; explicit `frequencies` can be supplied for wide inputs. Derived metrics are computed from levels, and future paths are combined before differencing so the first future value has the correct historical base.

With `reconstruct_levels=True`, realtime storage adds level forecasts for `logs`, `diff`, and `log diff` when level outturns are available. Set it to `False` to keep the native metric in `native_forecasts`. The first leading NaN from `diff`, `log diff`, `pop`, or `yoy` can be removed with `drop_transformation_nans=True`, the default. Interior missing observations are not treated as leading rows.

## Ragged regressors and dummies

`X_imputation` is applied to models whose `_needs_ragged_edge_imputation` flag is true. Valid values are `None`, `"zero"`, `"last"`, `"mean"`, and `"ar1_t"`. The option pads missing regressor dates at fit and forecast time:

| Value | Fill |
| --- | --- |
| `None` | Leave the regressor unchanged. |
| `"zero"` | Fill with zero. |
| `"last"` | Repeat the last observed value. |
| `"mean"` | Use the in-sample column mean. |
| `"ar1_t"` | Simulate an AR(1) path with Student-t innovations. |

MIDAS models set this flag false because they use their own ragged-edge information dates. Dummies are deterministic point columns generated from the date index and are never imputed. Dates may be a list, or a named mapping; all-zero dummies are removed from the fitted design and the same surviving columns are used at forecast time.

## Forecast trees

`TreeNode(transform, children, name=None, target=None)`

`ForecastTree(spec, label=None, data_transformation=None)`

`TreeNode` accepts a callable `transform` or a `ForecastModel` and a non-empty list of child models or nodes. A callable receives a dictionary of child DataFrames reduced to its `target`; a model transform fits on child component columns. `name` identifies a node and child model `label` identifies a leaf. `child_names`, `all_leaves()`, and `nodes()` expose the graph. Names must be unique across distinct objects and cycles are rejected. The same object may be reused in multiple branches.

`ForecastTree` fits leaves and model-backed nodes bottom-up, keeps `leaf_forecasts_` and `node_forecasts_`, and returns the root result. Its `data_transformation` is the fallback for leaves and nested trees without an own pipeline. A model-backed root selects its own target via its formula; a callable root can use `target`.

For a MIDAS combination tree, `ForecastMIDASCombo` accepts a root `ComboSpec` whose nested specs may include `MidasSpec`, `OLSSpec`, and `MultiMidasSpec`. The root name selects the returned forecast and `aggregate_decomp` controls component aggregation.

## Decomposition

Pass `decomp=True` to `ForecastModel.forecast()` or `RealTimeModel.forecast()`. Linear models and MIDAS-family models provide decompositions; unsupported models return `None`. Contributions must sum to the forecast for every horizon and target.

### Model-local decomposition (`ForecastResult.decomposition`)

The model's `_forecast_decomp()` hook supplies the minimal decomposition. The validated `ForecastResult.decomposition` contract is:

| Field | Requirement and meaning |
| --- | --- |
| `forecast_horizon` | Required integer in `0..steps-1`. |
| `component` | Required non-missing string naming the component. |
| `contribution` | Required finite numeric contribution in the model's output metric. |
| `weight` | Required column; `weight` is a required column but its values are nullable. It is typically a coefficient, and is null for components without a usable coefficient. |
| `variable` | Conditional. `variable` is required for multi-target models and omitted for a single target. |

For a single-target model, realtime attaches the target name when `variable` is omitted. A model can return extra model-specific columns, but the five fields above are the complete documented local schema. The local result does not yet contain realtime dates, vintage metadata, decomposition type, or revision attribution.

### RealTimeModel-augmented decomposition rows

`RealTimeModel` preserves the local fields and adds the following complete schema to `runner.decompositions`:

| Field | Requirement and meaning |
| --- | --- |
| `variable` | Required target variable; inferred for a single-target local result and checked for multi-target output. |
| `date` | Required absolute forecast target date. |
| `forecast_horizon` | Required horizon from the model-local decomposition. |
| `frequency` | Required target frequency, normally `"M"` or `"Q"`. |
| `source` | Required model label, optionally combined with the realtime `label`. |
| `vintage_date` | Required current vintage date. |
| `base_vintage_date` | Required nullable timestamp; `base_vintage_date` is null for level rows and is the previous vintage for revision rows. |
| `decomposition` | Required value: `"level"` for one-vintage rows or `"revision"` for between-vintage attribution rows. |
| `component` | Required component name from the local decomposition. |
| `revision_source` | Required nullable value; `revision_source` is null for level rows and is `"news"`, `"reestimation"`, or `"interaction"` for revision rows. |
| `contribution` | Required finite numeric contribution in the model's native output metric. |
| `weight` | Required nullable local weight carried into the realtime row. |
| `news` | Required field whose value is nullable. `news` is nullable: it is normally null on level rows unless supplied by the model; on revision rows it is `contribution / weight` when `weight` is non-null and non-zero, otherwise null. |
| `forecast_metric` | Required native output metric for the target; decomposition contributions are not reconstructed to levels. |

Level rows have `base_vintage_date` and `revision_source` null. For each transition between consecutive vintages, revision rows use the prior vintage as `base_vintage_date` and identify the attribution with `revision_source`. The numeric `news` field is distinct from the `"news"` revision-source label. Decomposition is sequential and is not available with `parallel=True`.

## External runtimes

`ExternalModel(script, debug=None, label=None, formula=None, data_transformation=None, subprocess_timeout=None, **params)`

`RModel(script, debug=None, label=None, formula=None, data_transformation=None, subprocess_timeout=None, **params)`

`MATLABModel(script, debug=None, label=None, formula=None, data_transformation=None, subprocess_timeout=None, **params)`

`JuliaModel(script, debug=None, label=None, formula=None, data_transformation=None, subprocess_timeout=None, **params)`

`ExternalModel` is the abstract bridge. Subclasses implement `_fit_command` and `_forecast_command`; the base class manages a fresh `cache_dir`, Parquet files, parameter serialisation, subprocess execution, timeout handling, and forecast validation. Supported `**params` types are `str`, `bool`, `int`, and `float`; they are written to `params.parquet`. `debug` is `None`, `"fit"`, or `"forecast"`. A positive `subprocess_timeout` raises `ExternalProcessTimeoutError` when exceeded, and a non-zero process raises `ExternalProcessError`.

R scripts define trusted `fit(y, X, params)` and `forecast(model, steps, X, y, params)` functions. MATLAB uses a function with `'fit'` and `'forecast'` actions; Julia defines the same two functions. `X` is empty when no regressors are configured. External forecast output must be a numeric table/DataFrame with exactly `steps` rows and one column per fitted target. The external language executables and their Parquet libraries are runtime prerequisites; constructing a wrapper alone does not run them.

## Quick workflow

```text
model = rt.models.ForecastRidge(
    cv=5,
    scale=True,
    data_transformation={"cpisa": "pop", "gdpkp": "pop"},
)
runner = rt.RealTimeModel(data=data, models=model)
runner.forecast(
    y_variables=["cpisa"],
    X_variables=["gdpkp"],
    step_frequency="Q",
    steps=12,
    y_lags=4,
    X_lags=1,
    X_imputation="last",
    decomp=True,
)
```

The public result is `runner.data`; model-local results are `ForecastResult.forecast` and `ForecastResult.decomposition`. Keep `step_frequency` on the vintage orchestrator and `frequency` on direct model `fit()`/`forecast()`/`predict()` calls.

<!-- BEGIN GENERATED API -->
## API

```json
{
  "exports": {
    "forecast_realtime": [
      "ExternalModel",
      "ForecastContext",
      "ForecastModel",
      "ForecastResult",
      "ForecastTree",
      "Formula",
      "InputMetricMapping",
      "JuliaModel",
      "MATLABModel",
      "ModelInputRequirements",
      "PreparedModelInputs",
      "RModel",
      "RawInputBundle",
      "RealTimeModel",
      "ResolvedTransformationPlan",
      "TreeNode",
      "generate_synthetic_data",
      "models"
    ],
    "forecast_realtime.models": [
      "ForecastBVAR",
      "ForecastBridgeOLS",
      "ForecastElasticNet",
      "ForecastLasso",
      "ForecastMIDAS",
      "ForecastMIDASCombo",
      "ForecastMultiMIDAS",
      "ForecastOLS",
      "ForecastRidge",
      "ForecastRlm",
      "RFableARIMA",
      "RFableETS",
      "RFableModel",
      "RandomForest",
      "XGBoost"
    ]
  },
  "package": "forecast_realtime",
  "signatures": {
    "forecast_realtime.ExternalModel": "(script: str, *, debug: str | None = None, label: str | None = None, formula: str | None = None, data_transformation: dict[str, str] | None = None, subprocess_timeout: float | None = None, **params)",
    "forecast_realtime.ForecastContext": "(y_history: pandas.DataFrame, X_history: pandas.DataFrame | None, y_conditioning: pandas.DataFrame | None = None, X_conditioning: pandas.DataFrame | None = None, forecast_origin: pandas.Timestamp | None = None, y_conditioning_input_metrics: dict[str, str] | None = None, X_conditioning_input_metrics: dict[str, str] | None = None) -> None",
    "forecast_realtime.ForecastModel": "(label: str | None = None, formula: str | None = None, data_transformation: dict[str, str] | None = None, align_start_dates: bool = False)",
    "forecast_realtime.ForecastResult": "(forecast=None, decomposition: pandas.DataFrame | None = None, forecast_origin: pandas.Timestamp | None = None, steps: int | None = None, expected_columns: list[str] | None = None, forecast_dates_include_origin: bool = False)",
    "forecast_realtime.ForecastTree": "(spec: 'TreeNode', label: 'str | None' = None, data_transformation: 'dict[str, str] | None' = None)",
    "forecast_realtime.Formula": "(formula_str: str)",
    "forecast_realtime.InputMetricMapping": "(values: tuple[tuple[str, str], ...] = ()) -> None",
    "forecast_realtime.JuliaModel": "(script: str, *, debug: str | None = None, label: str | None = None, formula: str | None = None, data_transformation: dict[str, str] | None = None, subprocess_timeout: float | None = None, **params)",
    "forecast_realtime.MATLABModel": "(script: str, *, debug: str | None = None, label: str | None = None, formula: str | None = None, data_transformation: dict[str, str] | None = None, subprocess_timeout: float | None = None, **params)",
    "forecast_realtime.ModelInputRequirements": "(y: tuple[tuple[str, str], ...] = (), X: tuple[tuple[str, str], ...] = ()) -> None",
    "forecast_realtime.PreparedModelInputs": "(y: pandas.DataFrame, X: pandas.DataFrame | None, y_metric: str | None = None, X_metrics: tuple[tuple[str, str], ...] = ()) -> None",
    "forecast_realtime.RModel": "(script: str, *, debug: str | None = None, label: str | None = None, formula: str | None = None, data_transformation: dict[str, str] | None = None, subprocess_timeout: float | None = None, **params)",
    "forecast_realtime.RawInputBundle": "(y_history: pandas.DataFrame, X_history: pandas.DataFrame | None = None, y_conditioning: pandas.DataFrame | None = None, X_conditioning: pandas.DataFrame | None = None, y_history_metrics: forecast_realtime.data_transformation.InputMetricMapping = InputMetricMapping(values=()), X_history_metrics: forecast_realtime.data_transformation.InputMetricMapping = InputMetricMapping(values=()), y_conditioning_metrics: forecast_realtime.data_transformation.InputMetricMapping = InputMetricMapping(values=()), X_conditioning_metrics: forecast_realtime.data_transformation.InputMetricMapping = InputMetricMapping(values=())) -> None",
    "forecast_realtime.RealTimeModel": "(data, models: forecast_realtime.forecast_model.ForecastModel | list[forecast_realtime.forecast_model.ForecastModel] = None)",
    "forecast_realtime.ResolvedTransformationPlan": "(data_transformation: tuple[tuple[str, str], ...] | None, y_input_metrics: tuple[tuple[str, str], ...], X_input_metrics: tuple[tuple[str, str], ...], y_variables: tuple[str, ...], X_variables: tuple[str, ...] | None, y_frequencies: tuple[tuple[str, str], ...], X_frequencies: tuple[tuple[str, str], ...], frequency: str | None, X_imputation: str | None, pipeline_source: str, y_conditioning_input_metrics: tuple[tuple[str, str], ...] = (), X_conditioning_input_metrics: tuple[tuple[str, str], ...] = ()) -> None",
    "forecast_realtime.TreeNode": "(transform: 'TransformType', children: 'list[ForecastModel | TreeNode]', name: 'str | None' = None, target: 'str | None' = None) -> None",
    "forecast_realtime.generate_synthetic_data": "(N: 'int' = 10, mode: 'str' = 'dense', seed: 'int' = 20260101, first_period='1980-01-31', endpoint='2025-12-31', publication_lags: 'bool' = True, year: 'int' = 2024) -> 'pd.DataFrame'",
    "forecast_realtime.models.ForecastBVAR": "(stationary: bool = True, forecasts_type: Literal['mean', 'median'] = 'mean', n_lags: int = 1, model: str = 'natural_conjugate', minnesota: bool = True, soc: bool = True, sur: bool = True, covid: bool = False, covid_dates: list = None, optimisation_method: str = 'ml', cv_options: dict | None = None, nb_restart: int = 5, n_samples: int = 1000, progressbar: bool = True, mode_only: bool = False, label: str | None = None, formula: str | None = None, data_transformation: dict[str, str] | None = None, method: str = 'andersson_et_al', N_draws: int = 5000, N_burn: int | None = None, base_value: numpy.ndarray | None = None, optim_random_state: int | None = 42, sampling_random_state: int | None = 42, forecast_random_state: int | None = 42)",
    "forecast_realtime.models.ForecastBridgeOLS": "(aggregation: str = 'mean', fit_intercept: bool = True, forecast_strategy: str = 'recursive', steps: int | None = None, scale: bool = False, label: str | None = None, formula: str | None = None, data_transformation: dict[str, str] | None = None, drop_nans: bool = False, align_start_dates: bool = True)",
    "forecast_realtime.models.ForecastElasticNet": "(fit_intercept: bool = True, forecast_strategy: str = 'recursive', steps: int | None = None, scale: bool = False, alpha: float | None = None, l1_ratio: float = 0.5, cv: int | sklearn.model_selection._split.BaseCrossValidator | None = None, label: str | None = None, alphas: numpy.ndarray | list | None = None, formula: str | None = None, data_transformation: dict[str, str] | None = None, drop_nans: bool = False, align_start_dates: bool = True)",
    "forecast_realtime.models.ForecastLasso": "(fit_intercept: bool = True, forecast_strategy: str = 'recursive', steps: int | None = None, scale: bool = False, alpha: float | None = None, cv: int | sklearn.model_selection._split.BaseCrossValidator | None = None, label: str | None = None, alphas: numpy.ndarray | list | None = None, formula: str | None = None, data_transformation: dict[str, str] | None = None, drop_nans: bool = False, align_start_dates: bool = True)",
    "forecast_realtime.models.ForecastMIDAS": "(method: str = 'almon', n_lags: int = 6, n_pars_weights: int = 2, estimator: str | None = None, horizons: list | None = None, start_lag: int = 0, dummy_periods: list | None = None, n_ar_lags: int = 0, label: str | None = None, formula: str | None = None, data_transformation: dict[str, str] | None = None) -> None",
    "forecast_realtime.models.ForecastMIDASCombo": "(combo_specs: nowcast_midas.specs.ComboSpec, horizons: int = 3, regressor_frequencies: dict[str, str] | None = None, label: str | None = None, formula: str | None = None, aggregate_decomp: bool | None = False, data_transformation: dict[str, str] | None = None) -> None",
    "forecast_realtime.models.ForecastMultiMIDAS": "(variables: list, method: str = 'almon', n_lags: int = 3, n_pars_weights: int = 2, estimator: str | None = None, horizons: list | None = None, start_lag: int = 0, dummy_periods: list | None = None, n_ar_lags: int = 0, label: str | None = None, formula: str | None = None, data_transformation: dict[str, str] | None = None) -> None",
    "forecast_realtime.models.ForecastOLS": "(fit_intercept: bool = True, forecast_strategy: str = 'recursive', steps: int | None = None, scale: bool = False, label: str | None = None, formula: str | None = None, data_transformation: dict[str, str] | None = None, drop_nans: bool = False, align_start_dates: bool = True)",
    "forecast_realtime.models.ForecastRidge": "(fit_intercept: bool = True, forecast_strategy: str = 'recursive', steps: int | None = None, scale: bool = False, alpha: float | None = None, cv: int | sklearn.model_selection._split.BaseCrossValidator | None = None, label: str | None = None, alphas: numpy.ndarray | list | None = None, alpha_scaling: str = 'mean', formula: str | None = None, data_transformation: dict[str, str] | None = None, drop_nans: bool = False, align_start_dates: bool = True)",
    "forecast_realtime.models.ForecastRlm": "(lags: int = 1, **kwargs)",
    "forecast_realtime.models.RFableARIMA": "(*, p: int | None = None, d: int | None = None, q: int | None = None, seasonal: bool = False, P: int | None = None, D: int | None = None, Q: int | None = None, period: int | str | None = None, xreg: str | None = None, index: str = 'auto', label: str | None = None, formula: str | None = None, **kwargs)",
    "forecast_realtime.models.RFableETS": "(*, error: str | None = None, trend: str | None = None, season: str | None = 'N', period: int | str | None = None, index: str = 'auto', label: str | None = None, formula: str | None = None, **kwargs)",
    "forecast_realtime.models.RFableModel": "(spec: str, *, index: str = 'auto', allow_xreg: bool = True, label: str | None = None, formula: str | None = None, data_transformation=None, **params)",
    "forecast_realtime.models.RandomForest": "(n_estimators: int = 100, max_depth: int | None = None, min_samples_leaf: int = 1, max_features: str | int | float | None = 1.0, random_state: int = 42, standardise: bool = False, forecast_strategy: str = 'recursive', steps: int | None = None, label: str | None = None, formula: str | None = None, data_transformation: dict[str, str] | None = None)",
    "forecast_realtime.models.XGBoost": "(n_estimators: int = 100, max_depth: int = 6, learning_rate: float = 0.1, subsample: float = 1.0, colsample_bytree: float = 1.0, random_state: int = 42, standardise: bool = False, forecast_strategy: str = 'recursive', steps: int | None = None, label: str | None = None, formula: str | None = None, data_transformation: dict[str, str] | None = None)"
  },
  "version": "0.5.3"
}
```
<!-- END GENERATED API -->