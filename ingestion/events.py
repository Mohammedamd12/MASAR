"""Government events: clean the rows, translate to English, remove duplicates, and decide which industrial cities each event matters to.

In the Excel files one row = one approved event request, identified by the government request number (GOV-2026-0005 style).
The Q1 and Q2 files overlap (Q2 repeats many Q1 events), so duplicates are found with that number.
The English event names come from ingestion/event_names_en.csv, because the Excel files only have Arabic names.
"""
import pandas as pd

from .config import WINDOW_END, WINDOW_START
from .excel_utils import norm_ar
from .labels import EVENT_CITIES, EVENT_TYPES, VENUE_TYPES

NOT_FOUND = "Unmapped"


def translate(values, table):
    """Arabic value -> English value. Anything we do not know becomes 'Unmapped'."""
    return values.map(lambda value: table.get(norm_ar(value), NOT_FOUND) if pd.notna(value) else NOT_FOUND)


def find_problem(row, start, end):
    """Check one source row. Returns the reject reason, or None if the row is fine."""
    if pd.isna(row["gov_request_number"]) or row["gov_request_number"] == "":
        return "missing_request_number"
    if pd.isna(row["start_date"]):
        return "invalid_start_date"
    if row["end_date"] < row["start_date"]:
        return "end_before_start"
    if row["end_date"] < pd.Timestamp(start) or row["start_date"] > pd.Timestamp(end):
        return "outside_window"
    return None


def clean_events(rows, cities, event_cities, event_names, start=WINDOW_START, end=WINDOW_END):
    """Returns (events_clean, event_days, rejects)."""
    df = rows.copy()
    if "attendance" not in df:  # only the Q1 file has this column
        df["attendance"] = pd.NA
    df = df.rename(columns={"request_number": "gov_request_number"})
    df["gov_request_number"] = df["gov_request_number"].astype("string").str.strip().str.upper()
    df["start_date"] = pd.to_datetime(df["start"], errors="coerce").dt.normalize()
    df["end_date"] = pd.to_datetime(df["end"], errors="coerce").dt.normalize()
    df["end_date"] = df["end_date"].fillna(df["start_date"])  # no end date: the event is one day
    df["attendance"] = pd.to_numeric(df["attendance"], errors="coerce")

    # step 1: reject rows we cannot use
    reasons = []
    for _, row in df.iterrows():
        reasons.append(find_problem(row, start, end))
    df["reject_reason"] = reasons
    rejected = df[df["reject_reason"].notna()]
    df = df[df["reject_reason"].isna()]

    # step 2: duplicates = same government request number. Keep the copy that has attendance.
    df = df.sort_values("attendance", na_position="last", kind="stable")
    is_duplicate = df.duplicated("gov_request_number", keep="first")
    duplicates = df[is_duplicate].assign(reject_reason="duplicate_request_number")
    df = df[~is_duplicate].copy()
    rejects = pd.concat([rejected, duplicates])
    rejects = rejects[["reject_reason", "gov_request_number", "start_date", "end_date", "source_file", "source_row"]]

    # step 3: translate to English
    df["event_name"] = df["gov_request_number"].map(event_names).fillna("Not translated")
    df["event_type"] = translate(df["event_type"], EVENT_TYPES)
    df["venue_type"] = translate(df["venue_type"], VENUE_TYPES)
    df["event_city"] = translate(df["city"], EVENT_CITIES)
    df["duration_days"] = (df["end_date"] - df["start_date"]).dt.days + 1

    # step 4: city relevance rule
    #   city   = the event is in the city of an industrial city -> only that industrial city
    #   region = same region as industrial cities, other city   -> every industrial city of that region
    #   none   = any other region
    rules = {}  # event city -> (region code, industrial city codes)
    for rule in event_cities.itertuples():
        rules[rule.event_city] = (rule.region_code, rule.industrial_city_codes)
    cities_in_region = {}  # region code -> list of industrial city codes
    for city in cities.itertuples():
        cities_in_region.setdefault(city.region_code, []).append(city.city_code)

    relevance_list = []
    region_list = []
    codes_list = []
    for event_city in df["event_city"]:
        if event_city not in rules:
            relevance, region_code, codes = "none", "", []
        else:
            region_code, city_codes = rules[event_city]
            if city_codes != "":
                relevance, codes = "city", city_codes.split("|")
            elif region_code in cities_in_region:
                relevance, codes = "region", cities_in_region[region_code]
            else:
                relevance, codes = "none", []
        relevance_list.append(relevance)
        region_list.append(region_code)
        codes_list.append(codes)
    df["relevance"] = relevance_list
    df["region_code"] = region_list
    df["industrial_city_codes"] = ["|".join(codes) for codes in codes_list]

    # step 5: one row per event + industrial city + day (used later for an "is event day" feature)
    days = []
    for number, codes, first_day, last_day in zip(df["gov_request_number"], codes_list, df["start_date"], df["end_date"]):
        first_day = max(first_day, pd.Timestamp(start))  # only count days inside Jan-Jun 2026
        last_day = min(last_day, pd.Timestamp(end))
        for day in pd.date_range(first_day, last_day):
            for code in codes:
                days.append({"gov_request_number": number, "city_code": code, "event_date": day})
    event_days = pd.DataFrame(days, columns=["gov_request_number", "city_code", "event_date"])
    event_days = event_days.merge(df[["gov_request_number", "relevance"]], on="gov_request_number")

    clean = df[["gov_request_number", "event_name", "event_type", "venue_type", "event_city",
                "start_date", "end_date", "duration_days", "attendance", "relevance",
                "region_code", "industrial_city_codes", "source_file", "source_row"]]
    clean = clean.sort_values(["start_date", "gov_request_number"]).reset_index(drop=True)
    return clean, event_days, rejects
