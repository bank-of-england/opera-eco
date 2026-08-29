---
title: Illustration Marimo
marimo-version: 0.24.0
width: medium
---

````python {.marimo}
import marimo as mo

mo.md(
    """
    # OPERA mixed-frequency forecasting

    This notebook runs OLS and MIDAS forecasts, decomposes nowcast news,
    combines the forecasts, and compares accuracy across horizons.

    Install the ecosystem and notebook dependencies first:

    ```bash
    pip install "opera-eco[modules,notebooks]"
    ```
    """
)
````

```python {.marimo}
import forecast_combo as fc
import forecast_evaluation as fe
import forecast_realtime as rt
import news_decomp as nd

from opera.sample_realtime_data import create_realtime_mixed_freq_data

target = "quarterly_a"
ols_regressors = [
    "quarterly_b",
    "quarterly_c",
    "quarterly_d",
    "quarterly_e",
]
midas_regressor = "monthly_a"
all_regressors = ols_regressors + [midas_regressor]

first_vintage = "2026-01-31"
last_vintage = "2026-12-31"
steps = 2
```

```python {.marimo}
mixed_freq_data = create_realtime_mixed_freq_data()
data = fe.NowcastData(outturns_data=mixed_freq_data)
```

```python {.marimo}
ols = rt.models.ForecastOLS(
    label="ols",
    formula=f"{target} ~ " + " + ".join(ols_regressors),
)

midas = rt.models.ForecastMIDAS(
    label="midas",
    method="almon",
    n_lags=5,
    estimator="ols",
    horizons=list(range(steps)),
    n_ar_lags=1,
    formula=f"{target} ~ {midas_regressor}",
)
```

```python {.marimo}
realtime_model = rt.RealTimeModel(data=data, models=[ols, midas])

realtime_model.forecast(
    X_variables=all_regressors,
    data_transformation=dict.fromkeys([target, *all_regressors], "levels"),
    X_imputation="last",
    y_variables=[target],
    step_frequency="Q",
    steps=steps,
    first_vintage=first_vintage,
    last_vintage=last_vintage,
    decomp=True,
)

realtime_model.data.summary()
```

```python {.marimo}
news = nd.NewsData(realtime_model.decompositions)
```

```python {.marimo}
combo = fc.ForecastCombo(forecast_data=realtime_model.data)

combo.fit(
    sources=["ols", "midas"],
    variables=[target],
    method="rmse",
    metric="levels",
    label="rmse combo",
)
```

```python {.marimo}
stats = fe.compute_accuracy_statistics(
    combo.forecast_data,
    variable=target,
).to_df()
stats = stats.loc[stats["metric"] == "levels"]
keep = [
    column
    for column in ("source", "forecast_horizon", "n_obs", "mae", "rmse")
    if column in stats
]
stats = stats[keep].sort_values(keep[:2]).reset_index(drop=True)

print("\nAccuracy:\n", stats)
```