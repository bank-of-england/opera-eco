import forecast_evaluation as fe
import forecast_realtime as rt
import numpy as np
import pandas as pd
import pytest
from news_decomp import NewsData

pytestmark = pytest.mark.contract


class _DeterministicForecastModel(rt.ForecastModel):
    def _fit(self, y, X=None, **kwargs):
        self.value = float(y.iloc[-1, 0]) + 0.5
        return self

    def _forecast(self, steps=1, X=None, y=None, **kwargs):
        return np.full((steps, 1), self.value)


def test_forecast_data_public_output_can_be_handed_to_nowcast_data():
    outturns = pd.DataFrame(
        {
            "date": pd.to_datetime(["2023-10-01", "2024-01-01"]),
            "vintage_date": pd.to_datetime(["2024-01-31", "2024-01-31"]),
            "variable": ["y", "y"],
            "frequency": ["Q", "Q"],
            "forecast_horizon": [0, 0],
            "value": [9.0, 10.0],
        }
    )
    point_data = fe.ForecastData(outturns_data=outturns)
    realtime_model = rt.RealTimeModel(
        data=point_data,
        models=_DeterministicForecastModel(label="tiny"),
    )
    realtime_model.forecast(
        y_variables=["y"],
        step_frequency="Q",
        steps=1,
        first_vintage="2024-01-31",
        last_vintage="2024-01-31",
    )

    nowcast_data = fe.NowcastData(
        outturns_data=point_data.outturns,
        forecasts_data=point_data.forecasts,
    )

    assert not nowcast_data.forecasts.empty
    assert nowcast_data.forecasts["source"].unique().tolist() == ["tiny"]
    assert 10.5 in nowcast_data.forecasts["value"].tolist()


def test_public_news_data_accepts_small_decomposition_handoff():
    decomposition = pd.DataFrame(
        {
            "variable": ["y"],
            "date": pd.to_datetime(["2024-04-01"]),
            "forecast_horizon": [0],
            "frequency": ["Q"],
            "source": ["tiny"],
            "vintage_date": pd.to_datetime(["2024-02-01"]),
            "base_vintage_date": [pd.NaT],
            "decomposition": ["level"],
            "component": ["x"],
            "revision_source": [pd.NA],
            "contribution": [1.0],
            "weight": [1.0],
            "news": [1.0],
            "forecast_metric": ["levels"],
        }
    )

    news = NewsData(decomposition)

    assert news.df.equals(decomposition)
