"""Compare the mixed-frequency pipeline with stored snapshots.

The test runs the 2026 vintages of ``quarterly_a`` with OLS on the quarterly
block and MIDAS on the monthly indicator. It combines the forecasts with
``forecast_combo`` and compares forecasts, decompositions, and accuracy
statistics with stored snapshots.
"""

import pytest

pytest.importorskip("nowcast_midas")

import forecast_combo as fc
import forecast_evaluation as fe
import forecast_realtime as rt
import news_decomp as nd

from ..sample_data import generated_realtime_data

pytestmark = [pytest.mark.pipeline, pytest.mark.mixed_freq]

TARGET = "quarterly_a"
OLS_REGRESSORS = ["quarterly_b", "quarterly_c", "quarterly_d", "quarterly_e"]
MIDAS_REGRESSOR = "monthly_a"
ALL_REGRESSORS = [*OLS_REGRESSORS, MIDAS_REGRESSOR]

FIRST_VINTAGE = "2026-01-31"
LAST_VINTAGE = "2026-06-30"
STEPS = 2


def _round(df):
    """Round float columns and normalise -0.0 to keep snapshots stable."""
    float_cols = df.select_dtypes(include="float").columns
    df[float_cols] = df[float_cols].round(6) + 0.0
    return df


@pytest.fixture(scope="module")
def mixed_freq_data():
    return generated_realtime_data()


@pytest.fixture(scope="module")
def realtime_model(mixed_freq_data):
    data = fe.NowcastData(outturns_data=mixed_freq_data)

    ols = rt.models.ForecastOLS(
        label="ols",
        formula=f"{TARGET} ~ " + " + ".join(OLS_REGRESSORS),
    )

    midas = rt.models.ForecastMIDAS(
        label="midas",
        method="almon",
        n_lags=5,
        estimator="ols",
        horizons=list(range(STEPS)),
        n_ar_lags=1,
        formula=f"{TARGET} ~ {MIDAS_REGRESSOR}",
    )

    model = rt.RealTimeModel(data=data, models=[ols, midas])

    model.forecast(
        X_variables=ALL_REGRESSORS,
        data_transformation=dict.fromkeys([TARGET, *ALL_REGRESSORS], "pop"),
        X_imputation="last",
        y_variables=[TARGET],
        step_frequency="Q",
        steps=STEPS,
        first_vintage=FIRST_VINTAGE,
        last_vintage=LAST_VINTAGE,
        decomp=True,
    )

    return model


@pytest.fixture(scope="module")
def combo(mixed_freq_data, realtime_model):
    # Pass only quarterly outturns because combinations do not yet support
    # mixed-frequency data fully.
    combo_data = fe.NowcastData(
        outturns_data=mixed_freq_data[mixed_freq_data["frequency"] == "Q"]
    )
    combo_data.add_forecasts(realtime_model.data.forecasts)

    combination = fc.ForecastCombo(forecast_data=combo_data)
    combination.fit(
        sources=["ols", "midas"],
        variables=[TARGET],
        method="rmse",
        metric="pop",
        label="rmse combo",
    )
    return combination


def test_mixed_freq_forecasts(realtime_model, snapshot):
    """Compare OLS and MIDAS forecasts at each vintage."""
    result = realtime_model.data.forecasts.copy()
    result = result.sort_values(
        ["source", "variable", "vintage_date", "date"]
    ).reset_index(drop=True)

    assert _round(result).to_dict(orient="list") == snapshot


def test_mixed_freq_decompositions(realtime_model, snapshot):
    """Compare the nowcast decomposition across vintages."""
    # Constructing NewsData validates the decomposition schema.
    nd.NewsData(realtime_model.decompositions)

    result = realtime_model.decompositions.copy()
    result = result.sort_values(
        ["source", "date", "vintage_date", "forecast_horizon", "component"]
    ).reset_index(drop=True)

    assert _round(result).to_dict(orient="list") == snapshot


def test_mixed_freq_accuracy(combo, snapshot):
    """Compare model and combination accuracy by horizon."""
    stats = fe.compute_accuracy_statistics(combo.forecast_data, variable=TARGET).to_df()
    stats = stats.loc[stats["metric"] == "pop"]
    keep = [
        c for c in ("source", "forecast_horizon", "n_obs", "mae", "rmse") if c in stats
    ]
    stats = stats[keep].sort_values(keep[:2]).reset_index(drop=True)

    assert _round(stats).to_dict(orient="list") == snapshot
