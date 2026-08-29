"""Compare an SC-MIDAS combination forecast with its snapshot.

The test mirrors ``test_midas_snapshot`` but drives ``ForecastMIDASCombo``
through the real-time pipeline. It fits a two-leg combination over
``var_monthly_a`` and a noisy synthetic variant, then compares the result with
the available snapshot data.
"""

import pytest

pytest.importorskip("nowcast_midas")

import forecast_evaluation as fe
import forecast_realtime as rt
from nowcast_midas.specs import ComboSpec, MidasSpec

from .sample_data import sample_midas_data

pytestmark = [pytest.mark.pipeline, pytest.mark.midas]

NOISY_VAR = "var_monthly_b"


@pytest.fixture()
def scmidas_data():
    return sample_midas_data()


def test_scmidas_data(scmidas_data, snapshot):
    """Run an SC-MIDAS combination and compare the snapshot."""

    data = fe.NowcastData(outturns_data=scmidas_data)

    midas_gdp = MidasSpec(
        "var_monthly_a",
        method="almon",
        n_lags=5,
        n_ar_lags=1,
    )
    midas_noisy = MidasSpec(
        NOISY_VAR,
        method="almon",
        n_lags=5,
        n_ar_lags=1,
    )

    soft_combo = ComboSpec(
        name="soft_combo",
        sources=[midas_gdp, midas_noisy],
        method="mse",
        window=8,
        discount_rate=0.95,
    )

    model = rt.models.ForecastMIDASCombo(
        combo_specs=soft_combo,
        horizons=2,
    )

    rt_model = rt.RealTimeModel(models=model, data=data)

    y_variables = ["var_quarterly_a"]
    X_variables = ["var_monthly_a", NOISY_VAR]
    data_transformation = {
        "var_quarterly_a": "pop",
        "var_monthly_a": "pop",
        NOISY_VAR: "pop",
    }

    rt_model.forecast(
        y_variables=y_variables,
        X_variables=X_variables,
        data_transformation=data_transformation,
        step_frequency="Q",
        first_vintage="2024-01-31",
        last_vintage="2024-06-30",
    )

    result = rt_model.data.forecasts
    result = result[result["source"] == "ForecastMIDASCombo"].copy()
    result = result.sort_values(["variable", "date"]).reset_index(drop=True)

    # Round float columns and normalise -0.0 to 0.0 for stable snapshots.
    float_cols = result.select_dtypes(include="float").columns
    result[float_cols] = result[float_cols].round(6) + 0.0

    assert result.to_dict(orient="list") == snapshot


def test_scmidas_data_decomposition(scmidas_data, snapshot):
    """Compare the SC-MIDAS decomposition with its stored snapshot."""

    data = fe.NowcastData(outturns_data=scmidas_data)

    midas_gdp = MidasSpec(
        "var_monthly_a",
        method="almon",
        n_lags=5,
        n_ar_lags=1,
    )
    midas_noisy = MidasSpec(
        NOISY_VAR,
        method="almon",
        n_lags=5,
        n_ar_lags=1,
    )

    soft_combo = ComboSpec(
        name="soft_combo",
        sources=[midas_gdp, midas_noisy],
        method="mse",
        window=8,
        discount_rate=0.95,
    )

    model = rt.models.ForecastMIDASCombo(
        combo_specs=soft_combo,
        horizons=2,
        aggregate_decomp=True,
    )

    rt_model = rt.RealTimeModel(models=model, data=data)

    y_variables = ["var_quarterly_a"]
    X_variables = ["var_monthly_a", NOISY_VAR]
    data_transformation = {
        "var_quarterly_a": "pop",
        "var_monthly_a": "pop",
        NOISY_VAR: "pop",
    }

    rt_model.forecast(
        y_variables=y_variables,
        X_variables=X_variables,
        data_transformation=data_transformation,
        step_frequency="Q",
        first_vintage="2024-01-31",
        last_vintage="2024-01-31",
        decomp=True,
        X_imputation=None,
    )

    # Extract the model decomposition.
    result = rt_model.decompositions
    result = result[result["source"] == "ForecastMIDASCombo"].copy()
    result = result.sort_values(
        ["date", "vintage_date", "forecast_horizon", "component"]
    ).reset_index(drop=True)

    # Round float columns and normalise -0.0 to 0.0 so cancellation terms do
    # not change sign across platforms and break the exact snapshot.
    float_cols = result.select_dtypes(include="float").columns
    result[float_cols] = result[float_cols].round(6) + 0.0

    assert result.to_dict(orient="list") == snapshot
