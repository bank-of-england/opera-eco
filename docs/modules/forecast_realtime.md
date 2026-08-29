# `forecast_realtime`

## Purpose

`forecast_realtime` fits forecast models on vintage data and stores their forecasts through `forecast_evaluation.ForecastData`. It separates the low-level `ForecastModel` contract from `RealTimeModel`, which runs that contract over vintages. It also provides wrappers and adapters for models in R, MATLAB, and Julia.

## Features

- A common model interface for fitting and forecasting.
- Real-time forecasts across historical or current data vintages.
- Backtesting, simulation, conditioning paths, and parallel vintage batches.
- Linear, tree-based, BVAR, bridge, MIDAS, and Fable model wrappers.
- Adapters for models written in R, MATLAB, and Julia.
- Data transformations, lagged regressors, ragged-edge imputation, and forecast
    decomposition.

`ForecastModel` represents one model. `RealTimeModel` applies it to a `ForecastData` object, deep-copies the model for each vintage, and writes the forecasts back for evaluation. Use `decomp=True` to attribute revisions to news, re-estimation, and interaction.

## Quick start

```python
import forecast_evaluation as fe
import forecast_realtime as rt

forecast_data = fe.ForecastData(load_fer=True)
model = rt.models.ForecastRidge()

rt_model = rt.RealTimeModel(data=forecast_data, models=model)
rt_model.forecast(
    y_variables=["cpisa"],
    step_frequency="Q",
    steps=12,
    label="Ridge",
)
```

Use the same workflow with the package’s linear, tree-based, BVAR, bridge, MIDAS, Fable, or external-language wrappers. Configure transformations, conditioning paths, backtesting, and simulation as required by the exercise.

## Forecast decomposition

Models that support decomposition can explain each vintage revision as news, re-estimation, or their interaction. Enable it with `decomp=True` on `RealTimeModel.forecast()` and inspect the resulting long-format data in `rt_model.decompositions`.

## Repository

Read the implementation and full API reference in the [forecast-realtime repository](https://github.com/bank-of-england/forecast-realtime).