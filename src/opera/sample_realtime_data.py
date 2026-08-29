"""Create a typical real-time, mixed-frequency dataset.

The dataset contains five quarterly (``quarterly_a`` to ``quarterly_e``) and
five monthly (``monthly_a`` to ``monthly_e``) standard-white-noise series.
Each series has its own publication lag.

* Reference dates are period **ends** (end-of-quarter / end-of-month).
* The data starts in 1990.
* Real-time **vintages start in 2026**. The initial vintage contains everything
    published before ``VINTAGE_START``. From then on, each observation appears
    at its first release and once more at a later revision.

The output is a long, compact real-time table with one row per
``(variable, date, vintage_date)`` — a row is only emitted when the value
changes, which is the usual storage convention for vintage databases.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SEED = 20260101
DATA_START = "1990-01-01"
DATA_END = "2026-12-31"
VINTAGE_START = pd.Timestamp("2026-01-01")

# Publication lag in days for each variable.
QUARTERLY_SERIES: dict[str, int] = {
    "quarterly_a": 30,
    "quarterly_b": 45,
    "quarterly_c": 60,
    "quarterly_d": 75,
    "quarterly_e": 85,
}

MONTHLY_SERIES: dict[str, int] = {
    "monthly_a": 2,
    "monthly_b": 8,
    "monthly_c": 16,
    "monthly_d": 25,
    "monthly_e": 40,
}

# Release schedule: one first release followed by a revision after this delay.
REVISION_LAG_DAYS = 90
REVISION_NOISE_STD = 0.25  # Standard deviation of the revision error.


def _release_rows(
    variable: str,
    frequency: str,
    dates: pd.DatetimeIndex,
    values: np.ndarray,
    pub_lag_days: int,
    rng: np.random.Generator,
) -> list[dict]:
    """Build first-release and revision rows for one series."""
    rows: list[dict] = []
    first_releases = dates + pd.Timedelta(days=pub_lag_days)
    revisions = first_releases + pd.Timedelta(days=REVISION_LAG_DAYS)
    provisional = values + rng.normal(0.0, REVISION_NOISE_STD, size=len(values))

    for date, first, revised, prov, final in zip(
        dates, first_releases, revisions, provisional, values, strict=True
    ):
        if first >= VINTAGE_START:
            # Both releases fall within the real-time sample.
            releases = ((first, prov), (revised, final))
        elif revised >= VINTAGE_START:
            # The initial vintage contains the provisional estimate, and the
            # revision arrives during the real-time sample.
            releases = ((VINTAGE_START, prov), (revised, final))
        else:
            # The final value was published before the first vintage, so the
            # initial vintage contains it once.
            releases = ((VINTAGE_START, final),)

        for vintage, value in releases:
            rows.append(
                {
                    "date": date,
                    "variable": variable,
                    "vintage_date": vintage,
                    "frequency": frequency,
                    "value": round(float(value), 4),
                }
            )
    return rows


def create_realtime_mixed_freq_data(seed: int = SEED) -> pd.DataFrame:
    """Create a real-time, mixed-frequency panel of white-noise series.

    Parameters
    ----------
    seed : int
        Seed for the random-number generator.

    Returns
    -------
    pd.DataFrame
        Long format with columns ``date``, ``variable``, ``vintage_date``,
        ``frequency`` and ``value``, sorted by variable, reference date and
        vintage date.
    """
    rng = np.random.default_rng(seed)

    q_dates = pd.date_range(DATA_START, DATA_END, freq="QE")
    m_dates = pd.date_range(DATA_START, DATA_END, freq="ME")

    rows: list[dict] = []
    for freq, dates, spec in (
        ("Q", q_dates, QUARTERLY_SERIES),
        ("M", m_dates, MONTHLY_SERIES),
    ):
        for variable, pub_lag in spec.items():
            rows.extend(
                _release_rows(
                    variable=variable,
                    frequency=freq,
                    dates=dates,
                    values=rng.standard_normal(len(dates)),
                    pub_lag_days=pub_lag,
                    rng=rng,
                )
            )

    return (
        pd.DataFrame(rows)
        .sort_values(["variable", "date", "vintage_date"])
        .reset_index(drop=True)
    )


def get_vintage(data: pd.DataFrame, vintage_date: str | pd.Timestamp) -> pd.DataFrame:
    """Return the panel available at ``vintage_date``.

    For each ``(variable, date)`` pair, retain the most recent value published
    on or before ``vintage_date``.
    """
    as_of = pd.Timestamp(vintage_date)
    available = data.loc[data["vintage_date"] <= as_of]
    latest = (
        available.sort_values("vintage_date")
        .groupby(["variable", "date"], as_index=False)
        .last()
    )
    return latest.sort_values(["variable", "date"]).reset_index(drop=True)


if __name__ == "__main__":
    panel = create_realtime_mixed_freq_data()
    print(panel.head())
    print(f"\nrows: {len(panel):,}")
    print(
        f"vintages: {panel['vintage_date'].min():%Y-%m-%d} -> "
        f"{panel['vintage_date'].max():%Y-%m-%d}"
    )
    print(f"\nvintage 2026-06-30:\n{get_vintage(panel, '2026-06-30').tail()}")
