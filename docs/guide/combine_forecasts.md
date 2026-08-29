# Combine Forecasts

`forecast_combo` combines forecasts stored in a `ForecastData` object. Add the individual model forecasts before fitting a combination.

## 1. Produce individual forecasts

Any compatible model workflow can supply the individual sources. For example, an OLS and MIDAS model can share a `NowcastData` object:

```python
import forecast_combo as fc

forecast_data = rt_model.data
combo = fc.ForecastCombo(forecast_data=forecast_data)
```

## 2. Fit a combination

```python
combo.fit(
    sources=["ols", "midas"],
    variables=["quarterly_a"],
    method="rmse",
    metric="levels",
    label="rmse combo",
)
```

Available methods include `average`, `rmse`, `mse`, `mae`, `huber`, `least_squares`, and `constrained_least_squares`. `average` assigns equal weights; error-based methods estimate weights from historical forecast errors.

Use `training_start`, `training_end`, `window_size`, `discount_param`, `period_filter`, and `k` to control the fitting period and outturn maturity.

## 3. Inspect weights and forecasts

```python
weights = combo.weights
combined_data = combo.forecast_data

fc.heatmap_by_vintage(weights, method="rmse", variable="quarterly_a")
combo.run_forecast_dashboard()
```

`combo.forecast_data` includes the combined forecast. Evaluate it alongside the component forecasts without rebuilding the data object.

## Hierarchical combinations

Use `ComboSpec` when one combination supplies another combination's source:

```python
from forecast_combo import ComboSpec

first_stage = ComboSpec(
    name="model_average",
    sources=["ols", "midas"],
    method="average",
)

combo.fit(
    sources=ComboSpec(
        name="top_level",
        sources=[first_stage, "benchmark"],
        method="rmse",
    ),
    variables=["quarterly_a"],
)
```