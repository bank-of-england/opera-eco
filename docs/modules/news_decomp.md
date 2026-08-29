# `news-decomp`

## Purpose

`news-decomp` explains how new data releases change nowcasts. It follows the New York Fed news-decomposition approach and separates a forecast revision into news, re-estimation, and interaction effects.

## Features

- Decompose nowcast changes across data vintages.
- Distinguish news from model re-estimation and their interaction.
- Analyse contributions by variable, release, forecast horizon, or vintage.
- Produce contribution tables, summary reports, and visualisations.
- Compare revisions across models and nowcasting exercises.

## Quick start

```python
from news_decomp import NewsData

data = NewsData(decompositions)
data.summary()
data.plot_contributions()
```

Provide a vintage-aware decomposition table containing forecast revisions and their component contributions. The package validates the data and returns long-format results for further analysis or reporting.

## Repository

Read the implementation and full API reference in the [news-decomp repository](https://github.com/bank-of-england/news-decomp).
