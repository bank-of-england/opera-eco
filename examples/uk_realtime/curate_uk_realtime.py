"""Build six-year panels ending in the month before each UK archive vintage."""

from collections.abc import Mapping, Sequence
from pathlib import Path

import pandas as pd

if __package__:
    from .curator import Curator
else:
    from curator import Curator

ARCHIVE_URL = "https://raw.githubusercontent.com/aeturrell/real-time-data/main/realtimedata.parquet"
UK_VARIABLES = (
    "agents_b2b_services_prices",
    "agents_business_services_incl_exports",
    "agents_capacity_utilisation",
    "agents_construction_output",
    "agents_consumer_goods_prices",
    "agents_consumer_goods_values",
    "agents_consumer_services_prices",
    "agents_consumer_services_values",
    "agents_credit_availability_large",
    "agents_credit_availability_medium",
    "agents_credit_availability_small",
    "agents_employment_intentions",
    "agents_housing",
    "agents_imported_goods_costs",
    "agents_investment_intentions",
    "agents_labour_costs",
    "agents_manufacturers_prices",
    "agents_manufacturing_exports",
    "agents_manufacturing_incl_exports",
    "agents_material_costs",
    "agents_profit_margins",
    "agents_recruitment_difficulties",
    "agents_services_exports",
    "average_weekly_earnings",
    "claimant_count",
    "construction_growth_mom",
    "core_cpi_inflation",
    "cpi_inflation",
    "cpih_inflation",
    "dmp_cpi_exp_1y",
    "dmp_cpi_exp_3y",
    "dmp_employment_expected_mean",
    "dmp_employment_realised_mean",
    "dmp_overall_uncertainty_high",
    "dmp_overall_uncertainty_very_high",
    "dmp_price_expected_mean",
    "dmp_price_realised_mean",
    "dmp_recruitment_much_harder",
    "dmp_sales_expected_mean",
    "dmp_sales_realised_mean",
    "dmp_uncertainty_employment",
    "dmp_uncertainty_price",
    "dmp_uncertainty_sales",
    "dmp_uncertainty_unit_cost",
    "dmp_uncertainty_wage",
    "dmp_unit_cost_expected_mean",
    "dmp_unit_cost_realised_mean",
    "dmp_wage_expected_mean",
    "dmp_wage_realised_mean",
    "employment",
    "employment_rate",
    "exports",
    "exports_real",
    "gva_monthly_growth_mom",
    "hours_worked",
    "imports",
    "imports_real",
    "inactivity_rate",
    "manufacturing_growth_mom",
    "ppi_input",
    "ppi_output",
    "private_regular_pay_growth",
    "production_growth_mom",
    "public_sector_net_borrowing",
    "regular_pay_growth",
    "retail_sales_growth_mom",
    "rpi",
    "services_cpi_inflation",
    "services_growth_mom",
    "trade_balance",
    "unemployment_rate",
    "vacancies",
)
UK_TRANSFORMATIONS = {
    **dict.fromkeys(
        ("claimant_count", "public_sector_net_borrowing", "trade_balance"), ("diff",)
    ),
    **dict.fromkeys(
        (
            "average_weekly_earnings",
            "employment",
            "exports",
            "exports_real",
            "hours_worked",
            "imports",
            "imports_real",
            "ppi_input",
            "ppi_output",
            "rpi",
            "vacancies",
        ),
        ("log diff",),
    ),
}


def load_uk_realtime(source: str | Path = ARCHIVE_URL) -> pd.DataFrame:
    """Return raw publications and revisions from the archive."""
    return pd.read_parquet(source)


def uk_curator(
    raw: pd.DataFrame,
    *,
    variables: Sequence[str] = UK_VARIABLES,
    transformations: Mapping[str, Sequence[str]] = UK_TRANSFORMATIONS,
) -> Curator:
    """Keep the listed monthly series and apply recipes to their published values."""
    is_monthly = raw["frequency"].eq("M")
    monthly = raw.loc[is_monthly & raw["short_name"].isin(variables)]
    identifiers = monthly.groupby("short_name", observed=True)["series_id"].nunique()
    if not identifiers.eq(1).all():
        raise ValueError(
            "Each selected UK series name must have exactly one identifier."
        )
    names = set(monthly["short_name"])
    recipes = {name: steps for name, steps in transformations.items() if name in names}
    releases = monthly.loc[
        :, ["short_name", "reference_period", "vintage_date", "value"]
    ].rename(columns={"short_name": "variable", "reference_period": "date"})
    monthly_count = int(is_monthly.sum())
    source_counts = {
        "raw_rows": len(raw),
        "non_monthly_rows_removed": len(raw) - monthly_count,
        "unselected_monthly_rows_removed": monthly_count - len(monthly),
        "retained_monthly_rows": len(monthly),
    }
    return Curator(releases, transformations=recipes, source_counts=source_counts)


def curate_uk_data(
    source: str | Path = ARCHIVE_URL, *, snapshot_freq: str | None = "ME"
) -> pd.DataFrame:
    """Return one row per vintage, reference month and eligible UK series."""
    curator = uk_curator(
        load_uk_realtime(source),
        variables=UK_VARIABLES,
        transformations=UK_TRANSFORMATIONS,
    )
    panels = curator.curate(
        as_of=None,
        snapshot_freq=snapshot_freq,
        stationarise=True,
        min_months=72,
        end_month=None,
        variables=None,
        extend_history=False,
    )
    outturns = (
        panels.reset_index()
        .melt(id_vars=["vintage_date", "date"], var_name="variable")
        .dropna(subset=["value"], ignore_index=True)
        .assign(frequency="M", metric="levels")
    )
    outturns.attrs["curation_log"] = curator.log
    return outturns
