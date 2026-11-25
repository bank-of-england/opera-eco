"""Backtest inflation forecasts across curated UK vintages.

Foundation models need optional backends and weights.
"""

# install the feature/foundation_models of forecast-realtime
import os

import numpy as np
from forecast_combo import ForecastCombo
from forecast_evaluation import ForecastData
from forecast_realtime import RealTimeModel
from forecast_realtime.models import (
    ForecastBVAR,
    ForecastChronos2,
    ForecastRidge,
    ForecastT0,
    ForecastTabICLv2,
    ForecastTimesFM,
    ForecastTimestral,
)
from sklearn.model_selection import TimeSeriesSplit

if __package__:
    from .curate_uk_realtime import curate_uk_data
else:
    from curate_uk_realtime import curate_uk_data

TARGET = "cpi_inflation"
TARGET_FORMULA = f"{TARGET} ~ ."  # all explanatory variables with lags
FOUNDATION_FORMULA = f"{TARGET} ~ raw(.)"  # all explanatory variables without lags
STEPS = 3
RANDOM_STATE = 1234
VINTAGE_START = "2015-01-01"

# tells Hugging Face to use cached model weights instead of contacting the Hub
os.environ.setdefault("HF_HUB_OFFLINE", "1")

if __name__ == "__main__":
    """Forecast from the first vintage on or after the cutoff."""
    np.random.seed(RANDOM_STATE)
    outturns = curate_uk_data()
    variables = outturns["variable"].unique().tolist()
    predictors = [variable for variable in variables if variable != TARGET]

    data = ForecastData(outturns_data=outturns, compute_levels=False, default_k=0)

    models = [
        ForecastRidge(
            label="Ridge",
            formula=TARGET_FORMULA,
            cv=TimeSeriesSplit(n_splits=5, gap=STEPS),
            alphas=np.logspace(-4, 4, 17),
            alpha_scaling="mean",
            penalise_ar=False,
            scale=True,
            forecast_strategy="direct",
            steps=STEPS,
            drop_nans=True,
        ),
        ForecastBVAR(label="BVAR", mode_only=True, progressbar=False),
        ForecastTimestral(
            label="Timestral-5M",
            formula=FOUNDATION_FORMULA,
            model_id="mistralai/Timestral-5M",
            device="cpu",
        ),
        ForecastT0(
            label="T0-alpha",
            formula=FOUNDATION_FORMULA,
            model_id="theforecastingcompany/t0-alpha",
            device="cpu",
        ),
        ForecastChronos2(
            label="Chronos-2-small",
            formula=FOUNDATION_FORMULA,
            model_id="autogluon/chronos-2-small",
            device="cpu",
        ),
        ForecastTimesFM(
            label="TimesFM-3.0",
            formula=FOUNDATION_FORMULA,
            model_id="google/timesfm-3.0-pytorch",
            device="cpu",
        ),
        ForecastTabICLv2(label="TabICLv2", formula=FOUNDATION_FORMULA, device="cpu"),
        # ForecastTabPFN(
        #     label="TabPFN-TS", formula=FOUNDATION_FORMULA, model_id="tabpfn-v2-regressor.ckpt",
        #     device="cpu",
        # ),
    ]

    model = RealTimeModel(data, models)
    model.forecast(
        y_variables=variables,
        X_variables=predictors,
        data_transformation=dict.fromkeys(variables, "levels"),
        step_frequency="M",
        steps=STEPS,
        first_vintage=VINTAGE_START,
        carry_forward_history=False,
        parallel=True,
        max_workers=len(models),
        batch_size=outturns["vintage_date"].nunique(),
        y_lags=1,
        X_lags=1,
        X_imputation="last",
        drop_transformation_nans=False,
        reconstruct_levels=False,
    )
    forecasts = model.data

    # Add benchmark models
    forecasts.add_benchmarks(
        models=["AR", "random_walk"],
        variables=[TARGET],
        metric="levels",
        frequency="M",
        forecast_periods=STEPS,
        max_lag=1,
    )

    # Add combos
    points = forecasts.forecasts
    sources = (
        points.loc[
            points["variable"].eq(TARGET) & points["metric"].eq("levels"), "unique_id"
        ]
        .unique()
        .tolist()
    )

    combo = ForecastCombo(forecasts)
    combo.fit(
        sources=sources,
        variables=[TARGET],
        method=["average", "rmse"],
        metric="levels",
        k=0,
        allow_partial_sources=True,
    )

    # launch dashboard for evaluation
    forecasts = combo.forecast_data
    forecasts.run_dashboard()
