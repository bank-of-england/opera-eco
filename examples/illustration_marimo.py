import marimo

__generated_with = "0.24.0"

app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        """
        # OPERA mixed-frequency forecasting

        This notebook runs OLS and MIDAS forecasts, decomposes nowcast news,
        combines the forecasts, and compares accuracy across horizons.

        Install the ecosystem and notebook dependencies first:

        ```bash
        pip install "opera-eco[modules,notebooks]"
        ```
        """
    )


@app.cell
def _():
    import forecast_combo as fc
    import forecast_evaluation as fe
    import forecast_realtime as rt
    import news_decomp as nd

    from opera.sample_realtime_data import create_realtime_mixed_freq_data

    target = "quarterly_a"
    ols_regressors = [
        "quarterly_b",
        "quarterly_c",
        "quarterly_d",
        "quarterly_e",
    ]
    midas_regressor = "monthly_a"
    all_regressors = ols_regressors + [midas_regressor]

    first_vintage = "2026-01-31"
    last_vintage = "2026-12-31"
    steps = 2
    return (
        all_regressors,
        create_realtime_mixed_freq_data,
        fc,
        fe,
        first_vintage,
        last_vintage,
        midas_regressor,
        nd,
        ols_regressors,
        rt,
        steps,
        target,
    )


@app.cell
def _(create_realtime_mixed_freq_data, fe):
    mixed_freq_data = create_realtime_mixed_freq_data()
    data = fe.NowcastData(outturns_data=mixed_freq_data)
    return data


@app.cell
def _(midas_regressor, ols_regressors, rt, steps, target):
    ols = rt.models.ForecastOLS(
        label="ols",
        formula=f"{target} ~ " + " + ".join(ols_regressors),
    )

    midas = rt.models.ForecastMIDAS(
        label="midas",
        method="almon",
        n_lags=5,
        estimator="ols",
        horizons=list(range(steps)),
        n_ar_lags=1,
        formula=f"{target} ~ {midas_regressor}",
    )
    return midas, ols


@app.cell
def _(
    all_regressors,
    data,
    first_vintage,
    last_vintage,
    midas,
    ols,
    rt,
    steps,
    target,
):
    realtime_model = rt.RealTimeModel(data=data, models=[ols, midas])

    realtime_model.forecast(
        X_variables=all_regressors,
        data_transformation=dict.fromkeys([target, *all_regressors], "levels"),
        X_imputation="last",
        y_variables=[target],
        step_frequency="Q",
        steps=steps,
        first_vintage=first_vintage,
        last_vintage=last_vintage,
        decomp=True,
    )

    realtime_model.data.summary()
    return realtime_model


@app.cell
def _(nd, realtime_model):
    news = nd.NewsData(realtime_model.decompositions)
    return news


@app.cell
def _(fc, realtime_model, target):
    combo = fc.ForecastCombo(forecast_data=realtime_model.data)

    combo.fit(
        sources=["ols", "midas"],
        variables=[target],
        method="rmse",
        metric="levels",
        label="rmse combo",
    )
    return combo


@app.cell
def _(combo, fe, target):
    stats = fe.compute_accuracy_statistics(
        combo.forecast_data,
        variable=target,
    ).to_df()
    stats = stats.loc[stats["metric"] == "levels"]
    keep = [
        column
        for column in ("source", "forecast_horizon", "n_obs", "mae", "rmse")
        if column in stats
    ]
    stats = stats[keep].sort_values(keep[:2]).reset_index(drop=True)

    print("\nAccuracy:\n", stats)
    return stats


if __name__ == "__main__":
    app.run()
