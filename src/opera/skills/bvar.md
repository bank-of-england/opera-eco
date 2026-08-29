---
name: bvar
description: Use this skill when working with the `bvar` Python package for Bayesian Vector Autoregressions.
module-package: bvar
module-version: "0.3.1"
---

# bvar

`bvar` estimates Bayesian vector autoregressions with Natural-Conjugate or Independent-NIW priors. The public API is built around `BVAR`; fitted models store posterior draws, point estimates, forecasts, and GIRFs on the instance.

## Canonical imports

```python
import bvar as bv
from bvar import (
    BVAR,
    GIRF,
    IndependentNIW,
    NaturalConjugate,
    compare_forecasts,
    cumulative_change,
    mcmc_posterior,
    plot_delta_forecast,
    plot_density,
    plot_histogram,
    simulate_var,
)
from bvar.models import (
    IndependentNIW,
    NaturalConjugate,
    PosteriorState,
    SamplingModel,
    SamplingResult,
)
from bvar.forecast import Forecasting, compare_forecasts
from bvar.girf import GIRF
from bvar.diagnostics import mcmc_posterior
from bvar.plots import (
    PlotBVAR,
    PlotGIRF,
    plot_delta_forecast,
    plot_density,
    plot_histogram,
)
from bvar.utils import cumulative_change, simulate_var
```

The root exports are the first line of imports. The submodule exports above are the canonical paths for the same implementation classes and helpers.

## Data contract

`BVAR` accepts a `pandas.DataFrame` with at least two numeric columns and a unique, increasing regular `DatetimeIndex` or `PeriodIndex`. Values must be finite. The package converts a datetime index to periods internally and keeps the input frequency and calendar anchor for forecast dates. There must be at least one observation after removing `n_lags` lags.

The package does not transform the values during sampling. If a series was logged or differenced before fitting, record that fact with `data_transformation` so forecast output can be reconstructed.

## BVAR

Constructor contract:

`BVAR(n_lags, model, stationary, optimisation_method="ml", random_state=None)`

`n_lags` is positive. `model` is a `SamplingModel`, normally `NaturalConjugate` or `IndependentNIW`. `stationary=False` treats variables as levels for prior dummy observations; `stationary=True` treats them as stationary. `optimisation_method` is `"ml"`, `"cross_validation"`, or `"none"`. The supplied sampling model is deep-copied. `random_state` seeds a private `numpy.random.Generator` and does not alter NumPy's global RNG.

After fitting, the main attributes are:

| Attribute | Meaning |
| --- | --- |
| `beta` | Posterior coefficient draws, shape `(N_draws, n*k)`. |
| `sigma` | Flattened covariance draws, shape `(N_draws, n*n)`. |
| `beta_point` | Posterior point estimate of the coefficient vector, shape `(n*k,)`. |
| `sigma_point` | Posterior point estimate of the flattened covariance matrix, shape `(n*n,)`. |
| `posterior_state_point` | `PosteriorState` containing the point estimates. |
| `n`, `k`, `nk`, `T` | Variables, regressors per equation, total coefficients, and effective observations. |
| `df_data`, `data` | Copied indexed input and its NumPy array. |
| `forecast_unconditional` | Forecast draw array after `forecast()` or `recursive_forecast()`. |
| `forecast_conditional` | Conditional forecast draw array, or `None`. |
| `irf_draws`, `irf_df` | GIRF draws and long-format GIRF results. |

Properties:

```text
bvar.is_fitted                 # bool
bvar.dimensions                # (n_vars, n_regressors, n_total_coeffs, n_effective_obs)
```

## Prior models

`NaturalConjugate(minnesota=True, soc=True, sur=True, covid=False, covid_dates=None)`

`IndependentNIW(c2=0.5, minnesota=True, soc=True, sur=True, covid=False, covid_dates=None)`

`NaturalConjugate` uses the closed-form Normal-Inverse-Wishart posterior. It supports marginal-likelihood optimisation and does not require burn-in. `IndependentNIW` uses a Gibbs sampler with independent priors for coefficients and covariance, requires burn-in, and has no closed-form posterior point-only fit. Its extra `c2` parameter controls cross-variable shrinkage.

Common prior flags are Minnesota shrinkage (`minnesota`), sum-of-coefficients dummy observations (`soc`), single-unit-root dummy observations (`sur`), and COVID dummy observations (`covid`). `covid_dates` is an optional two-element date range.

Set hyperparameters before fitting when using `optimisation_method="none"`:

`set_priors(c1=0.2, c3=2.0, lambda_constant=10.0, mu=1.0, theta=1.0, lambda_covid=10000.0, c1_mode=0.2, c1_sd=0.4, c3_mode=2.0, c3_sd=0.5, mu_mode=1.0, mu_sd=1.0, theta_mode=1.0, theta_sd=1.0)`

`IndependentNIW.set_priors()` additionally accepts `c2`. The `*_mode` and `*_sd` names are Gamma hyperprior parameters; they are not posterior result attribute names.

## Fit and sample

`optimise_hyperparameters(data, nb_restart=0, initial_values=None, target_series=None, cv_options=None, add_priors=True, random_state=None)`

`sample(data, N_draws=None, N_burn=None, point_only=False, progressbar=True, data_transformation=None, random_state=None)`

`optimise_hyperparameters()` returns `None` and updates the owned prior parameters. With `"ml"`, `NaturalConjugate` maximises its closed-form marginal likelihood. With `"cross_validation"`, the model must support `point_only=True`; `"none"` leaves manually set values in place.

`sample()` returns `None` and stores `beta`, `sigma`, `beta_point`, `sigma_point`, and `posterior_state_point`. `N_draws=None` means 5000 retained draws. `N_burn` is ignored for the direct Natural-Conjugate sampler; for Independent-NIW it defaults to half of the requested draws and must be less than `N_draws`. `point_only=True` is supported by Natural-Conjugate and is rejected by Independent-NIW.

The sampler result type is `SamplingResult` with `beta_draws`, `sigma_draws`, `beta_point`, `sigma_point`, optional `extras_point`, and optional `extras_draws`. `PosteriorState` carries `beta`, `sigma`, and optional model-owned `extras`; `.copy()` isolates all of them.

## Forecasting

`forecast(H, constraint_mean=None, constraint_variance=None, constraint_shape=None, method="andersson_et_al", N_draws=5000, N_burn=None, point_only=False, format=False, quantiles=None, base_value=None, constraint_sampler=None, progressbar=False, transformations=None, random_state=None)`

`recursive_forecast(H, N_draws=5000, point_only=False, progressbar=False, random_state=None)`

Both methods return `self`. `forecast()` stores forecast draws in `forecast_unconditional` and, when constraints are supplied, in `forecast_conditional`. `H` is the number of periods after the last fitted period. `N_draws` is capped at the number of stored posterior draws. `point_only=True` uses the stored point estimates and returns one draw.

`constraint_mean`, `constraint_variance`, and `constraint_shape` are arrays of shape `(H, n)`; `NaN` means unconstrained. Mean constraints use the Waggoner-Zha algorithm by default through `method="andersson_et_al"`. Variance and shape constraints provide soft or skewed conditioning. A custom `constraint_sampler` can replace the conditional sampler.

`format=True` creates long DataFrames on `df_forecasts_unconditional` and `df_forecasts_conditional` with columns `date, quantile, variable, value`. `quantiles=None` defaults to `[0.16, 0.5, 0.84]`. `base_value` is required to reconstruct forecast tails for `diff` or `log diff` data. `recursive_forecast()` is the simpler recursive unconditional path and accepts the same draw control without constraints.

## Forecast transformations

Pass the state used before fitting to `sample()`:

```text
bvar.sample(data, data_transformation={"GDP": "log_diff", "CPI": "levels"})
bvar.forecast(H=8, transformations={"GDP": "qoq", "CPI": "yoy"}, base_value=last_levels)
```

Supported input states are `"levels"`, `"logs"` (also `"log_levels"`), `"diff"`, and `"log_diff"`. Supported forecast transformations are `"qoq"` and `"yoy"`. Log differences are cumulatively exponentiated and ordinary differences are cumulatively added to `base_value` before the output growth rate is computed.

## GIRFs

`compute_girf(H, N_draws=5000, point_only=False, data_transformation=None, response_type=None, shock_size=None, progressbar=False, base_value=None)`

`compute_girf()` returns `self` and stores `irf_draws` with shape `(N_draws, H+1, n, n)`, `irf_var_names`, `irf_H`, `irf_response_type`, and `irf_shock_size`. `irf_draws[d, h, s, r]` is the response of variable `r` at horizon `h` to a shock in variable `s` for draw `d`. `h=0` is contemporaneous.

`response_type` maps variables to `"raw"`, `"raw_cumulated"`, `"level_change"`, `"pct_change"`, `"change_yoy"`, or `"pct_change_yoy"`. `shock_size` supplies a shock in natural units; omitted shocks are one standard deviation. `data_transformation` and `base_value` describe how logged or differenced variables become level responses. `base_value` may be a scalar or one value per variable and must be supplied for level or percentage responses of differenced data.

## Plotting and comparison

Methods inherited by `BVAR`:

```text
bvar.plot_fitted_values(confidence_level=95, max_cols=3, figsize_per_plot=(5, 3), var_names=None)
bvar.plot_forecast(alpha=0.05, max_cols=3, figsize_per_plot=(5, 3), var_names=None, from_date=None)
bvar.plot_girf(shock_var=None, response_var=None, quantiles=(0.16, 0.50, 0.84), figsize_per_plot=(4.0, 3.0), max_cols=4, title=None, zero_line=True)
```

Standalone plotting functions return `(fig, ax)` for density and histogram; `plot_delta_forecast()` and the BVAR plotting methods display their figures:

```text
plot_density(data, labels=None, title=None, figsize=(10, 6), bw=None, ax=None)
plot_histogram(data, labels=None, title=None, figsize=(10, 6), bins=30, alpha=0.5, colors=None, ax=None)
plot_delta_forecast(df, var_names=None, title="Forecast revision", figsize_per_plot=(5, 3.5), show="difference", n_rows=1, metric_labels=None, extra_data=None)
mcmc_posterior(draws, true_pars=None, max_cols=3, figsize_per_plot=(5, 3))
```

`plot_delta_forecast()` expects the long comparison schema and supports `show="difference"` or `show="forecasts"`. `metric_labels` appends a metric to subplot titles; `extra_data` overlays additional long-format series when showing forecasts. `plot_girf()` returns a Matplotlib `Figure` and accepts variable names, zero-based indices, or lists.

Compare two `forecast(..., format=True)` results with:

```text
compare_forecasts(df_forecast_a, df_forecast_b, H, labels=None, n_outturns=0)
```

The returned DataFrame contains the two named forecasts and a `difference` series with columns `date, quantile, variable, value, type`.

## Simulation helpers

```text
simulate_var(T, n, n_lags, covid=False, levels=False, ar_mat=None, constant=None, Sigma=None, seed=None)
cumulative_change(data, levels)
```

`simulate_var()` returns `(data, true_b, true_sigma, eps)`, with a quarterly `PeriodIndex`; `levels=True` integrates the simulated paths. `seed` may be an integer or a `numpy.random.Generator`. `cumulative_change()` is a convenience for forecast-evaluation transformations.

<!-- BEGIN GENERATED API -->
## API

```json
{
  "exports": {
    "bvar": [
      "BVAR",
      "GIRF",
      "IndependentNIW",
      "NaturalConjugate",
      "compare_forecasts",
      "cumulative_change",
      "mcmc_posterior",
      "plot_delta_forecast",
      "plot_density",
      "plot_histogram",
      "simulate_var"
    ],
    "bvar.forecast": [
      "Forecasting",
      "compare_forecasts"
    ],
    "bvar.models": [
      "IndependentNIW",
      "NaturalConjugate",
      "PosteriorState",
      "SamplingModel",
      "SamplingResult"
    ],
    "bvar.plots": [
      "PlotBVAR",
      "PlotGIRF",
      "plot_delta_forecast",
      "plot_density",
      "plot_histogram"
    ]
  },
  "package": "bvar",
  "signatures": {
    "bvar.BVAR": "(n_lags: 'int', model: 'SamplingModel', stationary: 'bool', optimisation_method: 'str' = 'ml', random_state: 'int | None' = None) -> 'None'",
    "bvar.GIRF": "()",
    "bvar.IndependentNIW": "(c2: 'float' = 0.5, minnesota: 'bool' = True, soc: 'bool' = True, sur: 'bool' = True, covid: 'bool' = False, covid_dates: 'list | None' = None) -> 'None'",
    "bvar.NaturalConjugate": "(minnesota: 'bool' = True, soc: 'bool' = True, sur: 'bool' = True, covid: 'bool' = False, covid_dates: 'list | None' = None) -> 'None'",
    "bvar.compare_forecasts": "(df_forecast_a: 'pd.DataFrame', df_forecast_b: 'pd.DataFrame', H: 'int', labels: 'list[str] | None' = None, n_outturns: 'int' = 0) -> 'pd.DataFrame'",
    "bvar.cumulative_change": "(data: numpy.ndarray, levels: numpy.ndarray) -> numpy.ndarray",
    "bvar.forecast.Forecasting": "()",
    "bvar.forecast.compare_forecasts": "(df_forecast_a: 'pd.DataFrame', df_forecast_b: 'pd.DataFrame', H: 'int', labels: 'list[str] | None' = None, n_outturns: 'int' = 0) -> 'pd.DataFrame'",
    "bvar.mcmc_posterior": "(draws: numpy.ndarray, true_pars: numpy.ndarray | None = None, max_cols: int = 3, figsize_per_plot: tuple = (5, 3)) -> None",
    "bvar.models.IndependentNIW": "(c2: 'float' = 0.5, minnesota: 'bool' = True, soc: 'bool' = True, sur: 'bool' = True, covid: 'bool' = False, covid_dates: 'list | None' = None) -> 'None'",
    "bvar.models.NaturalConjugate": "(minnesota: 'bool' = True, soc: 'bool' = True, sur: 'bool' = True, covid: 'bool' = False, covid_dates: 'list | None' = None) -> 'None'",
    "bvar.models.PosteriorState": "(beta: 'np.ndarray', sigma: 'np.ndarray', extras: 'Any | None' = None) -> None",
    "bvar.models.SamplingModel": "(minnesota: 'bool' = True, soc: 'bool' = True, sur: 'bool' = True, covid: 'bool' = False, covid_dates: 'list | None' = None) -> 'None'",
    "bvar.models.SamplingResult": "(beta_draws: 'np.ndarray', sigma_draws: 'np.ndarray', beta_point: 'np.ndarray', sigma_point: 'np.ndarray', extras_point: 'Any | None' = None, extras_draws: 'list | None' = None) -> None",
    "bvar.plot_delta_forecast": "(df: pandas.DataFrame, var_names: list[str] | str | None = None, title: str = 'Forecast revision', figsize_per_plot: tuple = (5, 3.5), show: str = 'difference', n_rows: int = 1, metric_labels: dict | None = None, extra_data: pandas.DataFrame | None = None) -> None",
    "bvar.plot_density": "(data: numpy.ndarray, labels: list[str] | None = None, title: str | None = None, figsize: tuple = (10, 6), bw: float | str | None = None, ax: matplotlib.axes._axes.Axes | None = None) -> tuple[matplotlib.figure.Figure, matplotlib.axes._axes.Axes]",
    "bvar.plot_histogram": "(data: numpy.ndarray, labels: list[str] | None = None, title: str | None = None, figsize: tuple = (10, 6), bins: int = 30, alpha: float = 0.5, colors: list | None = None, ax: matplotlib.axes._axes.Axes | None = None) -> tuple[matplotlib.figure.Figure, matplotlib.axes._axes.Axes]",
    "bvar.plots.PlotBVAR": "()",
    "bvar.plots.PlotGIRF": "()",
    "bvar.plots.plot_delta_forecast": "(df: pandas.DataFrame, var_names: list[str] | str | None = None, title: str = 'Forecast revision', figsize_per_plot: tuple = (5, 3.5), show: str = 'difference', n_rows: int = 1, metric_labels: dict | None = None, extra_data: pandas.DataFrame | None = None) -> None",
    "bvar.plots.plot_density": "(data: numpy.ndarray, labels: list[str] | None = None, title: str | None = None, figsize: tuple = (10, 6), bw: float | str | None = None, ax: matplotlib.axes._axes.Axes | None = None) -> tuple[matplotlib.figure.Figure, matplotlib.axes._axes.Axes]",
    "bvar.plots.plot_histogram": "(data: numpy.ndarray, labels: list[str] | None = None, title: str | None = None, figsize: tuple = (10, 6), bins: int = 30, alpha: float = 0.5, colors: list | None = None, ax: matplotlib.axes._axes.Axes | None = None) -> tuple[matplotlib.figure.Figure, matplotlib.axes._axes.Axes]",
    "bvar.simulate_var": "(T: int, n: int, n_lags: int, covid: bool = False, levels: bool = False, ar_mat: numpy.ndarray | None = None, constant: numpy.ndarray | None = None, Sigma: numpy.ndarray | None = None, seed: int | numpy.random._generator.Generator | None = None) -> Tuple[pandas.DataFrame, numpy.ndarray, numpy.ndarray, numpy.ndarray]"
  },
  "version": "0.3.1"
}
```
<!-- END GENERATED API -->