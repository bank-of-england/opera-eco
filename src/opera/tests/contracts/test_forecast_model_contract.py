import numpy as np
import pandas as pd
import pytest
from forecast_realtime import ForecastModel

pytestmark = pytest.mark.contract


class TinyForecastModel(ForecastModel):
    def _fit(self, y, X, **kwargs):
        self._value = float(y.iloc[-1, 0])
        return self

    def _forecast(self, steps, X, y, **kwargs):
        return np.full((steps, 1), self._value)


def _history():
    index = pd.date_range("2024-01-01", periods=3, freq="D")
    return pd.DataFrame({"y": [1.0, 2.0, 3.0]}, index=index), pd.DataFrame(
        {"x": [4.0, 5.0, 6.0]}, index=index
    )


def test_forecast_model_fit_is_chainable_and_forecast_is_valid():
    y, X = _history()
    model = TinyForecastModel(label="tiny")

    assert model.fit(y, X) is model
    result = model.forecast(steps=2)

    assert result.forecast.shape == (2, 1)
    assert result.forecast.columns.tolist() == ["y"]
    assert result.forecast.iloc[:, 0].tolist() == [3.0, 3.0]


def test_forecast_model_rejects_forecast_with_wrong_columns():
    y, X = _history()

    class InvalidForecastModel(TinyForecastModel):
        def _forecast(self, steps, X, y, **kwargs):
            return pd.DataFrame(
                {"wrong": [1.0] * steps},
                index=pd.date_range("2024-01-04", periods=steps, freq="D"),
            )

    model = InvalidForecastModel().fit(y, X)
    with pytest.raises((ValueError, TypeError), match="column|target|y"):
        model.forecast(steps=1)
