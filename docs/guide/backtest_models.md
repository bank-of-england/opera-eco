# Backtest Models

Backtesting runs a model across historical data vintages. At each vintage, `RealTimeModel` fits a fresh model, exposes only the information then available, and stores the forecasts in a shared `ForecastData` object.

## 1. Load data

Use `ForecastData` for one-frequency data or `NowcastData` when multiple vintages occur within a target period.

```python
import forecast_evaluation as fe
import forecast_realtime as rt

data = fe.ForecastData(load_fer=True)
```

## 2. Configure a model

```python
model = rt.models.ForecastOLS(
    label="ols",
    formula="cpisa ~ gdpkp + unemp",
)
```

The formula selects the target and regressors. Declare transformations in the vintage loop instead of applying them manually in the model.

## 3. Run the vintage loop

```python
rt_model = rt.RealTimeModel(data=data, models=model)

rt_model.forecast(
    y_variables=["cpisa"],
    X_variables=["gdpkp", "unemp"],
    data_transformation={
        "cpisa": "pop",
        "gdpkp": "pop",
        "unemp": "levels",
    },
    step_frequency="Q",
    steps=8,
    first_vintage="2015-01-01",
    last_vintage="2020-12-31",
    label="ols",
)
```

Read forecasts from `rt_model.data`. When the model supports decomposition, `forecast(..., decomp=True)` also populates `rt_model.decompositions`.

## 4. Inspect the result

```python
rt_model.data.summary()
rt_model.data.run_dashboard()
```

For autoregressive models, pass `y_lags=4` or a model-specific lag argument. The real-time loop manages the expanding information set and recursive forecast horizons.