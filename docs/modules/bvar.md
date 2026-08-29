# `bvar`

## Purpose

`bvar` estimates Bayesian vector autoregressions with Natural-Conjugate or Independent-NIW priors. It stores posterior draws, point estimates, forecasts, and generalised impulse responses on the fitted `BVAR` instance. OPERA also exposes it through `forecast_realtime.models.ForecastBVAR` for vintage-based forecasting.

## Features

- Bayesian VAR estimation with `NaturalConjugate` or `IndependentNIW` priors.
- Minnesota, sum-of-coefficients, single-unit-root, and COVID dummy priors.
- Unconditional and conditional forecasts with hard, soft, and skewed
    constraints.
- Generalised impulse response functions and forecast visualisations.
- Forecast transformations for levels, growth rates, and differenced data.
- Reproducible sampling through per-instance and per-call random states.

`BVAR` accepts a regular, increasing `DatetimeIndex` or `PeriodIndex` and at least two numeric series. Use `forecast_realtime` when the model must run over historical or live data vintages.

## Quick start

```python
import bvar as bv
import numpy as np

data, *_ = bv.simulate_var(T=200, n=3, n_lags=1, levels=True)

model = bv.NaturalConjugate(minnesota=True, soc=True, sur=True, covid=False)
bvar = bv.BVAR(
    n_lags=4, model=model, stationary=False, optimisation_method="ml", random_state=0
)

bvar.optimise_hyperparameters(data)
bvar.sample(data, N_draws=5000)

# Produce an unconditional forecast.
bvar.forecast(H=8)
bvar.plot_forecast(alpha=0.05)

# Compute generalised impulse responses.
bvar.compute_girf(H=20)
bvar.plot_girf(shock_var=data.columns[0])
```

### Conditional forecast

```python
H, n = 8, bvar.n
constraint_mean = np.full((H, n), np.nan)
constraint_mean[:, 0] = 2.0  # Hold variable 0 at 2.0 over the horizon.

constraint_variance = np.full((H, n), np.nan)
constraint_variance[:, 0] = 0.5  # Apply a soft constraint with standard deviation 0.5.

bvar.forecast(
    H=H, constraint_mean=constraint_mean, constraint_variance=constraint_variance
)
```

## Repository

Read the implementation and full API reference in the [bvar repository](https://github.com/bank-of-england/bvar).