"""Tests for the data preparation. Run from the project root with:  python -m pytest -v

The tests build tiny Excel files on the fly. Arabic text is taken from ingestion/labels.py,
so this file contains no Arabic script either.
"""
import pandas as pd

from ingestion import config, labels
from ingestion.events import clean_events
from ingestion.excel_utils import read_workbook
from ingestion.seeds import load_cities, load_event_cities, load_event_names, load_regions
from ingestion.traffic import clean_traffic, coverage
from ingestion.weather import to_frame


# ---------- helpers: turn English names back into the Arabic text the real files contain ----------
def header(table, english):
    return sorted(table[english])[0]


def key_for(table, value):
    return [k for k, v in table.items() if v == value][0]


def month_text(number):
    return key_for(labels.MONTHS, number) + " 2026"


def write_excel(path, df, title_rows=0):
    """Write df with `title_rows` empty rows above the header, like the real files."""
    with pd.ExcelWriter(path) as writer:
        df.to_excel(writer, index=False, startrow=title_rows)


def traffic_frame(rows, order, extra_note_column=False):
    """rows: (city_code, month_number, 'entries'|'exits', count). order: list of English column names."""
    data = {
        "region": [""] * len(rows),
        "city": [key_for(labels.TRAFFIC_CITIES, r[0]) for r in rows],
        "direction": [key_for(labels.DIRECTIONS, r[2]) for r in rows],
        "date": [month_text(r[1]) if isinstance(r[1], int) else r[1] for r in rows],
        "count": [r[3] for r in rows],
    }
    df = pd.DataFrame({header(labels.TRAFFIC_HEADERS, c): data[c] for c in order})
    if extra_note_column:
        df["note"] = None
    return df


def read_traffic_file(path):
    return read_workbook(path, labels.TRAFFIC_HEADERS, 4)


def read_events_file(path):
    return read_workbook(path, labels.EVENT_HEADERS, 5)


# ---------- seeds ----------
def test_seeds_have_12_cities_5_regions_and_valid_coordinates():
    cities, regions = load_cities(), load_regions()
    assert len(cities) == 12 and len(regions) == 5
    assert cities["city_code"].is_unique
    assert set(cities["region_code"]) == set(regions["region_code"])
    assert cities["latitude"].between(16, 33).all() and cities["longitude"].between(34, 56).all()


def test_event_city_rules_only_point_to_real_industrial_cities():
    codes = set(load_cities()["city_code"])
    for value in load_event_cities()["industrial_city_codes"]:
        if value:
            assert set(value.split("|")) <= codes


def test_traffic_labels_cover_all_12_cities():
    assert set(labels.TRAFFIC_CITIES.values()) == set(load_cities()["city_code"])


# ---------- traffic ----------
def test_traffic_two_layouts_and_bad_rows(tmp_path):
    cities = load_cities()
    a = traffic_frame([("JED", 1, "entries", 10), ("JED", 1, "exits", 8),
                       ("TAB", 2, "entries", 20), ("TAB", 2, "exits", 18),
                       ("TAB", 2, "exits", 18),                       # duplicate
                       ("JED", 3, "entries", -5),                     # negative
                       ("JED", 4, "entries", "abc"),                  # text instead of number
                       ("JED", "garbage", "entries", 5),              # bad month
                       ("JED", 5, "entries", 7)],                     # valid, but has no matching exit
                      order=["region", "city", "direction", "date", "count"], extra_note_column=True)
    b = traffic_frame([("HSA", 4, "entries", 30), ("HSA", 4, "exits", 25)],
                      order=["city", "region", "date", "direction", "count"])  # different column order
    write_excel(tmp_path / "Traffic (4).xlsx", a, title_rows=1)
    write_excel(tmp_path / "Traffic (3).xlsx", b, title_rows=0)

    parts = [read_traffic_file(tmp_path / f)[0] for f in ("Traffic (3).xlsx", "Traffic (4).xlsx")]
    rows = pd.concat(parts, ignore_index=True)
    assert rows["layout_version"].nunique() == 2
    assert set(rows["source_file"]) == {"Traffic (3).xlsx", "Traffic (4).xlsx"}
    assert set(rows["layout_version"]) == {"5 columns, header on row 1", "6 columns, header on row 2"}

    clean, rejects = clean_traffic(rows, cities)
    assert set(rejects["reject_reason"]) == {"duplicate_row", "negative_count", "invalid_count", "invalid_month"}
    jed_jan = clean[(clean.city_code == "JED") & (clean.month_start == "2026-01-01")].iloc[0]
    assert (jed_jan.entries, jed_jan.exits) == (10, 8)
    jed_may = clean[(clean.city_code == "JED") & (clean.month_start == "2026-05-01")].iloc[0]
    assert jed_may.entries == 7 and pd.isna(jed_may.exits)  # a missing side stays empty, not 0
    assert len(clean) == 4


def test_traffic_unknown_city_and_outside_window(tmp_path):
    cities = load_cities()
    df = traffic_frame([("JED", 1, "entries", 1), ("JED", 1, "exits", 1)],
                       order=["region", "city", "direction", "date", "count"])
    df.loc[0, header(labels.TRAFFIC_HEADERS, "city")] = "Atlantis"
    df.loc[1, header(labels.TRAFFIC_HEADERS, "date")] = key_for(labels.MONTHS, 1) + " 2027"
    write_excel(tmp_path / "Traffic_9.xlsx", df, title_rows=1)
    rows, _ = read_traffic_file(tmp_path / "Traffic_9.xlsx")
    clean, rejects = clean_traffic(rows, cities)
    assert len(clean) == 0
    assert set(rejects["reject_reason"]) == {"unknown_city", "outside_window"}


def test_traffic_coverage_shows_missing_months():
    cities = load_cities()
    clean = pd.DataFrame({"city_code": ["JED"], "month_start": [pd.Timestamp("2026-01-01")]})
    grid = coverage(clean, cities)
    assert len(grid) == 12 * 6
    assert grid.has_data.sum() == 1


# ---------- events ----------
NAMES = {"GOV-1": "Test event one", "GOV-2": "Test event two"}  # GOV-3 has no English name on purpose

def events_frame(rows, with_attendance):
    """rows: (request_number, start, end, english_city, attendance)."""
    h = labels.EVENT_HEADERS
    data = {
        header(h, "entity"): ["x"] * len(rows),
        header(h, "event_type"): [key_for(labels.EVENT_TYPES, "Workshop")] * len(rows),
        header(h, "title"): ["t"] * len(rows),
        header(h, "start"): [r[1] for r in rows],
        header(h, "end"): [r[2] for r in rows],
        sorted(h["venue_type"])[0 if with_attendance else 1]: [key_for(labels.VENUE_TYPES, "Hotels")] * len(rows),
        header(h, "venue_name"): ["v"] * len(rows),
        header(h, "city"): [key_for(labels.EVENT_CITIES, r[3]) for r in rows],
        header(h, "request_number"): [r[0] for r in rows],
    }
    if with_attendance:
        data[header(h, "attendance")] = [r[4] for r in rows]
    return pd.DataFrame(data)


def test_events_dedupe_relevance_and_rejects(tmp_path):
    cities, event_cities = load_cities(), load_event_cities()
    q1 = events_frame([("GOV-1", "2026-02-01", "2026-02-03", "Riyadh", 40),
                       ("GOV-2", "2026-03-01", "2026-03-02", "Khobar", 10)], with_attendance=True)
    q2 = events_frame([("GOV-1", "2026-02-01", "2026-02-03", "Riyadh", None),   # repeated from Q1
                       ("GOV-3", "2026-04-01", "2026-04-01", "Madinah", None),  # outside our regions
                       ("GOV-4", "2025-01-01", "2025-01-02", "Jeddah", None),   # before the window
                       ("GOV-5", "2026-05-05", "2026-05-01", "Jeddah", None)],  # ends before it starts
                      with_attendance=False)
    write_excel(tmp_path / "Public Sector Events Q1 2026.xlsx", q1)
    write_excel(tmp_path / "Public_Sector_Events_Q2_2026.xlsx", q2)
    raw = pd.concat([read_events_file(tmp_path / f)[0] for f in
                     ("Public Sector Events Q1 2026.xlsx", "Public_Sector_Events_Q2_2026.xlsx")], ignore_index=True)

    clean, days, rejects = clean_events(raw, cities, event_cities, NAMES)
    assert list(clean.gov_request_number) == ["GOV-1", "GOV-2", "GOV-3"]
    by_id = clean.set_index("gov_request_number")
    assert by_id.loc["GOV-1", "relevance"] == "city" and by_id.loc["GOV-1", "industrial_city_codes"] == "RUH2|RUH3"
    assert by_id.loc["GOV-1", "attendance"] == 40  # the Q1 copy (with attendance) was kept
    assert by_id.loc["GOV-2", "relevance"] == "region"  # Khobar -> every Eastern industrial city
    assert by_id.loc["GOV-2", "industrial_city_codes"] == "DMM1|DMM2|HSA|HFR"
    assert by_id.loc["GOV-3", "relevance"] == "none"
    assert by_id.loc["GOV-1", "event_name"] == "Test event one"
    assert by_id.loc["GOV-3", "event_name"] == "Not translated"  # no English name in the lookup
    assert set(rejects["reject_reason"]) == {"duplicate_request_number", "outside_window", "end_before_start"}
    assert len(days[days.gov_request_number == "GOV-1"]) == 3 * 2   # 3 days x 2 cities
    assert len(days[days.gov_request_number == "GOV-2"]) == 2 * 4   # 2 days x 4 cities
    assert "GOV-3" not in set(days.gov_request_number)


def test_events_unknown_city_is_kept_as_unmapped(tmp_path):
    q1 = events_frame([("GOV-1", "2026-02-01", "2026-02-01", "Riyadh", 5)], with_attendance=True)
    q1[header(labels.EVENT_HEADERS, "city")] = "Atlantis"
    write_excel(tmp_path / "Public_Sector_Events_Q1.xlsx", q1)
    raw, _ = read_events_file(tmp_path / "Public_Sector_Events_Q1.xlsx")
    clean, days, _ = clean_events(raw, load_cities(), load_event_cities(), NAMES)
    assert clean.event_city.iloc[0] == "Unmapped" and clean.relevance.iloc[0] == "none" and days.empty


# ---------- weather ----------
def test_weather_complete_calendar_and_invalid_values():
    payload = {"daily": {"time": ["2026-01-01", "2026-01-03"],
                         "temperature_2m_max": [20, 99], "temperature_2m_min": [10, 11],
                         "temperature_2m_mean": [15, None], "precipitation_sum": [0, 1],
                         "wind_speed_10m_max": [5, 6], "wind_gusts_10m_max": [9, 10]}}
    df = to_frame("RUH2", payload, "2026-01-01", "2026-01-03")
    assert len(df) == 3                                         # Jan 2 is missing in the answer but still has a row
    assert df.weather_missing.tolist() == [False, True, True]  # missing day and empty mean are flagged
    assert pd.isna(df.loc[2, "temperature_2m_max"])            # 99 C is impossible -> empty, not guessed


def test_weather_empty_answer_still_gives_full_calendar():
    df = to_frame("RUH2", {}, "2026-01-01", "2026-01-05")
    assert len(df) == 5 and df.weather_missing.all()


# ---------- the real files (only runs when they are next to the project) ----------
def test_real_files_end_to_end(tmp_path):
    from ingestion.run import main
    if not list(config.ROOT.glob(config.TRAFFIC_GLOB)) or not list(config.ROOT.glob(config.EVENTS_GLOB)):
        return  # real Excel files are not in the project folder; nothing to check
    main(config.ROOT, tmp_path, skip_weather=True)
    traffic = pd.read_csv(tmp_path / "traffic_monthly_clean.csv")
    events = pd.read_csv(tmp_path / "events_clean.csv")
    assert traffic.city_code.nunique() == 12
    assert not traffic.duplicated(["city_code", "month_start"]).any()
    assert not events.gov_request_number.duplicated().any()
    assert (events.event_city != "Unmapped").all()
    assert (events.event_name != "Not translated").all()  # every event has an English name
    assert len(load_event_names()) >= len(events)
