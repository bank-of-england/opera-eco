# `forecast_combo`

## Purpose

`forecast_combo` combines point forecasts from multiple sources. It copies a `ForecastData` instance from `forecast_evaluation`, estimates weights over real-time vintages, stores combined forecasts in the copy, and supports optional plots and Shiny dashboards.

## Features

- Equal-weight, error-based, and regression-based forecast combinations.
- Rolling windows, exponential discounting, and period filters.
- Hierarchical combinations built from nested `ComboSpec` objects.
- Partial-source handling when a model is unavailable for a target or horizon.
- Weight visualisations and dashboards for combined forecasts.
- Outturn-maturity controls for vintage-aware estimation.

`ForecastCombo` copies the supplied `ForecastData` before fitting, so combined forecasts do not alter the caller's data. It stores the results in `combo.forecast_data` and makes them available to the evaluation workflow.

## Quick start

```python
import forecast_evaluation as fe
import forecast_combo as fc

data = fe.ForecastData(load_fer=True)
combo = fc.ForecastCombo(forecast_data=data)

combo.fit(
    sources=["mpr", "compass conditional", "bvar unconditional"],
    variables=["gdpkp", "cpisa"],
    method=["average", "rmse", "constrained_least_squares"],
    training_start="2016-01-01",
    metric="pop",
)

# Visualise weights and launch the joint forecast dashboard
fc.heatmap_by_vintage(combo.weights, method="rmse", variable="gdpkp")
combo.run_forecast_dashboard()
```

## Repository

Read the implementation and full API reference in the [forecast-combo repository](https://github.com/bank-of-england/forecast-combo).