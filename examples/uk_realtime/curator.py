"""Curate monthly releases and revisions into as-of estimation panels."""

from collections.abc import Iterator, Mapping, Sequence

import numpy as np
import pandas as pd


def stationarise_series(
    name: str, values: pd.Series | pd.DataFrame, steps: Sequence[str] = ()
):
    """Apply ordered steps down monthly rows, separately for each vintage column.

    Dated inputs may omit months. For other indices, pass consecutive monthly
    rows with missing values left in place. An empty recipe keeps values as supplied.
    """
    if isinstance(steps, str) or any(
        step not in ("log", "diff", "log diff") for step in steps
    ):
        raise ValueError(
            f"Expected a sequence of 'log', 'diff' or 'log diff' steps for {name}."
        )
    if not steps or values.empty:
        return values
    data = values
    months = None
    if isinstance(values.index, (pd.DatetimeIndex, pd.PeriodIndex)):
        index = values.index
        months = (
            index.to_period("M")
            if isinstance(index, pd.DatetimeIndex)
            else index.asfreq("M")
        )
        if months.hasnans or not months.is_unique:
            raise ValueError(f"Expected one dated observation per month for {name}.")
        data = values.set_axis(months).reindex(
            pd.period_range(months.min(), months.max(), freq="M")
        )
    for step in steps:
        if step in ("log", "log diff"):
            if data.le(0).any(axis=None):
                raise ValueError(
                    f"Log transformation requires positive values for {name}."
                )
            data = np.log(data)
        if step in ("diff", "log diff"):
            data = data.diff()
    return data if months is None else data.reindex(months).set_axis(values.index)


def build_estimation_releases(
    monthly: pd.DataFrame, *, stationarise: bool = True, transform=stationarise_series
) -> pd.DataFrame:
    """Return real-time changes in transformed or as-published units."""
    if monthly.empty:
        raise ValueError("No monthly releases are available by the requested date.")
    parts = []
    for name, rows in monthly.groupby("variable", sort=True, observed=True):
        if rows["value"].isna().any() or not np.isfinite(rows["value"]).all():
            raise ValueError(f"Non-finite published value for {name}.")
        levels = rows.pivot(index="date", columns="vintage_date", values="value")
        levels.index = pd.PeriodIndex(levels.index, freq="M")
        calendar = pd.period_range(levels.index.min(), levels.index.max(), freq="M")
        levels = levels.reindex(calendar).sort_index(axis=1).ffill(axis=1)
        transformed = transform(name, levels) if stationarise else levels
        changed = transformed.notna() & transformed.ne(transformed.shift(axis=1))
        months, vintages = np.nonzero(changed.to_numpy())
        parts.append(
            pd.DataFrame(
                {
                    "date": calendar[months].to_timestamp("M"),
                    "variable": name,
                    "vintage_date": levels.columns[vintages],
                    "frequency": "M",
                    "value": transformed.to_numpy()[months, vintages],
                }
            )
        )
    return pd.concat(parts, ignore_index=True)


def balanced_window(
    panel: pd.DataFrame, vintage_date, *, months: int = 60, lag_months: int = 3
) -> pd.DataFrame:
    """Keep complete, nonconstant series in a common window of an as-of panel."""
    if months < 2 or lag_months < 0:
        raise ValueError("Use at least two months and a non-negative publication lag.")
    end = pd.Period(vintage_date, freq="M") - lag_months
    dates = pd.period_range(end=end, periods=months, freq="M").to_timestamp("M")
    window = panel.reindex(dates.rename("date")).dropna(axis="columns")
    return window.loc[:, window.max() > window.min()]


class Curator:
    """Build balanced panels from monthly releases and revisions.

    Pass one row per ``(variable, date, vintage_date)`` with a numeric ``value``.
    ``date`` is the reference month; ``vintage_date`` is the publication date.
    Supply ordered transformation steps by variable. Unspecified variables stay
    as published. Pass preprocessing row counts as ``source_counts`` to include
    them in the audit log.
    After ``curate()``, ``dataset`` holds the returned DataFrame and
    ``iter_vintages()`` yields complete matrices for estimation. Inspect
    ``log`` for the latest run or ``dataset.attrs["curation_log"]`` for that frame.
    """

    def __init__(
        self,
        releases: pd.DataFrame,
        *,
        transformations: Mapping[str, Sequence[str]] | None = None,
        source_counts: Mapping[str, int] | None = None,
    ):
        keys = ["variable", "date", "vintage_date"]
        columns = [*keys, "value"]
        missing = pd.Index(columns).difference(releases.columns)
        if len(missing):
            raise ValueError(f"Missing release columns: {', '.join(missing)}")
        self._recipes = {}
        for name, steps in (transformations or {}).items():
            if isinstance(steps, str) or not isinstance(steps, Sequence):
                raise TypeError(
                    f"Pass an ordered sequence of transformation steps for {name}."
                )
            self._recipes[name] = tuple(steps)
        monthly = releases.loc[:, columns].copy()
        unused = pd.Index(self._recipes).difference(monthly["variable"].unique())
        if len(unused):
            raise ValueError(
                f"Transformation recipes do not match selected monthly series: {', '.join(unused)}"
            )
        monthly["date"] = pd.PeriodIndex(monthly["date"], freq="M")
        monthly["vintage_date"] = pd.to_datetime(monthly["vintage_date"])
        if monthly[keys].isna().any().any() or monthly.duplicated(keys).any():
            raise ValueError(
                "Each release needs a unique series, reference month and vintage date."
            )
        self._monthly = monthly
        self._input_counts = {**(source_counts or {}), "release_rows": len(monthly)}
        self._release_cache: dict[bool, pd.DataFrame] = {}
        self.dataset = pd.DataFrame()
        self._as_of: pd.Timestamp | None = None

    @property
    def log(self) -> dict:
        """Return the latest successful run's audit log, or an empty dict before curation."""
        return self.dataset.attrs.get("curation_log", {})

    def make_stationary(self, name: str, values: pd.Series | pd.DataFrame):
        """Apply this variable's configured transformation, if any."""
        return stationarise_series(name, values, self._recipes.get(name, ()))

    def curate(
        self,
        as_of: str | pd.Timestamp | None = None,
        *,
        snapshot_freq: str | None = None,
        stationarise: bool = True,
        min_months: int = 96,
        end_month: str | pd.Period | None = None,
        variables: Sequence[str] | None = None,
        extend_history: bool = False,
    ) -> pd.DataFrame:
        """Store and return balanced monthly data for one vintage or all vintages.

        Apply the configured transformations when ``stationarise`` is true;
        otherwise keep published units. Require ``min_months`` consecutive,
        nonconstant months through ``end_month`` (default: the previous month).
        With ``extend_history``, include earlier consecutive common history.

        With ``as_of``, return dates by variables. Without it, index ``dataset``
        by (vintage_date, date), omitting origins with no eligible panel.
        By default, take a snapshot on each release date. Set ``snapshot_freq``
        to a pandas frequency such as ``W-FRI``, ``ME`` or ``QE`` to take
        end-of-day snapshots between the first and last release dates instead.
        If ``variables`` are specified, require them all in order: skip
        ineligible origins in a backtest, or raise for a single requested origin.
        """
        if min_months < 2:
            raise ValueError("Use at least two months of history.")
        if variables is not None:
            if isinstance(variables, str) or not pd.Index(variables).is_unique:
                raise ValueError("Pass a sequence of distinct variable names.")
            unknown = pd.Index(variables).difference(self._monthly["variable"].unique())
            if len(unknown):
                raise ValueError(f"Unknown series: {', '.join(unknown)}")
        cutoff = pd.Timestamp(as_of) if as_of is not None else None
        origins = (
            pd.DatetimeIndex([cutoff])
            if cutoff is not None
            else pd.DatetimeIndex(self._monthly["vintage_date"].unique()).sort_values()
        )
        if snapshot_freq is not None:
            if cutoff is not None:
                raise ValueError("Choose either as_of or snapshot_freq, not both.")
            offset = pd.tseries.frequencies.to_offset(snapshot_freq)
            calendar_offsets = (
                pd.offsets.Day,
                pd.offsets.Week,
                pd.offsets.MonthEnd,
                pd.offsets.QuarterEnd,
                pd.offsets.YearEnd,
            )
            if not isinstance(offset, calendar_offsets) or offset.n <= 0:
                raise ValueError(
                    "Use a positive daily, weekly, month-end, quarter-end or year-end snapshot_freq."
                )
            if len(origins):
                origins = pd.date_range(
                    origins.min(), origins.max(), freq=offset, normalize=True
                )
        end = pd.Period(end_month, freq="M") if end_month is not None else None
        if origins.hasnans or (
            end is not None
            and (pd.isna(end) or (len(origins) and end > origins.max().to_period("M")))
        ):
            raise ValueError(
                "Provide a valid origin and an end month no later than the origin."
            )
        if stationarise not in self._release_cache:
            changes = build_estimation_releases(
                self._monthly, stationarise=stationarise, transform=self.make_stationary
            )
            self._release_cache[stationarise] = changes.set_index(
                "vintage_date"
            ).sort_index()
        changes = self._release_cache[stationarise]
        windows = {}
        skipped = {
            "end_after_origin": 0,
            "requested_series_ineligible": 0,
            "no_eligible_series": 0,
        }
        for vintage in origins:
            month = vintage.to_period("M")
            if end is not None and end > month:
                skipped["end_after_origin"] += 1
                continue
            through = (
                vintage.strftime("%Y-%m-%d") if snapshot_freq is not None else vintage
            )
            latest = changes.loc[:through].drop_duplicates(
                ["variable", "date"], keep="last"
            )
            panel = latest.pivot(index="date", columns="variable", values="value")
            lag = 1 if end is None else month.ordinal - end.ordinal
            window = balanced_window(panel, vintage, months=min_months, lag_months=lag)
            if variables is not None:
                missing = pd.Index(variables).difference(window.columns)
                if len(missing):
                    if cutoff is None:
                        skipped["requested_series_ineligible"] += 1
                        continue
                    raise ValueError(
                        f"Series unavailable or ineligible at {vintage.date()}: {', '.join(missing)}"
                    )
                window = window.loc[:, list(variables)]
            if extend_history and not window.empty:
                dates = pd.date_range(
                    panel.index.min(), window.index[-1], freq="ME", name="date"
                )
                history = panel.reindex(index=dates, columns=window.columns)
                gaps = history.index[history.isna().any(axis=1)]
                window = (
                    history if gaps.empty else history.loc[history.index > gaps[-1]]
                )
            if cutoff is not None or not window.empty:
                windows[vintage] = window
            else:
                skipped["no_eligible_series"] += 1
        if cutoff is not None:
            self.dataset = windows[cutoff]
        elif windows:
            dataset = pd.concat(windows, names=["vintage_date", "date"])
            self.dataset = (
                dataset.sort_index(axis="columns") if variables is None else dataset
            )
        else:
            self.dataset = pd.DataFrame(
                index=pd.MultiIndex.from_arrays(
                    [[], []], names=["vintage_date", "date"]
                )
            )
        self.dataset.attrs["curation_log"] = {
            "input": self._input_counts.copy(),
            "transformations": {
                name: (" -> ".join(self._recipes.get(name, ())) if stationarise else "")
                or "as published"
                for name in sorted(self._monthly["variable"].unique())
            },
            "revision_rule": "latest release on or before each origin",
            "eligibility_rule": "complete and nonconstant in the minimum window; no imputation",
            "parameters": {
                "as_of": cutoff.isoformat() if cutoff is not None else None,
                "snapshot_freq": snapshot_freq,
                "stationarise": stationarise,
                "min_months": min_months,
                "end_month": str(end) if end is not None else "previous calendar month",
                "variables": list(variables) if variables is not None else None,
                "extend_history": extend_history,
            },
            "output": {
                "origins_considered": len(origins),
                "nonempty_vintages": sum(
                    not window.empty for window in windows.values()
                ),
                "skipped_origins": skipped,
                "rows": len(self.dataset),
                "columns": len(self.dataset.columns),
            },
        }
        self._as_of = cutoff
        return self.dataset

    def iter_vintages(self) -> Iterator[tuple[pd.Timestamp, pd.DataFrame]]:
        """Yield the forecast date and complete model input for each curated vintage."""
        if self.dataset.empty:
            return
        if self._as_of is not None:
            yield self._as_of, self.dataset
        else:
            for vintage, rows in self.dataset.groupby(level="vintage_date", sort=False):
                yield (
                    vintage,
                    rows.droplevel("vintage_date").dropna(axis="columns", how="all"),
                )
