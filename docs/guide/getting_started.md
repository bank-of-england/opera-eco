# Getting Started

## Installation

### Full ecosystem

Install `opera-eco` with every OPERA module dependency:

```sh
pip install "opera-eco[modules]"
```

This installs the `opera` package itself plus:

| Package | Role |
|---|---|
| `forecast_evaluation` | Validate data, evaluate accuracy, visualise |
| `forecast_realtime` | Real-time fit/forecast loops and backtesting |
| `forecast_combo` | Forecast combination |
| `bvar` | Bayesian VAR model library |
| `nowcast-midas` | MIDAS and mixed-frequency model library |
| `news_decomp` | Nowcast news decomposition |

### Skills only

Install the base package when you need assistant skills but not the Python modules:

```sh
pip install opera-eco
```

---

## Installing the Skills

OPERA ships skills for Copilot and Claude. Install them with the `opera` CLI:

```sh
# Install all skills and detect `.github/skills` or `.claude/skills` automatically.
opera install skills
```

Available skills:

| Name | Covers |
|---|---|
| `opera` | Full ecosystem architecture and module interactions |
| `forecast-evaluation` | Evaluating forecast accuracy |
| `forecast-realtime` | Real-time forecasting and backtesting |
| `forecast-combo` | Forecast combination methods |
| `bvar` | Bayesian VAR estimation |
| `nowcast-midas` | MIDAS and mixed-frequency nowcasting |
| `forecast-decomp` | Nowcast news decomposition |

---

## Using the Skills with an LLM

After installation, Copilot reads skills from `.github/skills/` and Claude reads them from `.claude/skills/`. Ask questions such as:

- *"How to backtest my model using OPERA?"*
- *"What combination methods are available in `forecast_combo`?"*

## Next Steps

Read the [example pipeline](example_pipeline.md) or run the [Marimo notebook](../notebooks/illustration.md).