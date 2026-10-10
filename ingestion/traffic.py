"""Traffic files: clean the rows and combine them into one monthly table.

In the Excel files one row = one industrial city + one month + one direction (entry or exit) + vehicle count.
In the clean table one row = one industrial city + one month, with an `entries` and an `exits` column.
"""
import pandas as pd

from .config import WINDOW_END, WINDOW_START
from .excel_utils import norm_ar
from .labels import DIRECTIONS, MONTHS, TRAFFIC_CITIES

# A month gets a warning when entries and exits are more than 30% apart
IMBALANCE_LIMIT = 0.30


def parse_month(value):
    """Turn '<month name> 2026' (Arabic) or a real Excel date into the first day of that month.
    Returns NaT when the value is not a month."""
    if hasattr(value, "year"):  # already a date
        return pd.Timestamp(value.year, value.month, 1)
    words = norm_ar(value).split()
    if len(words) == 2 and words[0] in MONTHS and words[1].isdigit():
        return pd.Timestamp(int(words[1]), MONTHS[words[0]], 1)
    return pd.NaT


def find_problem(row, start, end):
    """Check one source row. Returns the reject reason, or None if the row is fine."""
    if pd.isna(row["city_code"]):
        return "unknown_city"
    if pd.isna(row["month_start"]):
        return "invalid_month"
    if pd.isna(row["movement"]):
        return "invalid_direction"
    if pd.notna(row["count"]) and pd.isna(row["vehicles"]):
        return "invalid_count"  # the cell has text instead of a number
    if pd.isna(row["vehicles"]):
        return "missing_count"
    if row["vehicles"] < 0:
        return "negative_count"
    if row["vehicles"] % 1 != 0:
        return "non_integer_count"
    if row["month_start"] < pd.Timestamp(start) or row["month_start"] > pd.Timestamp(end):
        return "outside_window"
    return None


def clean_traffic(rows, cities, start=WINDOW_START, end=WINDOW_END):
    """Returns (clean table, rejected rows). Bad rows are never dropped silently: they go to the rejects with a reason."""
    rows = rows.copy()

    # translate the Arabic values
    rows["city_code"] = rows["city"].map(lambda city: TRAFFIC_CITIES.get(norm_ar(city)))
    rows["month_start"] = rows["date"].map(parse_month)
    rows["movement"] = rows["direction"].map(lambda d: DIRECTIONS.get(norm_ar(d)))  # entries or exits
    rows["vehicles"] = pd.to_numeric(rows["count"], errors="coerce")

    # check every row
    reasons = []
    for _, row in rows.iterrows():
        reasons.append(find_problem(row, start, end))
    rows["reject_reason"] = reasons
    rejected = rows[rows["reject_reason"].notna()]
    good = rows[rows["reject_reason"].isna()]

    # duplicates: the same city, month and direction twice. Keep the first one.
    is_duplicate = good.duplicated(["city_code", "month_start", "movement"], keep="first")
    duplicates = good[is_duplicate].assign(reject_reason="duplicate_row")
    good = good[~is_duplicate]
    rejects = pd.concat([rejected, duplicates])
    rejects = rejects[["reject_reason", "source_file", "source_row", "city_code", "month_start", "movement", "vehicles"]]

    # put entries and exits of the same city and month on one row
    entries = good[good["movement"] == "entries"][["city_code", "month_start", "vehicles"]]
    entries = entries.rename(columns={"vehicles": "entries"})
    exits = good[good["movement"] == "exits"][["city_code", "month_start", "vehicles"]]
    exits = exits.rename(columns={"vehicles": "exits"})
    clean = good[["city_code", "month_start", "source_file", "layout_version"]].drop_duplicates(["city_code", "month_start"])
    clean = clean.merge(entries, on=["city_code", "month_start"], how="left")
    clean = clean.merge(exits, on=["city_code", "month_start"], how="left")
    clean = clean.merge(cities[["city_code", "city_name", "region_code"]], on="city_code", how="left")
    clean = clean.sort_values(["city_code", "month_start"]).reset_index(drop=True)

    clean["quality_flag"] = add_quality_flags(clean)
    clean["entries"] = clean["entries"].astype("Int64")  # whole numbers, empty stays empty
    clean["exits"] = clean["exits"].astype("Int64")
    clean = clean[["city_code", "city_name", "region_code", "month_start", "entries", "exits",
                   "quality_flag", "source_file", "layout_version"]]
    return clean, rejects


def add_quality_flags(clean):
    """Warnings only. The numbers are never changed."""
    flags = []
    previous = None  # the row before, to compare with
    for row in clean.itertuples():
        problems = []
        if pd.notna(row.entries) and pd.notna(row.exits):
            biggest = max(row.entries, row.exits)
            if biggest > 0 and abs(row.entries - row.exits) / biggest > IMBALANCE_LIMIT:
                problems.append("entry_exit_imbalance")
            if previous is not None and previous.city_code == row.city_code \
                    and previous.entries == row.entries and previous.exits == row.exits:
                problems.append("repeated_previous_month_values")
        flags.append("|".join(problems) if problems else None)
        previous = row
    return flags


def coverage(clean, cities, start=WINDOW_START, end=WINDOW_END):
    """List every city and every month with has_data True or False, so missing months are visible.
    Missing months are reported, never filled."""
    months = pd.date_range(start, end, freq="MS")
    result = []
    for city_code in cities["city_code"]:
        for month in months:
            found = (clean["city_code"] == city_code) & (clean["month_start"] == month)
            result.append({"city_code": city_code, "month_start": month, "has_data": bool(found.any())})
    return pd.DataFrame(result)
