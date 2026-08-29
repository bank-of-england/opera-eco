# Evaluate Forecasts

`forecast_evaluation` validates outturns and forecasts, then provides accuracy statistics and formal forecast tests. Store all forecasts you want to compare in one `ForecastData` object.

## Accuracy statistics

```python
import forecast_evaluation as fe

accuracy = fe.compute_accuracy_statistics(
    data,
    variable="cpisa",
    k=12,
)

accuracy.plot(
    variable="cpisa",
    metric="yoy",
    statistic="rmse",
)
```

The result is a `TestResult`. Convert it to a DataFrame to sort, filter, or export the statistics:

```python
accuracy_table = accuracy.to_df()
```

## Compare against a benchmark

```python
data.add_benchmarks(models=["AR", "random_walk"])

dm = fe.diebold_mariano_table(
    data,
    benchmark_model="random_walk",
    k=12,
)
```

## Bias and efficiency

```python
bias = fe.bias_analysis(data, source="ols", k=12)
bias.plot(variable="cpisa", source="ols", metric="yoy")

efficiency = fe.weak_efficiency_analysis(data, source="ols")
```

The package provides accuracy, bias, Diebold-Mariano, weak- and strong-efficiency, rolling, fluctuation, and revision-error analyses. Each returns a `TestResult` with filtering, plotting, and export helpers.

## Evaluate a combination

`ForecastCombo` writes combined forecasts to the shared object, so the same call can compare an individual model with a combination:

```python
stats = fe.compute_accuracy_statistics(
    combo.forecast_data,
    variable="cpisa",
).to_df()

print(stats[["source", "forecast_horizon", "rmse", "mae"]])
```