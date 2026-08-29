import pandas as pd
import pytest
from news_decomp import NewsData
from pandera.errors import SchemaError, SchemaErrors

pytestmark = pytest.mark.contract


def _rows():
    return pd.DataFrame(
        {
            "variable": ["y", "y"],
            "date": pd.to_datetime(["2024-04-01", "2024-04-01"]),
            "forecast_horizon": [0, 0],
            "frequency": ["Q", "Q"],
            "source": ["tiny", "tiny"],
            "vintage_date": pd.to_datetime(["2024-02-01", "2024-03-01"]),
            "base_vintage_date": pd.to_datetime([pd.NaT, "2024-02-01"]),
            "decomposition": ["level", "revision"],
            "component": ["x", "x"],
            "revision_source": [pd.NA, "news"],
            "contribution": [2.0, 1.0],
            "weight": [1.0, 1.0],
            "news": [2.0, 1.0],
            "forecast_metric": ["levels", "levels"],
        }
    )


def test_news_data_accepts_level_and_revision_rows():
    data = NewsData(_rows())

    assert len(data.df) == 2
    assert set(data.df["decomposition"]) == {"level", "revision"}


def test_news_data_rejects_extra_columns():
    rows = _rows().assign(unexpected=1)

    with pytest.raises(SchemaErrors, match="column.*not|not.*schema"):
        NewsData(rows)


def test_news_data_rejects_inconsistent_contribution():
    rows = _rows()
    rows.loc[1, "contribution"] = 2.0

    with pytest.raises(SchemaError, match="contribution.*weight.*news"):
        NewsData(rows)


def test_news_data_rejects_level_row_with_base_vintage_date():
    rows = _rows()
    rows.loc[0, "base_vintage_date"] = pd.Timestamp("2024-01-01")

    with pytest.raises(SchemaError, match="decomposition.*base_vintage_date"):
        NewsData(rows)


def test_news_data_rejects_revision_row_without_required_metadata():
    rows = _rows()
    rows.loc[1, "revision_source"] = pd.NA

    with pytest.raises(SchemaError, match="revision_source.*decomposition"):
        NewsData(rows)
