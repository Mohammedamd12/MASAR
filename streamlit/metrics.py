"""Pure calculations for the Masar dashboard (pandas in, pandas out).

No Streamlit and no BigQuery here, so every number can be tested
(see tests/test_metrics.py).

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

    reg = regions.rename(columns={"region_name": "region_name"}).copy()
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
    """Q1 -> Q2 growth on AVERAGE monthly movement (some cities miss months).

    Returns (cities in both quarters with growth, excluded cities with reason).
    """
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


# --------------------------------------------------------------------------- summary helpers
def month_change(df: pd.DataFrame, month) -> dict | None:
    """Selected month vs the month before, LIKE-FOR-LIKE: only cities with data in both months.

    `df` must not be filtered by month. Returns None when there is no previous month to compare.
    """
    month = pd.Timestamp(month)
    prev = month - pd.DateOffset(months=1)
    cur, pre = df[df.month_start == month], df[df.month_start == prev]
    common = sorted(set(cur.city_code) & set(pre.city_code))
    if not common:
        return None
    c, p = cur[cur.city_code.isin(common)], pre[pre.city_code.isin(common)]

    def pct(a, b):
        return float((a - b) / b * 100) if b else None

    def by(level):
        a = c.groupby(level)["total_movements"].sum()
        b = p.groupby(level)["total_movements"].sum()
        return {key: pct(a[key], b[key]) for key in a.index if key in b.index}

    ratio = lambda d: d.entries.sum() / d.exits.sum() if d.exits.sum() else np.nan  # noqa: E731
    temp_c = pd.to_numeric(c.avg_temp_c, errors="coerce").mean()
    temp_p = pd.to_numeric(p.avg_temp_c, errors="coerce").mean()
    return {
        "prev": prev, "cities": len(common), "cities_now": int(cur.city_code.nunique()),
        "total_pct": pct(c.total_movements.sum(), p.total_movements.sum()),
        "by_city": by("city_name"), "by_region": by("region_name"),
        "ratio_delta": float(ratio(c) - ratio(p)),
        "temp_delta": None if pd.isna(temp_c) or pd.isna(temp_p) else float(temp_c - temp_p),
    }


def insights(view: pd.DataFrame, view_all_months: pd.DataFrame) -> list[dict]:
    """Three plain-language findings for the Operations Manager: volume, growth, data quality.

    Wording points to where to investigate (gate capacity, staffing, traffic management);
    it never claims a cause.
    """
    out = []
    by_city = view.groupby("city_name")["total_movements"].sum().sort_values(ascending=False)
    total = by_city.sum()
    if total:
        top, top_v = by_city.index[0], by_city.iloc[0]
        out.append({"tag": "Volume", "kind": "volume", "value": f"{top_v / total:.0%}",
                    "title": f"{top} carries the most traffic",
                    "body": f"{top_v:,.0f} of {total:,.0f} vehicle movements in scope — "
                            "first candidate for a gate-capacity and staffing review."})

    growth, excluded = growth_q1_q2(view_all_months)
    if growth.empty:
        out.append({"tag": "Growth", "kind": "growth", "value": "—",
                    "title": "Growth not comparable for this selection",
                    "body": "Q1 → Q2 growth needs a city with data in both quarters."})
    else:
        g = growth.iloc[0]
        few = g.q1_months < 3 or g.q2_months < 3
        body = (f"Average monthly movement {g.q1_avg_monthly:,.0f} → {g.q2_avg_monthly:,.0f} "
                f"({int(g.q1_months)} + {int(g.q2_months)} months).")
        low = growth.iloc[-1]
        if len(growth) > 1 and low.growth_pct < 0:
            body += f" Largest drop: {low.city_name} ({low.growth_pct:+.1f}%)."
        if few:
            body += " Fewer than 3 months in a quarter — read with care."
        out.append({"tag": "Fastest growth Q1 → Q2", "kind": "growth", "value": f"{g.growth_pct:+.1f}%",
                    "title": f"{g.city_name} grew fastest", "body": body
                    + (f" {len(excluded)} cities not compared (one quarter only)." if len(excluded) else "")})

    flags = quality_flags(view_all_months)
    if flags.empty:
        out.append({"tag": "Data quality", "kind": "quality", "value": "0",
                    "title": "No data-quality flags in this selection",
                    "body": "Entries and exits stay within 30% of each other in every city-month."})
    else:
        counts = flags.groupby("city_name").size().sort_values(ascending=False)
        worst, n = counts.index[0], int(counts.iloc[0])
        months_with_data = view_all_months[view_all_months.city_name == worst].month_start.nunique()
        out.append({"tag": "Data quality", "kind": "quality", "value": f"{n}/{months_with_data}",
                    "title": f"{worst}: flagged in {n} of {months_with_data} months",
                    "body": f"{len(flags)} flagged city-months in total. Check gate counts before "
                            "reading these months as real changes."})
    return out


def city_profile(view: pd.DataFrame, view_all_months: pd.DataFrame, city_code: str) -> dict:
    """Facts for one industrial city: totals in scope, growth, month coverage and flags."""
    one = view[view.city_code == city_code]
    all_m = view_all_months[view_all_months.city_code == city_code]
    growth, excluded = growth_q1_q2(all_m)
    flags = quality_flags(all_m)
    flagged = set(pd.to_datetime(flags.month_start))
    present = set(pd.to_datetime(all_m.month_start))
    peak = all_m.loc[all_m.total_movements.idxmax()] if not all_m.empty else None
    region_total = view[view.region_name == all_m.region_name.iloc[0]].total_movements.sum() if not all_m.empty else 0
    return {
        "name": all_m.city_name.iloc[0] if not all_m.empty else city_code,
        "region": all_m.region_name.iloc[0] if not all_m.empty else "—",
        "entries": int(one.entries.sum()), "exits": int(one.exits.sum()),
        "total": int(one.total_movements.sum()),
        "region_share": float(one.total_movements.sum() / region_total) if region_total else None,
        "ratio": round(one.entries.sum() / one.exits.sum(), 2) if one.exits.sum() else None,
        "growth": None if growth.empty else growth.iloc[0].to_dict(),
        "growth_reason": None if excluded.empty else excluded.iloc[0].reason,
        "months": [{"month": m, "has_data": m in present, "flagged": m in flagged} for m in EXPECTED_MONTHS],
        "flag_reasons": flags.reason.tolist(),
        "peak": None if peak is None else (pd.Timestamp(peak.month_start), int(peak.total_movements)),
    }