"""Compare a conditional BVAR forecast with its stored snapshot.

The test runs one vintage of the conditional BVAR from the Compass notebook
and compares the output with the stored snapshot.
"""

import pandas as pd
import pytest

pytest.importorskip("bvar")

import forecast_evaluation as fe
import forecast_realtime as rt

pytestmark = [pytest.mark.pipeline, pytest.mark.bvar]

# Set the seed explicitly so every stochastic call is reproducible.
SEED = 42


@pytest.fixture()
def compass_data():
    outturns = rt.generate_synthetic_data(
        N=3,
        seed=20260101,
        first_period="2010-01-31",
        endpoint="2023-12-31",
        publication_lags=True,
    )
    outturns = outturns.loc[outturns["metric"] == "pop"].copy()
    outturns["variable"] = outturns["variable"].replace(
        {
            "quarterly_1": "var_quarterly_a",
            "quarterly_2": "var_quarterly_b",
            "quarterly_3": "var_quarterly_c",
        }
    )
    outturns = outturns.loc[outturns["frequency"] == "Q"].copy()

    forecast_dates = (
        pd.period_range("2023Q3", periods=14, freq="Q")
        .to_timestamp(how="end")
        .normalize()
    )
    latest_outturns = (
        outturns.sort_values("vintage_date")
        .drop_duplicates(["date", "variable"], keep="last")
        .set_index(["date", "variable"])
    )
    forecast_rows = []
    for variable in ["var_quarterly_a", "var_quarterly_b", "var_quarterly_c"]:
        values = pd.Series(
            [
                latest_outturns.loc[(date, variable), "value"]
                if (date, variable) in latest_outturns.index
                else None
                for date in forecast_dates
            ],
            index=forecast_dates,
        ).ffill()
        values = values.fillna(
            outturns.loc[outturns["variable"] == variable, "value"].iloc[-1]
        )
        forecast_rows.extend(
            {
                "date": date,
                "vintage_date": pd.Timestamp("2024-01-31"),
                "variable": variable,
                "source": "source_a",
                "frequency": "Q",
                "forecast_horizon": horizon,
                "metric": "pop",
                "value": value,
            }
            for horizon, (date, value) in enumerate(values.items())
        )
    forecasts = pd.DataFrame(forecast_rows)
    data = fe.ForecastData(outturns_data=outturns, forecasts_data=forecasts)
    data.filter(start_date="1990-01-01")
    return data


def test_bvar_conditional_snapshot(compass_data, snapshot):
    """Run a conditional BVAR on the first vintage and compare the snapshot."""
    # Use one variable for each conditioning horizon, in deliberate order.
    variables = ["var_quarterly_c", "var_quarterly_a", "var_quarterly_b"]

    data_transformation = {
        "var_quarterly_c": "pop",
        "var_quarterly_a": "pop",
        "var_quarterly_b": "pop",
    }

    y_steps_ahead = {
        "var_quarterly_c": 0,  # Horizon 0.
        "var_quarterly_a": 1,  # Horizon 1.
        "var_quarterly_b": 13,  # Horizon 13.
    }

    y_sources = {var: "source_a" for var in variables}

    H = 14

    bvar_model = rt.models.ForecastBVAR(
        stationary=True,
        n_lags=5,
        mode_only=True,
        covid=True,
        optimisation_method="ml",
        optim_random_state=SEED,
        sampling_random_state=SEED,
        forecast_random_state=SEED,
    )

    rt_model = rt.RealTimeModel(
        data=compass_data,
        models=bvar_model,
    )

    rt_model.forecast(
        y_variables=variables,
        data_transformation=data_transformation,
        y_steps_ahead=y_steps_ahead,
        y_sources=y_sources,
        step_frequency="Q",
        steps=H,
        first_vintage="2024-01-31",
        last_vintage="2024-01-31",
    )

    # Extract the model forecasts.
    result = rt_model.data.forecasts

    result = result[result["source"] == "ForecastBVAR"].copy()
    result = result.sort_values(["variable", "date"]).reset_index(drop=True)

    # Round float columns and normalise -0.0 to 0.0 for stable snapshots.
    float_cols = result.select_dtypes(include="float").columns
    result[float_cols] = result[float_cols].round(6) + 0.0

    assert result.to_dict(orient="list") == snapshot
