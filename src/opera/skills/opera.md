---
name: opera
description: Modular forecasting ecosystem (Bank of England). OPERA = Prediction + Evaluation + Real-time Analysis. Modules compose for data → models → evaluation → combination pipelines. Full architecture + links to subskills.
module-package: opera-eco
# x-release-please-start-version
module-version: "0.4.6"
# x-release-please-end
---

<!-- x-release-please-start-version -->
# Version: 0.4.6
<!-- x-release-please-end -->

# OPERA — Prediction, Evaluation & Real-time Analysis

## What is OPERA?

Modular forecasting infra (BoE). Solves: duplicated logic, non-reproducible past forecasts, eval inconsistency, high onboarding friction.

Each concern — data, models, orchestration, eval, combination — = separate Python package. Compose via standard interfaces.

**Design:**
- 1 package = 1 job; no duplication
- Vintaged data → reproducible, no look-ahead bias
- Python/R/MATLAB/Julia models, same infra
- Point/density/nowcast/conditional/scenario forecasts all work
- MIT licensed (mostly public)

---

## Architecture

```
Data                           Orchestration               Output
────────────────────────────   ─────────────────────       ───────

┌──────────────────┐
│ Vintaged Data    │─outturns──┐
│ forecast_data    │          ▼
└──────────────────┘     ┌─────────────────┐   ┌──────────────┐
                         │ Forecast        │◄──│ Forecast     │
                         │ Evaluation      │   │ Combination  │
                         │ (validate both) │───▶│ (combine)    │
                         └────────┬────────┘   └──────────────┘
                           validated
                                 │
                                 ▼
                         ┌────────────────────┐
┌──────────────────┐    │ Real-time          │
│ bvar, nowcast-midas │──▶│ Forecasting        │──forecasts──▶ eval
│ custom, R/MATLAB │    │ (fit→forecast loop)│ + decomp
└──────────────────┘    │ + backtesting      │
                         └────────────────────┘
```

### Data flows

`forecast_data` → vintage outturns + forecasts. Data → `forecast_evaluation` (validates) → `forecast_realtime` (fit/forecast) + `forecast_combo` (combine) + `news_decomp` (decompose). Real-time forecasts loop back → eval.

---

## Modules

| Name | Package | PyPI | Job |
|------|---------|------|-----|
| BVAR | bvar | bvar | Bayesian VAR: estimation + conditional/unconditional forecasts |
| MIDAS | nowcast-midas | nowcast-midas | Mixed-freq nowcast (monthly → quarterly); multi-regressor + hierarchical combos |
| Eval | forecast_evaluation | forecast_evaluation | Validate data + test accuracy + visualize |
| Real-time | forecast_realtime | forecast_realtime | Fit/forecast loops + backtest + stress test |
| Combo | forecast_combo | — | Combine forecasts (weights, OLS, hierarchical) |
| Decomp | news_decomp | — | Nowcast decomp: level + revision splits |

---

## Each Module

### 1. BVAR (v0.3.1)

Bayesian VAR w/ Minnesota priors. Unconditional + conditional (hard/soft/skewed constraints) + GIRF.

**Can:**
- Two priors: `NaturalConjugate` (direct sample, closed-form likelihood) + `IndependentNIW` (Gibbs)
- Hyperparams: `"ml"` or `"cross_validation"` — both need a closed-form posterior mode → `NaturalConjugate` only; `IndependentNIW` → `"none"` (set by hand)
- Hard (Waggoner & Zha), soft (Antolín-Díaz), skewed constraints
- GIRFs
- COVID dummies
- Quantiles (default [0.16, 0.5, 0.84])
- `random_state` on `BVAR(...)` or per call (`optimise_hyperparameters`/`sample`/`forecast`/`recursive_forecast`) → private `bvar.rng`; global NumPy state untouched
- `model` is deep-copied on construction (safe to share a prior object)

**API** → **bvar** skill

---

### 2. SC-MIDAS (nowcast-midas v0.0.1)

MIDAS + SC-MIDAS nowcast (monthly → quarterly). Estimators: `MIDAS`, `MultiMIDAS`, `OLS`, `MidasCombo`. Specs: `MidasSpec`/`OLSSpec`/`VariableSpec`/`MultiMidasSpec`/`ComboSpec`. Nest specs → hierarchical combos.

**Can:**
- Single mixed-freq reg (`MIDAS`): exp_almon/beta (NLS), almon/unrestricted (OLS)
- Multi-regressor joint est (`MultiMIDAS`): monthly (MIDAS lags) + quarterly (linear) in one model; `VariableSpec` per var
- `forecast_decomp()` on every model: additive components of the OOS forecast (sums back to `forecast()`); combo version flattens the tree, `aggregate=True` → one row per model, `regressors=<new vintage>` → counterfactual/news attribution
- Long-format results as side-effects of fit/forecast: `fits_df_`, `forecasts_df_`; combo also `weights_df_`, `fits_and_forecasts_df_` (no `decompose()`/`fit_long()` methods)
- `MidasCombo.forecast()` → long DF (`date`, `horizon`, `value`, `spec`)
- Combo weight estimators: `constrained_ls` (default, LM + softmax) or `clipped_ols` (clip to [0,1] + normalise)
- `dummy_periods` (quarter-end months) fit gamma coeffs but are masked out of weight estimation
- `ComboSpec.sources`: strings, specs, nested combos
- `MultiMidasSpec` for pipeline refs

**API** → **nowcast-midas** skill

---

### 3. Forecast Evaluation (v0.1.13)

**Central hub.** Validates outturns **and** forecast paths. Prerequisite for estimation.

**Can:**
- `ForecastData`: forecasts + outturns, filter, merge, `add_benchmarks()` (AR/RW; `max_lag=1` skips BIC)
- `DensityForecastData`: quantile forecasts, sample draws, density plots
- `NowcastData`: intra-period (weekly) vintages, revision index k (post k≥0; pre k<0), `days_to_publication`, `compute_intra_period_accuracy`/`bias`
- Tests (→ `TestResult`): accuracy, Diebold-Mariano, bias, weak/strong efficiency, Blanchard-Leigh, revision predictability, revisions-errors + forecast-errors correlation
- Rolling + fluctuation tests w/ Giacomini-Rossi critical values
- Plots: vintage, hedgehog, errors by horizon, radar, density, outturn revisions, correlation heatmap
- Interactive dashboard (`run_dashboard()`)
- Built-in BoE FER data (GDP, CPI, unemployment, …)

**API** → **forecast-evaluation** skill

---

### 4. Real-time Forecasting (v0.5.3)

Operational orchestration layer. Wraps models w/ standard methods. 4 use cases: live forecasting, backtesting, simulation, stress-testing.

**Can:**
- `ForecastModel`: abstract; `_fit()` + `_forecast()` + optional `_forecast_decomp(steps, X, y)` (news/reestimation/interaction)
- `RealTimeModel`: loop vintages, deep-copy models (no state leak), store in `ForecastData`; `decomp=True` → `rt_model.decompositions`; `parallel=True` (batch vintages)
- Built-in: `ForecastRidge`, `ForecastLasso`, `ForecastElasticNet`, `ForecastOLS`, `RandomForest`, `XGBoost`, `CatBoost`, `NeuralNet`, `Ensemble`, `ForecastBVAR`, `ForecastRlm` (R `lm()`), `ForecastMIDAS`, `ForecastMultiMIDAS`, `ForecastMIDASCombo`
- External: `RModel`, `MATLABModel`, `JuliaModel` (Parquet + subprocess; fresh temp cache dir per instance *and* per `_fit()` → parallel-safe; debug REPL during dev)
- Transform: `"levels"`, `"pop"`, `"yoy"`, `"logs"`, `"log diff"`, `"diff"` + auto level recon; `drop_transformation_nans=True` drops the leading NaN row for diff/log-diff vars
- Lags: `y_lags` (int), `X_lags` (int or dict per var), `first_forecast_horizon`. Lag cols named `<y_name>_lag1…`, `<col>_lag1…`; recursive AR roll-forward gives each lag col its own period's value
- `_forecast` receives the design over history **plus** horizon when lags are set — slice the last `steps` rows yourself
- Decomp implemented by all `LinearRegression` models (OLS/Ridge/Lasso/ElasticNet) + MIDAS/MultiMIDAS/MIDASCombo
- Condition: `y_steps_ahead`/`y_sources` (target, BVAR-style), `X_steps_ahead`/`X_sources` (regressors)

**API** → **forecast-realtime** skill

---

### 5. Forecast Combination (v0.1.1)

Takes individual forecasts → combined. Combined loop back → eval (so combo schemes evaluated alongside single models).

**Can:**
- Methods: `average`, `rmse`, `mse`, `mae`, `huber`, `least_squares` (OLS), `constrained_least_squares` (JAX; `w_i ≥ 0`, Σ`w_i = 1`)
- `ForecastCombo` wraps `ForecastData` + `.fit()` (chainable); combined forecasts stored as new source
- `ComboSpec` dataclass: hierarchical multi-stage (nest in `sources` → `.flatten_and_validate()` resolves deps → root passed to `.fit()`)
- `sources` = list[str], `ComboSpec`, or list[str|ComboSpec] (mixed)
- `allow_partial_sources=True` (dflt) fits on the available subset; `False` raises on a missing source
- `fit_hierarchical()` deprecated (use `ComboSpec` via `.fit()`)
- Rolling window + exponential discount (`discount_param ∈ (0,1]`)
- Outturn maturity `k` (target `t` → vintage `t + (k+1)`; `k=0` = first post-target release), period filters
- Plots: heatmap, line, bar; dashboards: `run_weight_dashboard()` + `run_forecast_dashboard()`

**API** → **forecast-combo** skill

---

### 6. Nowcast Decomposition (v0.0.7)

NY Fed–style. Split nowcast updates → level + revision. "News" (new data) vs "reestimation" (coeff change) vs "interaction" (both).

**Can (mixin arch: `NewsAnalysis` + `NewsPlots` → `NewsData`):**
- `NewsData`: validate + store decomps (long format); `data.df`, `data.summary()`, `data.report()`
- Accuracy: `rmse`, `mae`, `accuracy_over_time` (vs realised)
- Indicator usefulness: `marginal_contributions`, `signal_magnitude`, `hit_rate`, `error_improvement`
- Timing: `timing_decomposition` (intrinsic vs timing premium); info density: `information_density`
- Real-time: `revision_predictability`, `news_vs_noise_r2`, `realtime_error_improvement`, `vintage_revision_contribution`
- NY Fed: `nowcast_evolution`, `revision_evolution`, `revision_impacts`, `cumulative_revision_impacts`, `release_table_data`, `indicator_table`, `indicator_table_over_time`, `raw_revision_contributions` (level-diff; sums exactly to the nowcast change)
- Plots incl. `plot_raw_revision_contributions`, `plot_nowcast_contributions`, `plot_revision_by_source`

**API** → **forecast-decomp** skill

---

## Data Standard

All modules use this schema:

| Col | Type | Desc |
|-----|------|------|
| `date` | Timestamp | Period end |
| `vintage_date` | Timestamp | Publication date |
| `variable` | str | `"gdpkp"`, `"cpisa"`, etc |
| `frequency` | str | `"Q"` or `"M"` |
| `forecast_horizon` | int | Forecast information horizon: 0=first usable target period, ≥1=later periods |
| `target_minus_vintage` | int | Calendar distance from target period to vintage; may be negative |
| `value` | float | Value |
| `source` | str | Model/forecaster ID (forecasts only) |
| `metric` | str | `"levels"`, `"pop"`, `"yoy"` |

**Horizon:** `forecast_horizon` is an information horizon on forecasts; `target_minus_vintage` is the separate calendar-distance field. Outturns do not use `forecast_horizon`. **Frequency:** One `ForecastData` per freq. Use `.merge()` to combine (must match `outturn_vintages` setting). **Key rules:** Outturns → forecasts (order). Models deep-copied per vintage (no leak). Combined forecasts → `ForecastData` (enabled eval). `.filter()` mutates (use `.copy()` to preserve).

---

## Integration Patterns

### Example: Data → Model → Eval

```python
# skill-test: skip (requires full FER data and expensive realtime estimation)
import forecast_evaluation as fe
import forecast_realtime as rt

# Load, validate
data = fe.ForecastData(load_fer=True)

# Fit + forecast
model = rt.models.ForecastRidge(cv=5)
rt_model = rt.RealTimeModel(data=data, models=model)
rt_model.forecast(
    y_variables=["gdpkp"],
    data_transformation={"gdpkp": "pop"},
    frequency="Q",
    steps=12,
    label="Ridge",
    y_lags=4,
)

# Eval
acc = fe.compute_accuracy_statistics(data, k=12)
dm = fe.diebold_mariano_table(data, benchmark_model="mpr", k=12)
```

### Example: Model → Eval → Combo → Re-eval

```python
# skill-test: skip (requires full FER data and multiple realtime estimations)
import forecast_evaluation as fe
import forecast_realtime as rt
import forecast_combo as fc

# Load
data = fe.ForecastData(load_fer=True)

# Run models
for Model, label in [
    (rt.models.ForecastRidge, "Ridge"),
    (rt.models.ForecastLasso, "Lasso"),
]:
    m = Model(cv=5)
    rtm = rt.RealTimeModel(data=data, models=m)
    rtm.forecast(
        y_variables=["gdpkp", "cpisa"],
        data_transformation={"gdpkp": "pop", "cpisa": "pop"},
        frequency="Q",
        steps=12,
        label=label,
        y_lags=4,
    )

# Combine
combo = fc.ForecastCombo(forecast_data=data)
combo.fit(
    sources=["Ridge", "Lasso", "mpr"],
    variables=["gdpkp", "cpisa"],
    method=["average", "rmse", "constrained_least_squares"],
    training_start="2016-01-01",
)

# Eval all (individual + combined)
acc = fe.compute_accuracy_statistics(data, k=12)
dm = fe.diebold_mariano_table(data, benchmark_model="mpr", k=12)
```

### Example: Conditional BVAR

```python
# skill-test: skip (requires full FER data and expensive BVAR estimation)
import forecast_evaluation as fe
import forecast_realtime as rt

data = fe.ForecastData(load_fer=True)

bvar = rt.models.ForecastBVAR(
    stationary=True,
    n_lags=5,
    mode_only=True,
    nb_restart=5,
    covid=True,
)
rtm = rt.RealTimeModel(data=data, models=bvar)
rtm.forecast(
    y_variables=["cpisa", "unemp", "gdpkp"],
    data_transformation={"cpisa": "pop", "unemp": "levels", "gdpkp": "pop"},
    y_steps_ahead={"cpisa": 1, "unemp": 0},
    y_sources={"cpisa": "mpr", "unemp": "mpr"},
    frequency="Q",
    steps=13,
    label="Conditional BVAR",
)
```

### Example: Add Custom Model

Implement `ForecastModel` interface:

```text
from forecast_realtime import ForecastModel
import numpy as np, pandas as pd


class MyModel(ForecastModel):
    def _fit(self, y: pd.DataFrame, X: pd.DataFrame = None, **kwargs):
        # fit logic
        return self

    def _forecast(self, steps: int, X=None, y=None, **kwargs) -> pd.DataFrame:
        # forecast logic → (steps, n_vars) with DatetimeIndex "date"
        return forecasts_df
```

Plug in:

```text
model = MyModel()
rtm = rt.RealTimeModel(data=data, models=model)
rtm.forecast(
    y_variables=["cpisa"],
    data_transformation={"cpisa": "levels"},
    frequency="Q",
    steps=4,
)
```

---

## Module Links

| Skill | Module | Docs |
|-------|--------|------|
| **forecast-evaluation** | `forecast_evaluation` | Data validation, accuracy, tests, dashboards, `NowcastData` |
| **forecast-realtime** | `forecast_realtime` | Fit/forecast loops, backtest, model wrapping, external models |
| **forecast-combo** | `forecast_combo` | Combination, hierarchical, rolling/discount weights, dashboards |
| **bvar** | `bvar` | BVAR estimation, conditional forecasts, GIRFs, COVID dummies |
| **nowcast-midas** | `nowcast-midas` | MIDAS/SC-MIDAS, mixed-freq, hierarchical combos |
| **forecast-decomp** | `news_decomp` | Nowcast decomp: level + revision splits, news/reest/interact |

---

<!-- x-release-please-start-version -->
<!-- BEGIN GENERATED API -->
## API

```json
{
  "exports": {
    "opera": [
      "__version__"
    ]
  },
  "package": "opera-eco",
  "signatures": {},
  "version": "0.4.6"
}
```
<!-- END GENERATED API -->
<!-- x-release-please-end -->

## Status

| Module | Partial | Full | Reviewed | Shipped |
|--------|---------|------|----------|---------|
| forecast_evaluation | ✓ | ✓ | ✓ | ✓ |
| bvar | ✓ | ✓ | — | — |
| forecast_combo | ✓ | ✓ | — | — |
| forecast_realtime | ✓ | — | — | — |
| nowcast-midas | ✓ | — | — | — |
| news_decomp | ✓ | — | — | — |
