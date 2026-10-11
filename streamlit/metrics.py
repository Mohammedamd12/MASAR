"""Pure calculations for the Masar dashboard (pandas in, pandas out).

No Streamlit and no BigQuery here, so every number can be tested.

Everything works on one "city-month" table: one row per industrial city per month.
`build_city_month()` creates it from whatever the pipeline provides:
  - the dbt mart  fct_city_movement_monthly (city_name, movement_month, total_entries, ...)
  - or the ingestion table traffic_monthly_clean (city_code, month_start, entries, ...)
plus the seeds (city -> region, coordinates), daily weather and event days.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Same rule as the ingestion quality_flag: entries and exits differ by more than 30%
# of the larger one  ->  ratio below 0.70 or above 1/0.70.
IMBALANCE_LIMIT = 0.30
RATIO_LOW = 1 - IMBALANCE_LIMIT
RATIO_HIGH = 1 / (1 - IMBALANCE_LIMIT)
HOT_DAY_C = 40.0
EXPECTED_MONTHS = pd.date_range("2026-01-01", "2026-06-01", freq="MS")

CITY_MONTH_COLUMNS = [
    "city_code", "city_name", "region_code", "region_name", "latitude", "longitude",
    "month_start", "quarter", "entries", "exits", "total_movements", "entry_exit_ratio",
    "in_both_quarters", "quality_flag",
    "avg_temp_c", "max_temp_c", "hot_days", "precipitation_mm", "event_count",
]

# Column names used by the dbt mart -> names used here.
MART_RENAMES = {
    "movement_month": "month_start",
    "total_entries": "entries",
    "total_exits": "exits",
    "total_movement": "total_movements",
}


# --------------------------------------------------------------------------- building
def _short_region(name: str) -> str:
    return str(name).replace(" Region", "").strip()


def build_city_month(
    traffic: pd.DataFrame,
    cities: pd.DataFrame,
    regions: pd.DataFrame,
    weather_daily: pd.DataFrame | None = None,
    event_days: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Combine traffic, seeds, weather and events into one city-month table."""
    t = traffic.rename(columns=MART_RENAMES).copy()
    if "month_start" not in t or "entries" not in t or "exits" not in t:
        raise ValueError("Traffic data needs a month column and entries/exits columns. "
                         f"Found: {list(traffic.columns)}")
    t["month_start"] = pd.to_datetime(t["month_start"]).dt.to_period("M").dt.to_timestamp()

    seed = cities[["city_code", "city_name", "region_code", "latitude", "longitude"]].copy()
    seed["city_name"] = seed["city_name"].str.strip()
    if "city_code" not in t:  # dbt mart has only city_name -> look up the code in the seed
        t["city_name"] = t["city_name"].astype(str).str.strip()
        t = t.merge(seed[["city_code", "city_name"]], on="city_name", how="left")
    t = t.drop(columns=[c for c in ["city_name", "region_code"] if c in t], errors="ignore")
    t = t.merge(seed, on="city_code", how="left")

    reg = regions.copy()
    reg["region_name"] = reg["region_name"].map(_short_region)
    t = t.merge(reg[["region_code", "region_name"]], on="region_code", how="left")

    t["entries"] = pd.to_numeric(t["entries"], errors="coerce").astype("Int64")
    t["exits"] = pd.to_numeric(t["exits"], errors="coerce").astype("Int64")
    t["total_movements"] = (t["entries"].fillna(0) + t["exits"].fillna(0)).astype("Int64")
    t["entry_exit_ratio"] = np.where(t["exits"].fillna(0) > 0,
                                     t["entries"].astype(float) / t["exits"].astype(float), np.nan)
    t["entry_exit_ratio"] = t["entry_exit_ratio"].round(3)
    t["quarter"] = "2026-Q" + t["month_start"].dt.quarter.astype(str)
    quarters = t.groupby("city_code")["quarter"].nunique()
    t["in_both_quarters"] = t["city_code"].map(quarters).eq(2)
    if "quality_flag" not in t:
        t["quality_flag"] = pd.NA

    t = t.merge(monthly_weather(weather_daily), on=["city_code", "month_start"], how="left")
    t = t.merge(monthly_events(event_days), on=["city_code", "month_start"], how="left")
    if event_days is not None:
        t["event_count"] = t["event_count"].fillna(0).astype("Int64")

    for col in CITY_MONTH_COLUMNS:
        if col not in t:
            t[col] = pd.NA
    return t[CITY_MONTH_COLUMNS].sort_values(["region_code", "city_code", "month_start"]).reset_index(drop=True)


def monthly_weather(weather_daily: pd.DataFrame | None) -> pd.DataFrame:
    """Daily Open-Meteo rows -> one row per city per month."""
    cols = ["city_code", "month_start", "avg_temp_c", "max_temp_c", "hot_days", "precipitation_mm"]
    if weather_daily is None or weather_daily.empty:
        return pd.DataFrame(columns=cols).astype({"month_start": "datetime64[ns]"})
    w = weather_daily.copy()
    w["month_start"] = pd.to_datetime(w["weather_date"]).dt.to_period("M").dt.to_timestamp()
    for c in ["temperature_2m_mean", "temperature_2m_max", "precipitation_sum"]:
        w[c] = pd.to_numeric(w.get(c), errors="coerce")
    out = w.groupby(["city_code", "month_start"], as_index=False).agg(
        avg_temp_c=("temperature_2m_mean", "mean"),
        max_temp_c=("temperature_2m_max", "max"),
        hot_days=("temperature_2m_max", lambda s: int((s >= HOT_DAY_C).sum())),
        precipitation_mm=("precipitation_sum", "sum"),
    )
    out["avg_temp_c"] = out["avg_temp_c"].round(1)
    return out


def monthly_events(event_days: pd.DataFrame | None) -> pd.DataFrame:
    """Event days -> number of distinct events per city per month."""
    cols = ["city_code", "month_start", "event_count"]
    if event_days is None or event_days.empty:
        return pd.DataFrame(columns=cols).astype({"month_start": "datetime64[ns]"})
    e = event_days.copy()
    e["month_start"] = pd.to_datetime(e["event_date"]).dt.to_period("M").dt.to_timestamp()
    return (e.groupby(["city_code", "month_start"])["gov_request_number"].nunique()
             .rename("event_count").reset_index())


# --------------------------------------------------------------------------- analysis
def filter_data(df, regions=None, cities=None, months=None) -> pd.DataFrame:
    """Sidebar filters. An empty or None list means 'all'."""
    out = df
    if regions:
        out = out[out["region_code"].isin(regions)]
    if cities:
        out = out[out["city_code"].isin(cities)]
    if months:
        out = out[out["month_start"].isin(pd.to_datetime(months))]
    return out


def kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"entries": 0, "exits": 0, "total": 0, "busiest_city": None,
                "busiest_city_share": None, "busiest_region": None,
                "busiest_region_share": None, "ratio": None, "cities": 0}
    entries, exits = int(df["entries"].sum()), int(df["exits"].sum())
    total = entries + exits
    by_city = df.groupby("city_name")["total_movements"].sum()
    by_region = df.groupby("region_name")["total_movements"].sum()
    return {
        "entries": entries, "exits": exits, "total": total,
        "busiest_city": by_city.idxmax(),
        "busiest_city_share": by_city.max() / total if total else None,
        "busiest_region": by_region.idxmax(),
        "busiest_region_share": by_region.max() / total if total else None,
        "ratio": round(entries / exits, 2) if exits else None,
        "cities": int(df["city_code"].nunique()),
    }


def totals_by(df: pd.DataFrame, level: str) -> pd.DataFrame:
    keys = {"city": ["city_code", "city_name", "region_name"],
            "region": ["region_code", "region_name"]}[level]
    return (df.groupby(keys, as_index=False)[["entries", "exits", "total_movements"]].sum()
              .sort_values("total_movements", ascending=False))


def map_points(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby(["city_code", "city_name", "region_name", "latitude", "longitude"],
                       as_index=False)["total_movements"].sum())


def growth_q1_q2(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Q1 -> Q2 growth on AVERAGE monthly movement (some cities miss months)."""
    m = df.groupby(["city_code", "city_name", "quarter"], as_index=False).agg(
        avg_monthly=("total_movements", "mean"), months=("month_start", "nunique"))
    q1 = m[m.quarter == "2026-Q1"].set_index(["city_code", "city_name"])
    q2 = m[m.quarter == "2026-Q2"].set_index(["city_code", "city_name"])
    both = q1.join(q2, lsuffix="_q1", rsuffix="_q2", how="inner").reset_index()
    both = both.rename(columns={"avg_monthly_q1": "q1_avg_monthly", "avg_monthly_q2": "q2_avg_monthly",
                                "months_q1": "q1_months", "months_q2": "q2_months"})
    both["growth_pct"] = ((both.q2_avg_monthly - both.q1_avg_monthly) / both.q1_avg_monthly * 100).round(1)
    both = both[["city_code", "city_name", "q1_avg_monthly", "q2_avg_monthly",
                 "q1_months", "q2_months", "growth_pct"]].sort_values("growth_pct", ascending=False)

    all_cities = m[["city_code", "city_name"]].drop_duplicates()
    excluded = all_cities[~all_cities.city_code.isin(both.city_code)].copy()
    excluded["reason"] = excluded.city_code.map(
        lambda c: "Only in Q1" if c in q1.index.get_level_values(0) else "Only in Q2")
    return both.reset_index(drop=True), excluded.reset_index(drop=True)


def monthly_trend(df: pd.DataFrame, level: str) -> pd.DataFrame:
    name = {"region": "region_name", "city": "city_name"}[level]
    return df.groupby(["month_start", name], as_index=False)["total_movements"].sum().sort_values("month_start")


def quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """City-months with an unusual entry/exit ratio or a pipeline quality flag."""
    out = df[["city_name", "region_name", "month_start", "entries", "exits",
              "entry_exit_ratio", "quality_flag"]].copy()
    ratio_off = (out.entry_exit_ratio < RATIO_LOW) | (out.entry_exit_ratio > RATIO_HIGH)
    flagged = out[ratio_off | out.quality_flag.notna()].copy()

    def why(r):
        reasons = []
        if pd.notna(r.quality_flag) and str(r.quality_flag).strip():
            reasons.append(str(r.quality_flag).replace("_", " ").replace("|", ", "))
        if pd.notna(r.entry_exit_ratio) and r.entry_exit_ratio > RATIO_HIGH:
            reasons.append("more entries than exits")
        elif pd.notna(r.entry_exit_ratio) and r.entry_exit_ratio < RATIO_LOW:
            reasons.append("more exits than entries")
        return "; ".join(dict.fromkeys(reasons))

    flagged["reason"] = flagged.apply(why, axis=1)
    return flagged.drop(columns="quality_flag").sort_values("month_start")


def missing_months(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (code, name), g in df.groupby(["city_code", "city_name"]):
        present = set(pd.to_datetime(g.month_start))
        absent = [m for m in EXPECTED_MONTHS if m not in present]
        if absent:
            rows.append({"city_code": code, "city_name": name,
                         "missing_months": ", ".join(m.strftime("%b") for m in absent),
                         "months_with_data": 6 - len(absent)})
    return pd.DataFrame(rows, columns=["city_code", "city_name", "missing_months", "months_with_data"])


def monthly_context(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby("month_start", as_index=False)
              .agg(total_movements=("total_movements", "sum"),
                   avg_temp_c=("avg_temp_c", "mean"),
                   hot_days=("hot_days", "max"),
                   event_count=("event_count", "sum"))
              .sort_values("month_start"))


def context_available(df: pd.DataFrame) -> dict:
    return {"weather": bool(pd.to_numeric(df["avg_temp_c"], errors="coerce").notna().any()),
            "events": bool(pd.to_numeric(df["event_count"], errors="coerce").notna().any())}