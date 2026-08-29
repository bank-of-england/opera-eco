"""Generated real-time panels shared by pipeline snapshot tests."""

import forecast_realtime as rt
import pandas as pd


def generated_realtime_data(n: int = 5) -> pd.DataFrame:
    """Return a generated real-time panel with native ``pop`` metrics only."""
    panel = rt.generate_synthetic_data(
        N=n,
        seed=20260101,
        first_period="2015-01-31",
        endpoint="2025-12-31",
        publication_lags=True,
    )
    panel = panel.loc[panel["metric"] == "pop"].copy()

    variable_mapping = {
        **{
            f"quarterly_{index}": f"quarterly_{chr(96 + index)}"
            for index in range(1, n + 1)
        },
        **{
            f"monthly_{index}": f"monthly_{chr(96 + index)}"
            for index in range(1, n + 1)
        },
    }
    panel["variable"] = panel["variable"].map(variable_mapping)
    return panel.reset_index(drop=True)
