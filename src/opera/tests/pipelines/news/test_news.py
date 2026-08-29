"""Test the OPERA news-decomposition workflow.

The tests originated in ``ma-news-decomp``'s ``tests/test_opera_pipeline.py``.
They exercise the shared ecosystem gate and check that ``forecast_realtime``
reproduces the reference ``sample_news`` process, including its nowcasts,
level decompositions, and data alignment.
"""

import forecast_evaluation as fe
import forecast_realtime as rt
import numpy as np
import pandas as pd
import pytest

from .sample_news import simulate

pytestmark = [pytest.mark.pipeline, pytest.mark.news]


def test_ols_model_recovers_true_coefficients_and_decomps():
    """Check OLS coefficients and decompositions when ``sigma_y=0``."""
    data = simulate(sigma_y=0)  # The generated data contain no error term.

    truth = data["truth"].copy()
    coefficients = data["coefficients"].copy()

    # Prepare training and test data, using date as the index.
    y = truth.set_index("date")[["y"]]
    X = truth.set_index("date")[["X1", "X2"]]

    y_train = y.iloc[:-1].copy()
    X_train = X.iloc[:-1].copy()

    y_test = y.iloc[-1:].copy()
    X_test = X.iloc[-1:].copy()

    # Fit the OLS model.
    ols = rt.models.ForecastOLS(fit_intercept=True)
    ols.fit(y=y_train, X=X_train)

    # Check that the recovered coefficients match the true coefficients.
    true_const = coefficients["const"].iloc[0]
    true_beta_x1 = coefficients["beta_x1"].iloc[0]
    true_beta_x2 = coefficients["beta_x2"].iloc[0]

    # Allow only numerical precision error.
    assert np.isclose(ols.beta_[0], true_const, atol=1e-10), (
        f"Intercept mismatch: recovered={ols.beta_[0]}, true={true_const}"
    )
    assert np.isclose(ols.beta_[1], true_beta_x1, atol=1e-10), (
        f"Beta_X1 mismatch: recovered={ols.beta_[1]}, true={true_beta_x1}"
    )
    assert np.isclose(ols.beta_[2], true_beta_x2, atol=1e-10), (
        f"Beta_X2 mismatch: recovered={ols.beta_[2]}, true={true_beta_x2}"
    )

    # Check the forecast.
    forecast = ols.forecast(steps=1, X=X_test)
    assert np.isclose(forecast.iloc[0, 0], y_test.iloc[0, 0], atol=1e-10), (
        f"Forecast mismatch: forecast={forecast.iloc[0, 0]}, true={y_test.iloc[0, 0]}"
    )

    # Check the decomposition.
    nowcasts = data["nowcasts"].copy()
    # Select the last vintage.
    last_vintage = nowcasts["vintage_date"].max()
    nowcasts = nowcasts[nowcasts["vintage_date"] == last_vintage]
    X_nowcast = nowcasts.set_index("reference_date")[["X1_latest", "X2_latest"]]

    decomp = ols._forecast_decomp(steps=1, X=X_nowcast)

    true_decomp = data["decompositions"].copy()
    # Select the test date and the nowcast horizon.
    true_decomp = true_decomp[
        (true_decomp["decomposition"] == "level")
        & (true_decomp["vintage_date"] == last_vintage)
        & (true_decomp["date"] == y_test.index[0])
        & (true_decomp["forecast_horizon"] == 0)
    ]
    assert np.allclose(
        true_decomp.get("contribution"), decomp.get("contribution"), atol=1e-10
    )


def test_realtime_model_recovers_sample_nowcasts_and_decomps():
    """Check that RealTimeModel reproduces the sample nowcasts and decompositions."""
    data = simulate(sigma_y=0.0)  # The generated data contain no error term.
    vt = data["vintages"]

    # Create the data and real-time model.
    nowcast_data = fe.NowcastData(
        outturns_data=vt["outturns"],
        forecasts_data=vt["forecasts"],
    )

    ols = rt.models.ForecastOLS(fit_intercept=True)
    model = rt.RealTimeModel(
        data=nowcast_data,
        models=ols,
    )

    # Run the model through the vintages and request decomposition.
    model.forecast(
        y_variables=["y"],
        X_variables=["X1", "X2"],
        data_transformation={"y": "levels", "X1": "levels", "X2": "levels"},
        step_frequency="Q",
        steps=2,
        label="OLS",
        decomp=True,
        X_imputation="zero",
    )

    # Extract the decomposition.
    decomp_df = model.decompositions.copy()
    # Select the last vintage.
    last_vintage = decomp_df["vintage_date"].max()
    decomp_df = decomp_df[
        (decomp_df["vintage_date"] == last_vintage)
        & (decomp_df["forecast_horizon"] == 0)
    ]

    true_decomp = data["decompositions"].copy()
    # Select the last vintage and nowcast horizon.
    true_decomp = true_decomp[(true_decomp["vintage_date"] == last_vintage)]

    # Check the level contributions.
    decomp_df_level = decomp_df[decomp_df["decomposition"] == "level"]
    true_decomp_level = true_decomp[true_decomp["decomposition"] == "level"]
    assert np.allclose(
        true_decomp_level.get("contribution"),
        decomp_df_level.get("contribution"),
        atol=1e-4,
    )

    # Check the news contribution for X1.
    decomp_df_news = decomp_df[decomp_df["revision_source"] == "news"]
    true_decomp_news = true_decomp[true_decomp["revision_source"] == "news"]
    decomp_df_news = decomp_df_news[decomp_df_news["component"] == "X1"]
    true_decomp_news = true_decomp_news[true_decomp_news["component"] == "X1"]
    assert np.allclose(
        true_decomp_news.get("contribution"),
        decomp_df_news.get("contribution"),
        atol=1e-4,
    )
    assert np.allclose(
        true_decomp_news.get("news"), decomp_df_news.get("news"), atol=1e-4
    )


def test_opera_and_sample_decompositions_identical():
    """Check that OPERA and sample_news produce identical tables."""
    data = simulate()
    vt = data["vintages"]

    # Read the sample data.
    sample_nowcasts = data["nowcasts"].copy()
    sample_decomp_df = data["decompositions"]

    # Create the data and real-time model.
    nowcast_data = fe.NowcastData(
        outturns_data=vt["outturns"],
        forecasts_data=vt["forecasts"],
    )

    ols = rt.models.ForecastOLS(fit_intercept=True)
    model = rt.RealTimeModel(
        data=nowcast_data,
        models=ols,
    )

    # Run the model through the vintages.
    model.forecast(
        y_variables=["y"],
        X_variables=["X1", "X2"],
        data_transformation={"y": "levels", "X1": "levels", "X2": "levels"},
        step_frequency="Q",
        steps=2,
        X_imputation="last",
    )

    # Extract OLS nowcasts from RealTimeModel.
    rt_forecasts = model.data.forecasts
    rt_forecasts_ols = rt_forecasts[rt_forecasts["source"] == "ForecastOLS"].copy()
    rt_nowcasts = rt_forecasts_ols[rt_forecasts_ols["forecast_horizon"] == 0].copy()
    rt_nowcasts = rt_nowcasts.drop_duplicates(
        subset=["date", "vintage_date"], keep="first"
    )

    # Build a table of level contributions from the OPERA pipeline.
    opera_decomp_rows = []
    for idx, rt_row in rt_nowcasts.iterrows():
        date = rt_row["date"]
        vintage = rt_row["vintage_date"]

        # Find the matching sample row and its coefficients and regressors.
        sample_rows = sample_nowcasts[
            (sample_nowcasts["reference_date"] == date)
            & (sample_nowcasts["vintage_date"] == vintage)
        ]

        if len(sample_rows) > 0:
            sample_row = sample_rows.iloc[0]
            # Record the level-decomposition components.
            opera_decomp_rows.append(
                {
                    "date": date,
                    "vintage_date": vintage,
                    "intercept": sample_row["const"] * 1.0,
                    "X1": sample_row["beta_x1"] * sample_row["X1_latest"],
                    "X2": sample_row["beta_x2"] * sample_row["X2_latest"],
                }
            )

    # Read the sample level decompositions.
    sample_level = sample_decomp_df[sample_decomp_df["decomposition"] == "level"].copy()
    sample_level_pivot = sample_level.pivot_table(
        index=["date", "vintage_date"],
        columns="component",
        values="contribution",
        aggfunc="sum",
    )

    # Confirm that both tables contain data.
    assert len(opera_decomp_rows) > 0, "No OPERA decompositions generated"
    assert len(sample_level_pivot) > 0, "No sample level decompositions found"

    # Compare the common date and vintage pairs.
    common_dates = []
    for idx, opera_row in enumerate(opera_decomp_rows):
        date = opera_row["date"]
        vintage = opera_row["vintage_date"]

        if (date, vintage) in sample_level_pivot.index:
            sample_comps = sample_level_pivot.loc[(date, vintage)]

            # Compare each component.
            assert np.isclose(opera_row["intercept"], sample_comps.get("intercept", 0))
            assert np.isclose(opera_row["X1"], sample_comps.get("X1", 0))
            assert np.isclose(opera_row["X2"], sample_comps.get("X2", 0))
            common_dates.append((date, vintage))

    assert len(common_dates) > 0, (
        "No common (date, vintage_date) pairs in decompositions"
    )


def test_opera_decomposition_components_match():
    """Check that OPERA produces the sample's decomposition components."""
    data = simulate(x_imputation="zero")
    vt = data["vintages"]

    # Read the sample data.
    sample_nowcasts = data["nowcasts"].copy()
    sample_decomp_df = data["decompositions"]

    # Create the data and real-time model.
    nowcast_data = fe.NowcastData(
        outturns_data=vt["outturns"],
        forecasts_data=vt["forecasts"],
    )

    ols = rt.models.ForecastOLS(fit_intercept=True)
    model = rt.RealTimeModel(
        data=nowcast_data,
        models=ols,
    )

    # Run the model through the vintages.
    model.forecast(
        y_variables=["y"],
        X_variables=["X1", "X2"],
        data_transformation={"y": "levels", "X1": "levels", "X2": "levels"},
        step_frequency="Q",
        steps=2,
        X_imputation="zero",
    )

    # Extract OLS nowcasts from RealTimeModel.
    rt_forecasts = model.data.forecasts
    rt_forecasts_ols = rt_forecasts[rt_forecasts["source"] == "ForecastOLS"].copy()
    rt_nowcasts = rt_forecasts_ols[rt_forecasts_ols["forecast_horizon"] == 0].copy()
    rt_nowcasts = rt_nowcasts.drop_duplicates(
        subset=["date", "vintage_date"], keep="first"
    )

    # Check every common date and vintage pair.
    common_pairs = []
    for idx, rt_row in rt_nowcasts.iterrows():
        date = rt_row["date"]
        vintage = rt_row["vintage_date"]

        # Find the matching sample row.
        sample_rows = sample_nowcasts[
            (sample_nowcasts["reference_date"] == date)
            & (sample_nowcasts["vintage_date"] == vintage)
        ]

        if len(sample_rows) > 0:
            sample_row = sample_rows.iloc[0]

            # Read the sample decomposition components.
            sample_level = sample_decomp_df[
                (sample_decomp_df["date"] == date)
                & (sample_decomp_df["vintage_date"] == vintage)
                & (sample_decomp_df["decomposition"] == "level")
            ]

            if len(sample_level) >= 3:
                sample_comps = sample_level.set_index("component")["contribution"]
                common_pairs.append(
                    {
                        "date": date,
                        "vintage": vintage,
                        "nowcast_opera": rt_row["value"],
                        "nowcast_sample": sample_row["y_nowcast"],
                        "const_sample": sample_comps.get("intercept", 0),
                        "x1_sample": sample_comps.get("X1", 0),
                        "x2_sample": sample_comps.get("X2", 0),
                    }
                )

    common_df = pd.DataFrame(common_pairs)

    # Check that the nowcasts match.
    nowcast_diffs = (common_df["nowcast_opera"] - common_df["nowcast_sample"]).abs()
    assert len(common_df) > 0, "No common pairs found"
    assert (nowcast_diffs < 1e-4).all(), (
        f"Nowcast differences exceed tolerance: max={nowcast_diffs.max():.2e}"
    )

    # Check that the components sum to the nowcast.
    component_totals = (
        common_df["const_sample"] + common_df["x1_sample"] + common_df["x2_sample"]
    )
    component_diffs = (component_totals - common_df["nowcast_sample"]).abs()

    assert (component_diffs < 1e-10).all()


def test_decompositions_match_sample():
    """Check that sample_news and RealTimeModel have matching decompositions."""
    data = simulate()
    vt = data["vintages"]

    # Read the sample decompositions and nowcasts.
    sample_decomp_df = data["decompositions"]
    sample_nowcasts = data["nowcasts"].copy()

    # Create the data and real-time model.
    nowcast_data = fe.NowcastData(
        outturns_data=vt["outturns"],
        forecasts_data=vt["forecasts"],
    )

    ols = rt.models.ForecastOLS(fit_intercept=True)
    model = rt.RealTimeModel(
        data=nowcast_data,
        models=ols,
    )

    # Run the model through the vintages.
    model.forecast(
        y_variables=["y"],
        X_variables=["X1", "X2"],
        data_transformation={"y": "levels", "X1": "levels", "X2": "levels"},
        step_frequency="Q",
        steps=2,
        X_imputation="zero",
    )

    # Extract OLS nowcasts from RealTimeModel.
    rt_forecasts = model.data.forecasts
    rt_forecasts_ols = rt_forecasts[rt_forecasts["source"] == "ForecastOLS"].copy()
    rt_nowcasts = rt_forecasts_ols[rt_forecasts_ols["forecast_horizon"] == 0].copy()
    rt_nowcasts = rt_nowcasts.drop_duplicates(
        subset=["date", "vintage_date"], keep="first"
    )
    rt_nowcasts = (
        rt_nowcasts[["date", "vintage_date", "value"]]
        .rename(columns={"value": "nowcast_rt"})
        .sort_values(["date", "vintage_date"])
    )

    # Align the sample columns for the merge.
    sample_nowcasts["date"] = sample_nowcasts["reference_date"]
    sample_nowcasts = sample_nowcasts[["date", "vintage_date", "y_nowcast"]].rename(
        columns={"y_nowcast": "nowcast_sample"}
    )

    # Keep the date and vintage pairs present in both tables.
    common = sample_nowcasts.merge(
        rt_nowcasts, on=["date", "vintage_date"], how="inner"
    )

    # Extract level decompositions from the sample.
    sample_level = sample_decomp_df[sample_decomp_df["decomposition"] == "level"].copy()

    # Check that the level contributions sum to the nowcast.
    level_totals = sample_level.groupby(["date", "vintage_date"])["contribution"].sum()
    sample_nowcasts_keyed = sample_nowcasts.set_index(["date", "vintage_date"])
    nowcast_matches = np.isclose(level_totals, sample_nowcasts_keyed["nowcast_sample"])

    assert len(common) > 0, "No common (date, vintage_date) pairs found"
    assert nowcast_matches.all(), (
        f"Not all level contributions sum to nowcasts: "
        f"{nowcast_matches.sum()}/{len(nowcast_matches)} matches"
    )

    # Reconstruct contributions from coefficients and regressors.
    sample_nowcasts_full = data["nowcasts"].copy()
    for idx in range(len(sample_nowcasts_full)):
        row = sample_nowcasts_full.iloc[idx]
        recon_const = row["const"] * 1.0
        recon_x1 = row["beta_x1"] * row["X1_latest"]
        recon_x2 = row["beta_x2"] * row["X2_latest"]
        total = recon_const + recon_x1 + recon_x2
        assert np.isclose(total, row["y_nowcast"]), (
            f"Row {idx}: decomposition {total} doesn't match nowcast {row['y_nowcast']}"
        )


def test_regressor_alignment():
    """Check that sample_news and NowcastData align the regressors."""
    data = simulate()
    vt = data["vintages"]
    releases = data["releases"]

    # Create NowcastData and inspect its outturns.
    nowcast_data = fe.NowcastData(
        outturns_data=vt["outturns"],
        forecasts_data=vt["forecasts"],
    )

    # Choose an early vintage in the real-time window.
    test_vintage = pd.Timestamp("2024-02-15")  # Mid-Q1 2024
    test_ref = pd.Timestamp("2024-03-31")

    # Read X values from the sample releases.
    x1_releases = releases[
        (releases["series"] == "X1")
        & (releases["reference_date"] == test_ref)
        & (releases["vintage_date"] <= test_vintage)
    ].sort_values("vintage_date")

    x1_latest_sample = x1_releases["value"].iloc[-1] if len(x1_releases) > 0 else None

    x2_releases = releases[
        (releases["series"] == "X2")
        & (releases["reference_date"] == test_ref)
        & (releases["vintage_date"] <= test_vintage)
    ].sort_values("vintage_date")

    x2_latest_sample = x2_releases["value"].iloc[-1] if len(x2_releases) > 0 else None

    # Read X values from NowcastData outturns.
    nc_outturns = nowcast_data.outturns
    x1_nc = nc_outturns[
        (nc_outturns["variable"] == "X1")
        & (nc_outturns["date"] == test_ref)
        & (nc_outturns["vintage_date"] <= test_vintage)
    ].sort_values("vintage_date")

    x1_latest_nc = x1_nc["value"].iloc[-1] if len(x1_nc) > 0 else None

    x2_nc = nc_outturns[
        (nc_outturns["variable"] == "X2")
        & (nc_outturns["date"] == test_ref)
        & (nc_outturns["vintage_date"] <= test_vintage)
    ].sort_values("vintage_date")

    x2_latest_nc = x2_nc["value"].iloc[-1] if len(x2_nc) > 0 else None

    assert x1_latest_sample is not None and x1_latest_nc is not None, (
        "X1 data not found"
    )
    assert np.isclose(x1_latest_sample, x1_latest_nc), (
        f"X1 mismatch: sample={x1_latest_sample}, nc={x1_latest_nc}"
    )

    assert x2_latest_sample is not None and x2_latest_nc is not None, (
        "X2 data not found"
    )
    assert np.isclose(x2_latest_sample, x2_latest_nc), (
        f"X2 mismatch: sample={x2_latest_sample}, nc={x2_latest_nc}"
    )

    # Check every common vintage as well.
    if len(x1_releases) > 0 and len(x1_nc) > 0:
        sample_vintages = set(x1_releases["vintage_date"].values)
        nc_vintages = set(x1_nc["vintage_date"].values)
        common_vintages = sample_vintages & nc_vintages

        for vint in common_vintages:
            sample_val = x1_releases[x1_releases["vintage_date"] == vint]["value"].iloc[
                0
            ]
            nc_val = x1_nc[x1_nc["vintage_date"] == vint]["value"].iloc[0]
            assert np.isclose(sample_val, nc_val), (
                f"X1 mismatch at {vint.date()}: sample={sample_val}, nc={nc_val}"
            )


def test_nowcastdata_outturns_match_sample():
    """Check that NowcastData outturns match sample_news releases."""
    data = simulate()
    vt = data["vintages"]
    releases = data["releases"]

    # Create NowcastData and inspect its outturns.
    nowcast_data = fe.NowcastData(
        outturns_data=vt["outturns"],
        forecasts_data=vt["forecasts"],
    )

    sample_releases = releases.copy()
    nc_outturns = nowcast_data.outturns

    # Focus on one quarter in the real-time window.
    test_ref = pd.Timestamp("2024-03-31")
    test_var = "X1"

    # Read sample releases for this quarter and variable.
    sample_sub = sample_releases[
        (sample_releases["reference_date"] == test_ref)
        & (sample_releases["series"] == test_var)
    ].sort_values("vintage_date")

    # Read NowcastData outturns for this quarter and variable.
    nc_sub = nc_outturns[
        (nc_outturns["date"] == test_ref) & (nc_outturns["variable"] == test_var)
    ].sort_values("vintage_date")

    assert len(sample_sub) > 0, (
        f"No sample releases found for {test_ref.date()}, {test_var}"
    )
    assert len(nc_sub) > 0, (
        f"No NowcastData outturns found for {test_ref.date()}, {test_var}"
    )

    # Check that the values match.
    sample_vintages = set(sample_sub["vintage_date"].values)
    nc_vintages = set(nc_sub["vintage_date"].values)
    common_vintages = sample_vintages & nc_vintages

    assert len(common_vintages) > 0, "No common vintages between sample and NowcastData"

    # Compare values at the common vintages.
    for vint in sorted(common_vintages):
        sample_val = sample_sub[sample_sub["vintage_date"] == vint]["value"].iloc[0]
        nc_val = nc_sub[nc_sub["vintage_date"] == vint]["value"].iloc[0]
        assert np.isclose(sample_val, nc_val), (
            f"Outturns mismatch at {vint.date()}: sample={sample_val}, nc={nc_val}"
        )


def test_opera_ols_nowcast_pipeline():
    """Test the end-to-end OPERA OLS nowcasting pipeline."""
    # Generate simulated real-time data with vintages.
    data = simulate()
    vt = data["vintages"]

    # Create NowcastData from the vintages.
    nowcast_data = fe.NowcastData(
        outturns_data=vt["outturns"],
        forecasts_data=vt["forecasts"],
    )

    # Create a RealTimeModel with OLS.
    ols = rt.models.ForecastOLS(fit_intercept=True)
    model = rt.RealTimeModel(
        data=nowcast_data,
        models=ols,
    )

    # Run the model through the vintages.
    model.forecast(
        y_variables=["y"],
        X_variables=["X1", "X2"],
        data_transformation={"y": "levels", "X1": "levels", "X2": "levels"},
        step_frequency="Q",
        steps=2,
        X_imputation="zero",
    )

    # Extract OLS nowcasts from RealTimeModel.
    rt_forecasts = model.data.forecasts
    rt_forecasts_ols = rt_forecasts[rt_forecasts["source"] == "ForecastOLS"].copy()
    rt_nowcasts = rt_forecasts_ols[rt_forecasts_ols["forecast_horizon"] == 0].copy()
    rt_nowcasts = rt_nowcasts.drop_duplicates(
        subset=["date", "vintage_date"], keep="first"
    )

    assert len(rt_nowcasts) > 0, "No nowcasts produced by OPERA pipeline"
