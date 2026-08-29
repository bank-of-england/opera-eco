"""Compare a MIDAS forecast with its stored snapshot.

The test runs one vintage of the MIDAS model on mixed-frequency data and
compares the output with the stored snapshot.
"""

import pytest

pytest.importorskip("nowcast_midas")

import forecast_evaluation as fe
import forecast_realtime as rt

from .sample_data import sample_midas_data

pytestmark = [pytest.mark.pipeline, pytest.mark.midas]


@pytest.fixture()
def midas_data():
    return sample_midas_data()


def test_midas_data(midas_data, snapshot):
    """Run a MIDAS model on one vintage and compare the snapshot."""

    data = fe.NowcastData(outturns_data=midas_data)

    model = rt.models.ForecastMIDAS(
        method="almon",
        n_lags=5,
        estimator="ols",
        horizons=[0, 1],
        n_ar_lags=1,
    )

    rt_model = rt.RealTimeModel(models=model, data=data)

    y_variables = ["var_quarterly_a"]
    X_variables = ["var_monthly_a"]
    data_transformation = {
        "var_quarterly_a": "pop",
        "var_monthly_a": "pop",
    }

    rt_model.forecast(
        y_variables=y_variables,
        X_variables=X_variables,
        data_transformation=data_transformation,
        step_frequency="Q",
        first_vintage="2024-01-31",
        last_vintage="2024-06-30",
        X_imputation=None,
    )

    # Extract the model forecasts.
    result = rt_model.data.forecasts
    result = result[result["source"] == "ForecastMIDAS"].copy()
    result = result.sort_values(["variable", "date"]).reset_index(drop=True)

    # Round float columns and normalise -0.0 to 0.0 for stable snapshots.
    float_cols = result.select_dtypes(include="float").columns
    result[float_cols] = result[float_cols].round(6) + 0.0

    assert result.to_dict(orient="list") == snapshot


def test_midas_data_decomposition(midas_data, snapshot):
    """Compare the MIDAS decomposition for one vintage with its snapshot."""

    data = fe.NowcastData(outturns_data=midas_data)

    model = rt.models.ForecastMIDAS(
        method="almon",
        n_lags=5,
        estimator="ols",
        horizons=[0, 1],
        n_ar_lags=1,
    )

    rt_model = rt.RealTimeModel(models=model, data=data)

    y_variables = ["var_quarterly_a"]
    X_variables = ["var_monthly_a"]
    data_transformation = {
        "var_quarterly_a": "pop",
        "var_monthly_a": "pop",
    }

    rt_model.forecast(
        y_variables=y_variables,
        X_variables=X_variables,
        data_transformation=data_transformation,
        step_frequency="Q",
        first_vintage="2024-01-31",
        last_vintage="2024-06-30",
        decomp=True,
        X_imputation=None,
    )

    # Extract the model decomposition.
    result = rt_model.decompositions
    result = result[result["source"] == "ForecastMIDAS"].copy()
    result = result.sort_values(
        ["date", "vintage_date", "forecast_horizon", "component"]
    ).reset_index(drop=True)

    # Round float columns and normalise -0.0 to 0.0 so cancellation terms do
    # not change sign across platforms and break the exact snapshot.
    float_cols = result.select_dtypes(include="float").columns
    result[float_cols] = result[float_cols].round(6) + 0.0

    assert result.to_dict(orient="list") == snapshot
