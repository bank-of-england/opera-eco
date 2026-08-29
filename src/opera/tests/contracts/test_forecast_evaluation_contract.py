import forecast_evaluation as fe
import pandas as pd
import pytest

pytestmark = pytest.mark.contract


def _outturns(rows):
    return pd.DataFrame(
        rows,
        columns=[
            "date",
            "vintage_date",
            "variable",
            "frequency",
            "forecast_horizon",
            "value",
        ],
    )


def _forecasts(rows):
    return pd.DataFrame(
        rows,
        columns=[
            "date",
            "vintage_date",
            "variable",
            "frequency",
            "forecast_horizon",
            "value",
            "source",
        ],
    )


def test_forecast_data_accepts_representative_point_data():
    data = fe.ForecastData(
        outturns_data=_outturns([("2024-04-01", "2024-05-01", "y", "Q", 0, 10.0)]),
        forecasts_data=_forecasts(
            [("2024-07-01", "2024-05-01", "y", "Q", 1, 11.0, "tiny")]
        ),
    )

    assert data.forecasts["source"].drop_duplicates().tolist() == ["tiny"]
    assert data.forecasts["forecast_horizon"].drop_duplicates().tolist() == [1]


def test_forecast_data_rejects_missing_required_forecast_column():
    forecasts = _forecasts(
        [("2024-07-01", "2024-05-01", "y", "Q", 1, 11.0, "tiny")]
    ).drop(columns="source")

    with pytest.raises(ValueError, match="source"):
        fe.ForecastData(
            outturns_data=_outturns([("2024-04-01", "2024-05-01", "y", "Q", 0, 10.0)]),
            forecasts_data=forecasts,
        )


def test_forecast_data_rejects_forecasts_before_outturns():
    data = fe.ForecastData()

    with pytest.raises(ValueError, match="Outturns must be added before forecasts"):
        data.add_forecasts(
            _forecasts([("2024-07-01", "2024-05-01", "y", "Q", 1, 11.0, "tiny")])
        )


def test_nowcast_data_tracks_multiple_vintages_and_revision_index():
    outturns = _outturns(
        [
            ("2024-01-01", "2024-01-15", "y", "Q", 0, 10.0),
            ("2024-01-01", "2024-02-01", "y", "Q", 0, 11.0),
        ]
    )
    forecasts = _forecasts(
        [
            ("2024-01-01", "2024-01-15", "y", "Q", 0, 10.5, "tiny"),
            ("2024-01-01", "2024-02-01", "y", "Q", 0, 11.5, "tiny"),
        ]
    )

    data = fe.NowcastData(outturns_data=outturns, forecasts_data=forecasts)

    assert set(data.df["vintage_date_forecast"]) == set(
        pd.to_datetime(["2024-01-15", "2024-02-01"])
    )
    assert set(data.df["k"]) == {-2, -1}
    assert "days_to_publication" in data.df


def _density_frame(quantiles):
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-04-01"] * len(quantiles)),
            "vintage_date": pd.to_datetime(["2024-02-01"] * len(quantiles)),
            "variable": ["y"] * len(quantiles),
            "frequency": ["Q"] * len(quantiles),
            "forecast_horizon": [0] * len(quantiles),
            "value": list(range(1, len(quantiles) + 1)),
            "source": ["tiny"] * len(quantiles),
            "quantile": quantiles,
        }
    )


def test_density_forecast_data_accepts_valid_quantiles():
    data = fe.DensityForecastData(
        outturns_data=_outturns([("2024-04-01", "2024-02-01", "y", "Q", 0, 10.0)]),
        forecasts_data=_density_frame([0.1, 0.5, 0.9]),
    )

    assert data.density_forecasts["quantile"].tolist() == [0.1, 0.5, 0.9]


def test_density_forecast_data_rejects_missing_quantile():
    forecasts = _density_frame([0.5]).drop(columns="quantile")

    with pytest.raises(ValueError, match="quantile"):
        fe.DensityForecastData(
            outturns_data=_outturns([("2024-04-01", "2024-02-01", "y", "Q", 0, 10.0)]),
            forecasts_data=forecasts,
        )


@pytest.mark.parametrize("quantile", [-0.1, 1.1])
def test_density_forecast_data_rejects_out_of_range_quantile(quantile):
    with pytest.raises((ValueError, TypeError), match="quantile|between|range|0"):
        fe.DensityForecastData(
            outturns_data=_outturns([("2024-04-01", "2024-02-01", "y", "Q", 0, 10.0)]),
            forecasts_data=_density_frame([quantile]),
        )
