# OPERA: Open-Source Prediction Evaluation and Real-Time Analysis

**[Documentation](https://bank-of-england.github.io/opera-eco/)** | **[Add your own model](https://bank-of-england.github.io/opera-eco/guide/adding_a_model/)**

OPERA is a modular ecosystem for real-time forecasting and open collaboration. It is composed of the following modules:

- [`opera-eco`](https://github.com/bank-of-england/opera-eco) pins compatible releases and supplies documentation, AI skills, and integration tests.
- [`forecast_evaluation`](https://github.com/bank-of-england/forecast_evaluation) validates vintaged outturns and forecasts and provide evaluation and visualisation capabilities.
- [`forecast_realtime`](https://github.com/bank-of-england/forecast-realtime) runs models across vintages.
- [`bvar`](https://github.com/bank-of-england/bvar) provides tools for working with Bayesian VARs.
- [`nowcast-midas`](https://github.com/bank-of-england/nowcast-midas) nowcasts quarterly targets from higher-frequency indicators using MIDAS anc combination techniques.
- [`forecast_combo`](https://github.com/bank-of-england/forecast-combo) combines forecasts through averaging, regression, error-based weighting, or hierarchies.
- [`news_decomp`](https://github.com/bank-of-england/news-decomp) attributes nowcast levels and revisions to news, re-estimation, and interaction.

---

## Architecture

![Forecasting Ecosystem Architecture](docs/diagram.svg)

---

## Modules

| Module | Package | Role |
|---|---|---|
| Model Libraries | `bvar`, `nowcast-midas` | Bayesian VARs; mixed-data sampling and SC-MIDAS combinations |
| Forecast Evaluation | `forecast_evaluation` | Validate data, evaluate accuracy, run statistical tests, visualise |
| Real-time Forecasting | `forecast_realtime` | Fit and forecast wrappers, backtesting, simulation, stress-testing, R/MATLAB/Julia adapters |
| Forecast Combination | `forecast_combo` | Inverse-error, regression and hierarchical combination |
| News Decomposition | `news_decomp` | Nowcast decomposition into level and revision; news/reestimation/interaction |

Install all ecosystem packages with `pip install "opera-eco[modules]"`.

## Authors

The package authors listed in each repository's `pyproject.toml` are:

| Package | Authors |
|---|---|
| `opera-eco` | Paul Labonne; Diego Lopez |
| `forecast_evaluation` | James Hurley; Paul Labonne; Harry Li |
| `forecast_realtime` | Paul Labonne; Sumer Singh; Harry Li; Nades Raviraj |
| `bvar` | Paul Labonne; Andrea Renzetti; Joseph Oyegoke |
| `nowcast-midas` | James Kensett; Paul Labonne; Andre Moreira |
| `forecast_combo` | Filippo Busetto; Paul Labonne; James McConachie; Roshni Tara |
| `news_decomp` | Guido Bonatti; Kensley Blaise; Paul Labonne; Nades Raviraj |

---

## Quick Start

```bash
pip install opera-eco              # Install the CLI and skills only.
pip install "opera-eco[modules]"  # Install the CLI and all ecosystem packages.
pip install "opera-eco[notebooks]" # Install Marimo notebook tooling.
opera install skills               # Install AI skills in .claude/skills/.
```

Then ask Copilot or Claude to use an installed skill:

```text
Tell me about @opera and how I can use it with my model.
```

## OPERA Skills for Claude and Copilot

The package includes seven skills for AI coding assistants:

| Skill | Description |
|---|---|
| **opera** | Meta-skill covering the full ecosystem: architecture, modules, data flows, conventions, integration patterns |
| **forecast-evaluation** | Data validation, accuracy metrics, statistical tests, visualisations, dashboards |
| **forecast-realtime** | Real-time forecasting, backtesting, model wrapping, external language models (R, MATLAB, Julia) |
| **bvar** | Bayesian VARs, conditional forecasting with hard/soft/skewed constraints, GIRFs |
| **nowcast-midas** | MIDAS regressions, MultiMIDAS, SC-MIDAS combinations, monthly-to-quarterly nowcasting |
| **forecast-combo** | Forecast combination methods, hierarchical pooling, weight analysis |
| **forecast-decomp** | Nowcast decomposition: levels and revisions, news, reestimation, interaction, and New York Fed-style analysis |

## Project Layout

```
docs/                            # Documentation site.
examples/illustration.py        # Runnable end-to-end example.
examples/illustration_marimo.py # Native Marimo version of the example.
src/opera/                      # Package source, bundled skills, and tests.
  cli.py                        # Command-line interface.
  skills_manager.py             # Skill discovery and installation.
  skills/                       # Bundled Markdown skill files.
pyproject.toml                  # Python package configuration.
zensical.toml                   # Documentation site configuration.
```

## Data Classification
Bank of England Data Classification: OFFICIAL BLUE