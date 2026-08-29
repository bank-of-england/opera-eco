# OPERA: Open-Source Prediction Evaluation and Real-Time Analysis

OPERA is a modular ecosystem aimed at streamlining forecasting tasks for economists and fostering open collaboration. Model logic - estimation, forecasting, forecast decomposition - is separated from the real-time workflow, making it easier to compare models in replicable environments and leverage open source contributions. The ecosystem is currently composed of seven blocks which cover the full pipeline from raw data to evaluation. Its architecture, interfaces and design principles reflect the specific constraints of macro analysis: data revision, ragged edge, mixed-frequency, conditional projections, uncertainty quantification, narrative accounting and nested models. By making these modules open-source, OPERA provides a platform for central bankers, academics and other forecasters to share infrastructure and collaborate.

![Forecasting Ecosystem Architecture](diagram.svg)

## Modules

The ecosystem currently contains seven packages. Each package is useful on its own, but their collective value compounds when used together.

| Capability | Package | Role |
|---|---|---|
| Forecast evaluation | [`forecast_evaluation`](https://github.com/bank-of-england/forecast_evaluation) | Validate outturns and forecasts, evaluate accuracy, and visualise results |
| Real-time forecasting | [`forecast_realtime`](https://github.com/bank-of-england/forecast-realtime) | Fit models, run forecasts over vintages, and support backtesting and simulation |
| Bayesian VAR models | [`bvar`](https://github.com/bank-of-england/bvar) | Produce unconditional and conditional Bayesian VAR forecasts |
| Mixed-frequency models | [`nowcast-midas`](https://github.com/bank-of-england/nowcast-midas) | Produce MIDAS, MultiMIDAS, and SC-MIDAS nowcasts |
| Forecast combination | [`forecast_combo`](https://github.com/bank-of-england/forecast-combo) | Combine forecasts using statistical and hierarchical methods |
| News decomposition | [`news_decomp`](https://github.com/bank-of-england/news-decomp) | Attribute forecast revisions to news, re-estimation, and interaction |
| Ecosystem integration | [`opera-eco`](https://github.com/bank-of-england/opera-eco) | Manage dependencies, skills, documentation, and cross-package tests |

### Forecast evaluation: `forecast_evaluation`
#### Maintainers: Harri Li, Paul Labonne
`forecast_evaluation` validates outturn and forecast vintages before models use them, then scores forecasts and provides dashboard visualisations. It checks that outturns match their targets, vintages are comparable, and data contracts are compatible. The module supports point forecasts, nowcasts, and density forecasts.

### Real-time forecasting: `forecast_realtime`
#### Maintainers: Paul Labonne, Sumer Singh

`forecast_realtime` connects models to data and runs the forecasting workflow. It wraps compliant models with a standardised interface for fitting and forecasting. It supports live forecasts, backtesting across historical vintages, simulation experiments, and conditioning paths. It also provides adapters for models written in R, MATLAB, and Julia.

### Native model libraries: `bvar` and `nowcast-midas`
#### Maintainers: Paul Labonne, Andrea Renzetti

Model packages provide estimation and forecasting logic behind standard fit and forecast interfaces. `bvar` provides Bayesian VARs with unconditional and conditional forecasts. `nowcast-midas` provides MIDAS, MultiMIDAS, and SC-MIDAS models for mixed-frequency nowcasting. The orchestration layer uses these interfaces without depending on implementation details.

### Forecast combination: `forecast_combo`
#### Maintainers: Paul Labonne, Filippo Busetto, James McChonachie

`forecast_combo` combines validated forecasts and outturns from `forecast_evaluation` using methods such as inverse-error weighting, optimal pooling, regression, and hierarchical combination. It writes combined forecasts back to `forecast_evaluation`, which evaluates them on the same basis as individual forecasts.

### News decomposition: `news_decomp`
#### Maintainers: Paul Labonne, Guido Banatti

`news_decomp` analyses nowcast updates in the New York Fed style. It separates each update into a level and a revision, then attributes the revision to news, re-estimation, and their interaction. It consumes decompositions from models that support the optional `forecast_realtime` hook and provides accuracy, indicator-usefulness, timing, and real-time revision analyses.

### Ecosystem integration: `opera-eco`
#### Maintainer: Paul Labonne

`opera-eco` pins compatible package releases, installs bundled skills through its command-line interface, and runs ecosystem-wide contract and pipeline suites to verify that packages work together correctly.

## Authors and contributors

## Licence and copyright

This project is released under the [MIT Licence](https://opensource.org/license/mit/).

Copyright (c) 2026 Bank of England.

The full licence text is available in the repository's [LICENSE file](https://github.com/bank-of-england/forecast-combo/blob/main/LICENSE).
