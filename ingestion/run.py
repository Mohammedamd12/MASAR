"""Run the whole data preparation:  python -m ingestion.run [--skip-weather] [--input-dir DIR]

Writes CSV files (UTF-8, ISO dates, English only) to data/processed/ so Airflow can load them into BigQuery.
"""
import argparse
from pathlib import Path

import pandas as pd

from . import config
from .events import clean_events
from .excel_utils import read_workbook
from .labels import EVENT_HEADERS, TRAFFIC_HEADERS
from .seeds import load_cities, load_event_cities, load_event_names, load_regions
from .traffic import clean_traffic, coverage
from .weather import collect_weather


def write_csv(df: pd.DataFrame, path: Path):
    df.to_csv(path, index=False, date_format="%Y-%m-%d", encoding="utf-8")
    print(f"  wrote {path.name}: {len(df)} rows")


def read_all(files, headers, min_found):
    """Read many Excel files. Returns (all rows together, sheet log)."""
    tables = []
    logs = []
    for file in files:
        rows, log = read_workbook(file, headers, min_found)
        if len(rows) > 0:
            tables.append(rows)
        logs += log
    if not tables:
        raise SystemExit("No usable sheets found. Check --input-dir and the file names.")
    return pd.concat(tables, ignore_index=True), logs


def main(input_dir: Path, out_dir: Path, skip_weather: bool):
    out_dir.mkdir(parents=True, exist_ok=True)
    cities, regions, event_cities = load_cities(), load_regions(), load_event_cities()
    assert len(cities) == 12 and len(regions) == 5, "seeds must hold 12 cities and 5 regions"

    print("Traffic")
    traffic_files = sorted(input_dir.glob(config.TRAFFIC_GLOB))
    rows, logs = read_all(traffic_files, TRAFFIC_HEADERS, 4)
    clean, rejects = clean_traffic(rows, cities)
    write_csv(clean, out_dir / "traffic_monthly_clean.csv")
    write_csv(rejects, out_dir / "traffic_rejects.csv")
    write_csv(coverage(clean, cities), out_dir / "traffic_coverage.csv")
    write_csv(pd.DataFrame(logs), out_dir / "traffic_sheet_log.csv")
    print(f"  cities with data: {clean.city_code.nunique()} of {len(cities)}; "
          f"flagged months: {int(clean.quality_flag.notna().sum())}")

    print("Events")
    event_files = sorted(input_dir.glob(config.EVENTS_GLOB))
    rows, logs = read_all(event_files, EVENT_HEADERS, 5)
    events, days, rejects = clean_events(rows, cities, event_cities, load_event_names())
    write_csv(events, out_dir / "events_clean.csv")
    write_csv(days, out_dir / "event_days.csv")
    write_csv(rejects, out_dir / "events_rejects.csv")
    write_csv(pd.DataFrame(logs), out_dir / "events_sheet_log.csv")
    print("  relevance:", events["relevance"].value_counts().to_dict())
    no_city = int((events["event_city"] == "Unmapped").sum())
    if no_city:
        print(f"  WARNING: {no_city} events have a city that is not in labels.py")
    no_name = int((events["event_name"] == "Not translated").sum())
    if no_name:
        print(f"  WARNING: {no_name} events have no English name in event_names_en.csv")

    if skip_weather:
        print("Weather skipped (--skip-weather)")
    else:
        print("Weather (Open-Meteo)")
        weather = collect_weather(cities)
        write_csv(weather, out_dir / "weather_daily.csv")
        print(f"  days without weather: {int(weather['weather_missing'].sum())}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=config.ROOT, help="folder with the .xlsx files")
    parser.add_argument("--out-dir", type=Path, default=config.OUT_DIR)
    parser.add_argument("--skip-weather", action="store_true", help="do not call the Open-Meteo API")
    args = parser.parse_args()
    main(args.input_dir, args.out_dir, args.skip_weather)
