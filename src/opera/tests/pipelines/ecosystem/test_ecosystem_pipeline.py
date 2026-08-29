"""Compare the OPERA ecosystem illustration with stored snapshots.

The tests mirror ``examples/illustration.py``. They run a real-time vintage
loop, combine OLS and MIDAS forecasts, decompose the resulting nowcasts, and
compare each stage with a stored snapshot.
"""

import forecast_combo as fc
import forecast_evaluation as fe
import forecast_realtime as rt
import news_decomp as nd
import pytest

from ..sample_data import generated_realtime_data

pytestmark = [pytest.mark.pipeline, pytest.mark.ecosystem]

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
def realtime_model():
    """Run the vintage loop once for all tests in this module."""
    data = fe.NowcastData(outturns_data=generated_realtime_data())

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
def combo(realtime_model):
    """Combine the two models with inverse-RMSE weights."""
    combination = fc.ForecastCombo(forecast_data=realtime_model.data)

    combination.fit(
        sources=["ols", "midas"],
        variables=[TARGET],
        method="rmse",
        metric="pop",
        label="rmse combo",
    )

    return combination


def test_ecosystem_forecasts(realtime_model, snapshot):
    """Compare the OLS and MIDAS forecasts at each vintage."""
    result = realtime_model.data.forecasts.copy()
    result = result.sort_values(
        ["source", "variable", "vintage_date", "date"]
    ).reset_index(drop=True)

    assert _round(result).to_dict(orient="list") == snapshot


def test_ecosystem_news(realtime_model, snapshot):
    """Compare nowcast levels and revisions from the news decomposition."""
    news = nd.NewsData(realtime_model.decompositions)

    result = news.df.copy()
    result = result.sort_values(
        ["source", "date", "vintage_date", "forecast_horizon", "component"]
    ).reset_index(drop=True)

    assert _round(result).to_dict(orient="list") == snapshot


def test_ecosystem_combo(combo, snapshot):
    """Compare forecasts from the inverse-RMSE combination."""
    forecasts = combo.forecast_data.forecasts
    result = forecasts[forecasts["source"] == "rmse combo"].copy()
    # Exclude a source-order identifier and internal alignment state from the snapshot.
    result = result.drop(columns=["unique_id", "_aligned"], errors="ignore")
    result = result.sort_values(
        ["variable", "vintage_date", "date", "forecast_horizon"]
    ).reset_index(drop=True)

    assert _round(result).to_dict(orient="list") == snapshot


def test_ecosystem_evaluation(combo, snapshot):
    """Compare accuracy for each model and the combination by horizon."""
    stats = fe.compute_accuracy_statistics(combo.forecast_data, variable=TARGET).to_df()
    stats = stats.loc[stats["metric"] == "pop"]
    keep = [
        c for c in ("source", "forecast_horizon", "n_obs", "mae", "rmse") if c in stats
    ]
    stats = stats[keep].sort_values(keep[:2]).reset_index(drop=True)

    assert _round(stats).to_dict(orient="list") == snapshot
