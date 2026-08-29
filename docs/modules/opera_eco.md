# `opera-eco`

## Purpose

`opera-eco` coordinates the OPERA forecasting ecosystem. It keeps compatible package releases together, distributes shared coding-assistant skills, and checks that the packages work together through common interfaces and workflows testing.

## Features

- Install a compatible set of OPERA forecasting packages.
- Install bundled skills for the OPERA ecosystem and its individual modules.
- Run shared contract tests for package interfaces and data exchange.
- Run end-to-end pipeline tests across models, forecasting, evaluation, combination, and news decomposition.
- Support package maintainers as they test changes across the ecosystem.

The package keeps model logic separate from real-time workflow orchestration. Model packages provide estimation and forecasting; workflow packages run models across vintages, evaluate results, combine forecasts, and explain revisions.

## Quick start

Install the package with its test dependencies:

```bash
python -m pip install "opera-eco[test]"
```

Run the shared test suites from a package repository:

```bash
pytest --pyargs opera.tests -m contract
pytest --pyargs opera.tests -m pipeline
```

Install the bundled skills with the command-line interface:

```bash
opera install skills
```

## Repository

Read the implementation and full API reference in the [`opera-eco` repository](https://github.com/bank-of-england/opera-eco).
