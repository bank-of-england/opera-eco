# Install the libraries before running this example.
# pip install "opera-eco[modules]"

# %% Import modules and set options.
import forecast_combo as fc
import forecast_evaluation as fe
import forecast_realtime as rt
import news_decomp as nd

from opera.sample_realtime_data import create_realtime_mixed_freq_data

target = "quarterly_a"
ols_regressors = ["quarterly_b", "quarterly_c", "quarterly_d", "quarterly_e"]
midas_regressor = "monthly_a"
all_regressors = ols_regressors + [midas_regressor]

first_vintage = "2026-01-31"
last_vintage = "2026-12-31"
steps = 2

# %% Load the real-time panel.
mixed_freq_data = create_realtime_mixed_freq_data()

data = fe.NowcastData(outturns_data=mixed_freq_data)

# %% Fit OLS to the quarterly block and MIDAS to the monthly indicator.
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

# %% Run the vintage loop.
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

# %% Decompose the nowcast news.
# `decomp=True` records each regressor's contribution to the nowcast level and
# to its revision at every vintage.
news = nd.NewsData(realtime_model.decompositions)
# news.report()  # Uncomment to print the report.

# %% Combine the two models.
combo = fc.ForecastCombo(forecast_data=realtime_model.data)

combo.fit(
    sources=["ols", "midas"],
    variables=[target],
    method="rmse",
    metric="levels",
    label="rmse combo",
)

# %% Compare accuracy by horizon.
stats = fe.compute_accuracy_statistics(combo.forecast_data, variable=target).to_df()
stats = stats.loc[stats["metric"] == "levels"]
keep = [c for c in ("source", "forecast_horizon", "n_obs", "mae", "rmse") if c in stats]
stats = stats[keep].sort_values(keep[:2]).reset_index(drop=True)

print("\nAccuracy:\n", stats)
