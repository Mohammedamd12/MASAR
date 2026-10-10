"""Settings used by every step of the data preparation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Seed files (small tables we maintain by hand, loaded by `dbt seed`)
SEEDS_DIR = ROOT / "dbt" / "seeds"
CITIES_SEED = SEEDS_DIR / "industrial_cities.csv"
REGIONS_SEED = SEEDS_DIR / "regions.csv"
EVENT_CITIES_SEED = SEEDS_DIR / "event_cities.csv"

# English event names (the Excel files only have Arabic names), one row per government request number
EVENT_NAMES_FILE = ROOT / "ingestion" / "event_names_en.csv"

# Where things are read from and written to
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed"

# File name patterns (work with "Traffic_3.xlsx" and "Traffic (3).xlsx")
TRAFFIC_GLOB = "Traffic*.xlsx"
EVENTS_GLOB = "Public*Events*.xlsx"

# We only analyse January to June 2026
WINDOW_START = "2026-01-01"
WINDOW_END = "2026-06-30"

# Open-Meteo historical weather API
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
TIMEZONE = "Asia/Riyadh"
