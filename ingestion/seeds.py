"""Load the small seed tables (12 industrial cities, 5 regions, event city mapping)."""
import pandas as pd

from .config import CITIES_SEED, EVENT_CITIES_SEED, EVENT_NAMES_FILE, REGIONS_SEED


def load_cities() -> pd.DataFrame:
    return pd.read_csv(CITIES_SEED)


def load_regions() -> pd.DataFrame:
    return pd.read_csv(REGIONS_SEED)


def load_event_cities() -> pd.DataFrame:
    return pd.read_csv(EVENT_CITIES_SEED, keep_default_na=False)


def load_event_names() -> dict:
    """gov_request_number -> English event name"""
    table = pd.read_csv(EVENT_NAMES_FILE)
    return dict(zip(table["gov_request_number"], table["event_name_en"]))
