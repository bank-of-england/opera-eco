"""Generated real-time data used by the MIDAS pipeline snapshots."""

import pandas as pd

from ..sample_data import generated_realtime_data


def sample_midas_data() -> pd.DataFrame:
    """Return generated ``pop`` data for the MIDAS input variables."""
    panel = generated_realtime_data(n=2)
    panel["variable"] = panel["variable"].replace(
        {
            "quarterly_a": "var_quarterly_a",
            "monthly_a": "var_monthly_a",
            "monthly_b": "var_monthly_b",
        }
    )
    return panel
