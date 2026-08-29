# `forecast_evaluation`

## Purpose

`forecast_evaluation` evaluates real-time point and density forecasts across forecast vintages. It supports quarterly (`Q`) and monthly (`M`) data, vintage-aware outturn revisions, and intra-period nowcasts. It validates both the realised outturns used for scoring and the forecast paths supplied by models or conditional exercises.

The module provides data validation; accuracy, bias, efficiency, and Diebold-Mariano tests; rolling and fluctuation tests; a Shiny dashboard; and a nowcasting workflow for intra-period vintages, such as weekly observations.

## Features

- `ForecastData` for vintage-aware point forecasts and outturns.
- `NowcastData` for forecasts updated several times within a target period.
- `DensityForecastData` for quantile forecasts and empirical densities.
- Accuracy, bias, efficiency, revision, and benchmark comparisons.
- Rolling and fluctuation tests for changes in forecast performance.
- Matplotlib visualisations and an interactive Shiny dashboard.

The package uses long-format forecast data and supports quarterly (`Q`) and monthly (`M`) frequencies. Add outturns before forecasts so the package can align vintages and calculate evaluation results.

## Analysis

Use the package to compare forecast accuracy and bias, test forecast efficiency, study revisions and nowcast performance, and monitor changes in performance over time. Results can be explored in tables, plots, or the interactive dashboard.

## Bundled data

The package includes a bundled Forecast Evaluation Report dataset for trying the evaluation workflow and comparing forecasts with benchmark models.

## Quick start

```python
import forecast_evaluation as fe

data = fe.ForecastData(load_fer=True)
data.filter(variables=["gdpkp", "cpisa"])

# Compute accuracy and plot the result.
acc = fe.compute_accuracy_statistics(data, k=12)
acc.plot(variable="cpisa", metric="yoy", statistic="rmse")

# Compare with MPR using the Diebold-Mariano test.
dm = fe.diebold_mariano_table(data, benchmark_model="mpr", k=12)

# Analyse bias.
bias = fe.bias_analysis(data, source="mpr", k=12)
bias.plot(variable="aweagg", source="mpr", metric="yoy")

# Open the interactive dashboard.
data.run_dashboard()
```

## Repository

Read the implementation and full API reference in the [forecast_evaluation repository](https://github.com/bank-of-england/forecast_evaluation).