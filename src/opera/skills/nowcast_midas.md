---
name: nowcast-midas
description: MIDAS & SC-MIDAS nowcasting—mixed-freq regressions + combo forecasts. Quarterly GDP-like targets from monthly indicators. MultiMIDAS multi-regressors, decomposition, realtime, dummy periods, long-fmt output.
module-package: nowcast-midas
module-version: "0.0.1"
---

# nowcast-midas

Python pkg (BoE, MIT). Quarterly nowcasting/short-horizon forecasts of low-freq targets (GDP, etc.) from high-freq indicators (monthly). Four core estimators: `MIDAS`, `MultiMIDAS`, `OLS`, `MidasCombo`. Specs: `MidasSpec`, `VariableSpec`, `MultiMidasSpec`, `OLSSpec`, `ComboSpec`. NLS via `scipy.optimize.least_squares` (Levenberg-Marquardt) + JAX autodiff.

## Package surface

The package root exports exactly these names:

```python
__all__ = [
    "MIDAS",
    "OLS",
    "ComboSpec",
    "FittedMidas",
    "FittedMultiMidas",
    "FittedOLS",
    "MidasCombo",
    "MidasSpec",
    "MultiMIDAS",
    "MultiMidasSpec",
    "OLSSpec",
    "VariableFit",
    "VariableSpec",
]
from nowcast_midas import (
    MIDAS,
    OLS,
    ComboSpec,
    FittedMidas,
    FittedMultiMidas,
    FittedOLS,
    MidasCombo,
    MidasSpec,
    MultiMIDAS,
    MultiMidasSpec,
    OLSSpec,
    VariableFit,
    VariableSpec,
)
from nowcast_midas.temporal_weights import (
    almon,
    beta,
    exp_almon,
    get_weights,
    unrestricted,
)
from nowcast_midas.combo_weights import (
    clipped_ols,
    constrained_least_squares,
    fit_average,
    fit_weights,
)
from nowcast_midas.utils import sample_combo_data, sample_data
```

The weighting functions and sample generators are submodule exports; the root export list above is authoritative.

---

## Install & quick start

```sh
pip install -e .                # runtime
pip install -e ".[dev]"         # + test/lint
pip install -e ".[docs]"        # + docs
```

Py ≥ 3.9.

```text
target, regressors, info = sample_combo_data(n_quarters=60, seed=42)
outlier = info["outlier_date"]

midas_pmi = MidasSpec("PMI", method="almon", n_lags=6, dummy_periods=[outlier])
midas_ip = MidasSpec("IP", method="almon", n_lags=6, dummy_periods=[outlier])
ols_unemp = OLSSpec("UNEMP", n_lags=1, dummy_periods=[outlier])

soft_combo = ComboSpec(
    name="soft_combo",
    sources=[midas_pmi, midas_ip],
    method="mse",
    window=8,
    discount_rate=0.95,
)
final_combo = ComboSpec(
    name="final_combo",
    sources=[soft_combo, ols_unemp],
    method="regression",
)

model = MidasCombo(combo_specs=final_combo, horizons=3)
model.fit(target=target, regressors=regressors)
oos = model.forecast()
print(model.summary(horizon=0))
```

---

## Data fmt

### `MIDAS` / `OLS`

DataFrame with two columns: `date` (datetime) and `value` (numeric). The quarterly target must contain no missing values. A `MIDAS` regressor is monthly (ME); an `OLS` regressor is quarterly (QE).

### `MidasCombo`

Long-fmt DF: `date`, `variable` (must match spec), `frequency` ('QE'|'ME'), `value`.

Apply transforms (log-diff, deflate) before import. No internal transforms.

---

## `MIDAS` — single mixed-freq model

```text
model = MIDAS(
    method="almon",  # 'exp_almon'|'beta'|'almon'|'unrestricted'
    n_lags=6,  # high-freq lags
    n_pars_weights=2,  # shape pars for almon/exp_almon
    estimator=None,  # 'ols' (almon/unrestricted) | 'nls' (others)
    horizons=[0, 4],  # forecast horizons h; fit per h
    start_lag=0,
    n_ar_lags=0,
    dummy_periods=[outlier],  # exclude from weight est
)

model.fit(target, regressors)  # sets fits_, fits_df_ (long)
fc = model.forecast(regressors_forecast)  # long: horizon, date, forecast
dec = model.forecast_decomp(regressors_forecast, regressor_name="PMI")
model.summary()
model.plot_fit()
model.plot_weights()
model.plot_forecast()
```

After fit: `fits_` (dict[h, FittedMidas]), `fits_df_` (long: date, horizon, value), `target_`, `valid_mask_`. After forecast: `forecasts_df_` (long: horizon, date, forecast). `forecast()` takes **no** `info_date`: the anchor `T_X` is always the latest date in `regressors_forecast`, and the horizon-`h` model forecasts `T_X + h` quarters.

`FittedMidas`: alpha, beta, theta, weights, fitted_values, residuals, dates, ...

**Weight schemes:**
- `'unrestricted'` → 1 coef/lag (OLS)
- `'almon'` → polynomial (degree n_pars_weights-1, OLS)
- `'exp_almon'` → exponential Almon (NLS)
- `'beta'` → Beta poly (NLS)

Only `'ols'` valid for almon/unrestricted; beta/exp_almon → NLS forced.

---

<!-- BEGIN GENERATED API -->
## API

```json
{
  "exports": {
    "nowcast_midas": [
      "ComboSpec",
      "FittedMidas",
      "FittedMultiMidas",
      "FittedOLS",
      "MIDAS",
      "MidasCombo",
      "MidasSpec",
      "MultiMIDAS",
      "MultiMidasSpec",
      "OLS",
      "OLSSpec",
      "VariableFit",
      "VariableSpec"
    ],
    "nowcast_midas.combo_weights": [
      "clipped_ols",
      "constrained_least_squares",
      "fit_average",
      "fit_weights"
    ],
    "nowcast_midas.temporal_weights": [
      "almon",
      "beta",
      "exp_almon",
      "get_weights",
      "unrestricted"
    ],
    "nowcast_midas.utils": [
      "sample_combo_data",
      "sample_data"
    ]
  },
  "package": "nowcast-midas",
  "version": "0.0.1"
}
```
<!-- END GENERATED API -->

---

## `OLS` — quarterly counterpart

Plain OLS, quarterly only. Same horizons/AR/dummy interface.

```text
ols_model = OLS(
    n_lags=1,
    start_lag=0,
    horizons=[0, 1, 2],
    n_ar_lags=0,
    dummy_periods=[outlier],
)
ols_model.fit(target, regressors)  # sets fits_, fits_df_ (long)
ols_model.forecast(regressors_forecast)  # long: horizon, date, forecast
ols_model.forecast_decomp(regressors_forecast, regressor_name="UNEMP")
```

`FittedOLS`: intercept, coef, gamma, phi, fitted_values, residuals, dates.

No `summary()` / plot methods on `OLS` — use `fits_df_` / `forecasts_df_`.

---

## `MultiMIDAS` — multi-regressor

Joint est of several regressors, each own scheme/lags/freq. Monthly (ME) → MIDAS lags; quarterly (QE) → linear.

```text
model = MultiMIDAS(
    variables=[
        VariableSpec("PMI", method="exp_almon", n_lags=6),  # NLS → nonlinear
        VariableSpec("IP", method="almon", n_lags=6),  # OLS → linear (beta=1)
        VariableSpec("UNEMP", frequency="QE", n_lags=1),  # quarterly, linear
    ],
    method="almon",
    n_lags=6,
    n_pars_weights=2,
    horizons=[0, 1],
    n_ar_lags=0,
    dummy_periods=None,
)
model.fit(target, regressors)  # sets fits_, fits_df_ (long)
fc = model.forecast(regressors)  # long: horizon, date, forecast
decomp = model.forecast_decomp(regressors)  # long component breakdown
model.summary(horizon=0)
```

**Routing:**
- All monthly almon/unrestricted → OLS (closed-form).
- Any monthly exp_almon/beta → NLS (Levenberg-Marquardt).
- Linear-in-pars terms (almon/unrestricted/quarterly) always linear, even in NLS: enters as fixed design cols, beta=1.0. Avoids scale degeneracy.

`fits_` dict[h, FittedMultiMidas]. `FittedMultiMidas`: alpha, variable_fits (dict[name, VariableFit]), gamma, phi, fitted_values, residuals, dates. `VariableFit`: beta (estimated only for exp_almon/beta), theta, weights (normalised for nonlinear terms and unnormalised for linear terms; delta vector for QE).

---

## Specs — compose pipelines

```text
MidasSpec(
    variable="PMI",
    method="almon",
    n_lags=3,
    n_pars_weights=2,
    estimator=None,
    start_lag=0,
    n_ar_lags=0,
    dummy_periods=None,
    minimum_sample_size=None,  # min fitted obs before the source is usable
)

OLSSpec(
    variable="UNEMP",
    n_lags=1,
    start_lag=0,
    n_ar_lags=0,
    dummy_periods=None,
    minimum_sample_size=None,
)

VariableSpec(
    variable="PMI",
    method="almon",
    n_lags=3,
    n_pars_weights=2,
    estimator=None,
    start_lag=0,
    frequency="ME",  # 'ME'|'QE'
)

MultiMidasSpec(
    name="multi_block",
    variables=["PMI", VariableSpec("IP", n_lags=3)],
    method="almon",
    n_lags=3,
    n_pars_weights=2,
    estimator=None,
    start_lag=0,
    n_ar_lags=0,
    dummy_periods=None,
    minimum_sample_size=None,
)

ComboSpec(
    name="final_combo",
    sources=["PMI", "UNEMP"],  # str/MidasSpec/OLSSpec/MultiMidasSpec/ComboSpec
    method="average",  # 'average'|'rmse'|'mse'|'mae'|'regression'
    window=None,  # rolling window; None=expanding
    minimum_sample_size=10,  # Minimum observations per source; fewer gives weight 0.
    discount_rate=1.0,  # exp discount for error-weighted
    estimation_start=None,
    estimation_end=None,  # regression sample bounds
    estimator="constrained_ls",  # 'constrained_ls'|'clipped_ols'
    dummy_periods=None,
)
```

`ComboSpec.sources`: strings (resolved vs other specs), embedded specs (auto-registered), nested `ComboSpec` (combos of combos). `MultiMidasSpec` ref by name.

`flatten()`, `collect_indicators()` walk tree in dep order; `MidasCombo` calls internally.

---

## Decomposition — forecast breakdown

Every model exposes `forecast_decomp()`: additive components of the OOS point forecast that sum back to `forecast()`. Long-fmt DF: `horizon`, `date`, `component`, `contribution`, `weight`.

```text
# Single indicator (MIDAS / OLS)
dec = model.forecast_decomp(regressors_forecast, regressor_name="PMI")
# components: intercept, <regressor block>, dummies, AR lags
# MIDAS lag block has weight=NaN (not a single linear multiplier)

# Multi-regressor
dec = mm.forecast_decomp(
    regressors
)  # one component per variable + intercept/dummies/AR

# Combo pipeline: flattens the tree to leaf models, applies effective weights
dec = combo.forecast_decomp(spec_name="final_combo")  # "{model}::{component}"
dec = combo.forecast_decomp(
    spec_name="final_combo", aggregate=True
)  # one row per model
dec = combo.forecast_decomp(
    spec_name="final_combo", regressors=new_vintage
)  # counterfactual
```

`spec_name=None` → root `ComboSpec`. `regressors=None` → frames stored at fit time; pass a different vintage for revision attribution (news decomposition). Useful: which indicator drove the forecast change, stress-testing (X moves ±1σ).

---

## Long-format output

Fits & forecasts are long DataFrames, populated as a side-effect of `fit()` / `forecast()` (there are no separate `*_long()` methods).

```text
# MIDAS / OLS / MultiMIDAS
model.fits_df_  # date, horizon, value        (set by fit)
model.forecasts_df_  # horizon, date, forecast     (set by forecast)

# MidasCombo
combo.fits_df_  # spec, date, horizon, value    (indicators + combos)
combo.weights_df_  # spec, source, horizon, value  (combination weights)
combo.forecasts_df_  # date, horizon, value, spec    (set by forecast)
combo.fits_and_forecasts_df_  # concat of fits_df_ + forecasts_df_
```

Long format → easier export/comparison w/ external tools (EViews, R, etc.).

---

## Clipped OLS — simple constrained regression

Alternative to Levenberg-Marquardt. Uses plain OLS, clips weights to [0,1], and normalises them.

```text
ComboSpec(
    name="regression_combo",
    sources=["PMI", "UNEMP"],
    method="regression",
    estimator="clipped_ols",
)
```

**`clipped_ols`**: OLS, clipping to [0,1], and softmax normalisation. It is faster because it avoids iterative optimisation, but it is less stable than `constrained_ls` for ill-conditioned designs.

**`constrained_ls`** (default): Levenberg-Marquardt w/ softmax reparameterization. Slower, more stable.

---

## Enhanced dummy periods — exclude anomalies from weights

Mask outlier quarters (COVID, crises) from error-weighted & regression weight estimation. Dummies still fit (gamma coeffs added), but don't distort combination weights.

```text
ComboSpec(
    name="combo",
    sources=["PMI", "IP"],
    method="mse",
    window=8,
    dummy_periods=["2020-03", "2020-06", "2020-09", "2020-12"],  # COVID
)

# Or per-indicator
MidasSpec(
    "PMI",
    n_lags=3,
    dummy_periods=[pd.Timestamp("2020-03-31"), pd.Timestamp("2020-06-30")],
)
```

- **Error-weighted methods** (`mse`, `rmse`, `mae`): residuals masked = NaN at dummy dates. Discount window skips them.
- **Regression** (`method="regression"`): rows at dummy dates excluded from weight estimation. Forecasts still computed; just don't train on them.
- **Validation**: Quarter-end months only (03, 06, 09, 12). Raises `ValueError` if invalid.

---

## `MidasCombo` — SC-MIDAS pipeline

Assemble & run full combo tree. Flattens specs → fits indicators (stage 1) → combo nodes in dep order (stage 2).

```text
model = MidasCombo(
    combo_specs=final_combo,  # root ComboSpec (tree flattened)
    horizons=3,  # fits MIDAS/OLS per h in range(horizons)
)

model.fit(target=target, regressors=regressors)
oos = model.forecast()  # long: date, horizon, value, spec
fc_decomp = model.forecast_decomp()  # long component breakdown (root combo)
print(model.summary(horizon=0))
model.plot_fit()
model.plot_weights()
model.plot_forecast()
```

Indicator models are derived **only** from the combo tree — the `midas_specs` / `ols_specs` / `multi_midas_specs` ctor args were removed in 0.1.0. Embed `MidasSpec` / `OLSSpec` / `MultiMidasSpec` instances as `ComboSpec.sources`.

**Stage 1:** Fit every `MidasSpec`/`OLSSpec` across all horizons. **Stage 2:** Fit each `ComboSpec` node (leaves first, all horizons).
- `'average'` → equal weights
- `'mse'`, `'rmse'`, `'mae'` → inverse-error weights w/ optional window + discount
- `'regression'` → constrained LS (weights ≥0, sum to 1) or clipped OLS

**`forecast()`:** No arguments. Step `s` (0-based) forecasts `y[T+s+1]` with the horizon-`s` model — the only cell that needs no future regressors. Returns a **long** DF (`date`, `horizon`, `value`, `spec`) and sets `forecasts_df_` + `fits_and_forecasts_df_`.

Key attrs after fit: `target_`, `regressors_`, `midas_models_`, `ols_models_`, `multi_midas_models_`, `midas_instances_`, `ols_instances_`, `multi_midas_instances_`, `fitted_`, `combo_weights_`, `fits_df_`, `weights_df_`.

Combo weights: `dict[combo_name, dict[h, dict[source_name, ndarray]]]`. Time-varying.

---

## Plot

`MIDAS` and `MidasCombo` expose plotting methods directly — all return `(fig, ax)`:

```text
combo.plot_fit(
    combo_names=None, indicator_names=None, horizon=None, ax=None, ylim=None, xlim=None
)  # None,None → root combo
combo.plot_weights(combo_name=None, horizon=None, ax=None)
combo.plot_forecast(
    combo_names=None, indicator_names=None, horizon=None, ax=None, ylim=None, xlim=None
)  # requires forecast() first
```

`OLS` / `MultiMIDAS`: no built-in plots — plot from `fits_df_` / `forecasts_df_`.

---

## Utils

```text
# Single-indicator DGP
target, regressors = sample_data(
    n_obs=100,
    n_lags=6,
    alpha=2.0,
    beta_=1.0,
    noise=0.5,
    seed=42,
    horizon=0,
    method="exp_almon",
    n_ar_lags=0,
)

# Full combo DGP (long-fmt + ground-truth dict)
target, regressors, info = sample_combo_data(
    n_quarters=60,
    n_lags=6,
    monthly_vars=["PMI", "IP", "GDPM"],
    quarterly_vars=["UNEMP"],
    seed=42,
    outlier_date="2020-06-30",
    outlier_size=-25.0,
)
```

`sample_combo_data` → long-fmt frames + `info` dict (outlier_date, alpha, betas, gammas, weights, noise, monthly_vars, quarterly_vars).

Lag helpers honor **ragged edge**: quarter's anchor month = latest available month-within-quarter. Alignment consistent w/ realtime vintages. Missing lags = NaN.

---

## Patterns

### MIDAS + AR + dummy

```text
import pandas as pd

target, regressors = sample_data(n_obs=500, n_lags=6, seed=0, horizon=4, n_ar_lags=1)
outlier_date = pd.Timestamp(target["date"].iloc[300])
target.loc[target["date"] == outlier_date, "value"] += 10.0

model = MIDAS(
    method="almon",
    n_lags=6,
    estimator="ols",
    horizons=[0, 4],
    n_ar_lags=1,
    dummy_periods=[outlier_date],
)
model.fit(target, regressors)
model.plot_fit()
model.plot_weights()
```

### Two-level SC-MIDAS combo

```text
soft_combo = ComboSpec(
    name="soft_combo",
    sources=[MidasSpec("PMI", "almon", n_lags=5), MidasSpec("IP", "almon", n_lags=5)],
    method="mse",
    window=8,
    discount_rate=0.95,
)
final_combo = ComboSpec(
    name="final_combo",
    sources=[soft_combo, OLSSpec("UNEMP", n_lags=1)],
    method="regression",
)
model = MidasCombo(combo_specs=final_combo, horizons=1).fit(target, regressors)
soft_weights = model.combo_weights_["soft_combo"][0]
final_in_sample = model.fitted_["final_combo"][0]
decomp = model.forecast_decomp(spec_name="final_combo")  # component breakdown
```

### MultiMIDAS standalone & combo

```text
variables = [
    VariableSpec("PMI", method="exp_almon", n_lags=6),
    VariableSpec("IP", method="almon", n_lags=6),
    VariableSpec("UNEMP", frequency="QE", n_lags=1),
]

# Standalone
mm = MultiMIDAS(variables=variables, horizons=[0]).fit(target, regressors)
ip_weights = mm.fits_[0].variable_fits["IP"].weights

# Embedded in combo
multi_block = MultiMidasSpec(name="multi_block", variables=variables)
combo = ComboSpec(name="combo", sources=[multi_block], method="average")
pipe = MidasCombo(combo_specs=combo, horizons=4).fit(target, regressors)
fitted_mm = pipe.multi_midas_models_["multi_block"][0]
```

### Realtime

See `examples/realtime_midas.py` & `examples/realtime_midas_combo.py`. Use w/ `forecast-realtime` vintage mgmt. Pass each vintage's (target, regressors) slice to fit/forecast independently.

---

## Gotchas

- **Input shapes:** `MIDAS`/`OLS` → 2 cols [`date`, `value`]. `MidasCombo` → long-fmt [`date`, `variable`, `frequency`, `value`]. Variable must match spec exactly.
- **Missing values** — targets must contain values; missing regressor months are allowed, and rows with a missing lag are dropped.
- **Horizons:** List on `MIDAS`/`OLS` (`horizons=[0, 4]`); int on `MidasCombo` (uses `range(horizons)`).
- **Estimator routing:** `estimator='ols'` only almon/unrestricted. Beta/exp_almon → NLS forced. MultiMIDAS mixed methods → NLS whole model, linear-in-pars still linear.
- **Quarterly regressors:** Always linear. Use `VariableSpec(frequency="QE", n_lags=M)` in MultiMIDAS; method/n_pars_weights/estimator ignored.
- **Dummies:** Applied at target freq (gamma on D[t+h]). Excluded from weight est if `dummy_periods` set. No internal transform; apply log-diff/deflate before fit.
- **AR augment** drops first n_ar_lags rows. **Forecast x-anchor:** `T_X` = latest regressor date (`MIDAS`/`OLS` have no `info_date` arg; `MultiMIDAS` still accepts one). Ragged edge honored.
- **`MidasCombo.forecast()` returns long format** (`date`, `horizon`, `value`, `spec`) — the old wide `{var}_{N}qa` columns are gone. Step `s` → `y[T+s+1]` from the horizon-`s` model. Variable name conflict between MIDAS/OLS/MultiMIDAS specs → `ValueError`.
- **No `decompose()` / `fit_long()` / `forecast_long()` methods** — use `forecast_decomp()` and the `*_df_` attributes.

---

## API

**Classes (estimators & results)**
- `MIDAS(method, n_lags, n_pars_weights, estimator, horizons, start_lag, n_ar_lags, dummy_periods)`
- `FittedMidas` — alpha, beta, theta, weights, fitted_values, residuals, dates
- `MultiMIDAS(variables, method, n_lags, n_pars_weights, estimator, horizons, start_lag, n_ar_lags, dummy_periods)`
- `FittedMultiMidas` — alpha, variable_fits, gamma, phi, fitted_values, residuals, dates
- `VariableFit` — beta, theta, weights
- `OLS(n_lags, start_lag, horizons, n_ar_lags, dummy_periods)`
- `FittedOLS` — intercept, coef, gamma, phi, fitted_values, residuals, dates
- `MidasCombo(combo_specs, horizons)`

**Specs**
- `MidasSpec(variable, method, n_lags, n_pars_weights, estimator, start_lag, n_ar_lags, dummy_periods, minimum_sample)`
- `OLSSpec(variable, n_lags, start_lag, n_ar_lags, dummy_periods, minimum_sample)`
- `VariableSpec(variable, method, n_lags, n_pars_weights, estimator, start_lag, frequency)`
- `MultiMidasSpec(name, variables, method, n_lags, n_pars_weights, estimator, start_lag, n_ar_lags, dummy_periods, minimum_sample)`
- `ComboSpec(name, sources, method, window, minimum_sample, discount_rate, estimation_start, estimation_end, estimator, allow_missing_indicators, dummy_periods)`

**Utils**
- `build_lag_matrix(target_dates, regressors, n_lags, start_lag)`
- `build_quarterly_lag_matrix(target_dates, regressors, n_lags, start_lag)`
- `sample_data(n_obs, n_lags, alpha, beta_, noise, seed, horizon, method, n_ar_lags)`
- `sample_combo_data(n_quarters, n_lags, monthly_vars, quarterly_vars, seed, outlier_date, outlier_size)`

**Plots (mixed into MIDAS)**
- `plot_fit(horizon=None, ax=None)` — fitted vs actual
- `plot_weights(horizon=None, ax=None)` — lag weights
- `plot_forecast(horizon=None, start_date=None, ax=None)` — forecast path

**MIDAS / OLS / MultiMIDAS methods**
- `fit(target, regressors)` → sets `fits_`, `fits_df_`
- `forecast(regressors_forecast)` (MultiMIDAS: `forecast(regressors, info_date=None)`) → long DF
- `forecast_decomp(...)` → long component breakdown
- `summary(horizon=...)` — MIDAS & MultiMIDAS only

**MidasCombo methods**
- `fit(target, regressors)` — run stages 1–2
- `forecast()` → long DF (`date`, `horizon`, `value`, `spec`)
- `forecast_decomp(spec_name=None, regressors=None, aggregate=False)` → long decomposition
- `summary(horizon=0)` — text report
- `plot_fit(...)`, `plot_weights(...)`, `plot_forecast(...)` (from `ComboPlots`)

**Plotting**
- `MIDAS.plot_fit()`, `MIDAS.plot_weights()`, and `MIDAS.plot_forecast()`
- `MidasCombo.plot_fit()`, `MidasCombo.plot_weights()`, and `MidasCombo.plot_forecast()`

---

## Refs

- Ghysels, Santa-Clara, Valkanov (2004). MIDAS touch.
- Ghysels, Sinko, Valkanov (2007). Further results. Econometric Reviews 26(1).
- Andreou, Ghysels, Kourtellos (2010). Mixed sampling freqs. J. Econometrics 158(2).
- Bates, Granger (1969). Combination of forecasts. Operational Research 20(4).
- Stock, Watson (2004). Output growth combos. J. Forecasting 23(6).
