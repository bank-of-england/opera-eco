# `nowcast-midas`

## Purpose

`nowcast-midas` (imported as `nowcast_midas`) implements Mixed Data Sampling (MIDAS) regressions and Staggered-Combination MIDAS (SC-MIDAS) combinations. It supports quarterly nowcasting and short-horizon forecasting from monthly indicators, with quarterly OLS for indicators already at the target frequency. The models can also be used through `forecast_realtime` for vintage-data backtesting.

## Features

- MIDAS regressions for quarterly targets and monthly indicators.
- Quarterly OLS for indicators already at the target frequency.
- `MultiMIDAS` for several monthly and quarterly regressors.
- SC-MIDAS combinations built from nested model specifications.
- Almon, exponential Almon, beta, unrestricted, average, and error-based
    weighting schemes.
- Forecast decomposition, outlier dummies, and long-format results.

Use narrow `[date, value]` frames for `MIDAS` and `OLS`. Use long-format `[date, variable, frequency, value]` data for `MultiMIDAS` and `MidasCombo`. Targets must be complete; missing regressor lags are dropped. Apply any transformations before fitting.

## Quick start

### Single MIDAS

```python
from nowcast_midas import MIDAS

from nowcast_midas.utils import sample_data

target, regressors = sample_data(n_obs=200, n_lags=6, seed=0, horizon=0)

model = MIDAS(method="almon", n_lags=6)
model.fit(target, regressors)
forecast = model.forecast(regressors)
```

### SC-MIDAS combinations

Build combinations from MIDAS, OLS, MultiMIDAS, or other combination specifications, then fit and forecast them as one model. Combinations support average, error-based, and regression weighting.

### MultiMIDAS

`MultiMIDAS` estimates several regressors jointly and can mix monthly MIDAS terms with quarterly regressors. Use `VariableSpec` to describe each input. Its forecast can be decomposed into contributions from each variable, the intercept, dummies, and autoregressive terms.

## Repository

Read the implementation and full API reference in the [nowcast-midas repository](https://github.com/bank-of-england/nowcast-midas).