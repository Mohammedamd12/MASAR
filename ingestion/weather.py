"""Open-Meteo historical weather: one daily table for every industrial city."""
import json
import time

import numpy as np
import pandas as pd
import requests

from .config import OPEN_METEO_URL, RAW_DIR, TIMEZONE, WINDOW_END, WINDOW_START

DAILY_VARIABLES = [
    "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
    "precipitation_sum", "wind_speed_10m_max", "wind_gusts_10m_max",
]

# Values outside these limits are treated as invalid and become empty (NULL)
VALID_RANGES = {
    "temperature_2m_max": (-30, 60), "temperature_2m_min": (-30, 60), "temperature_2m_mean": (-30, 60),
    "precipitation_sum": (0, 500), "wind_speed_10m_max": (0, 200), "wind_gusts_10m_max": (0, 300),
}


def fetch_city(latitude, longitude, start, end, retries=5, session=None) -> dict:
    """Call the API for one city. Retries when the server is busy (429) or has a temporary error (5xx)."""
    session = session or requests
    params = {"latitude": latitude, "longitude": longitude, "start_date": start, "end_date": end,
              "daily": ",".join(DAILY_VARIABLES), "timezone": TIMEZONE}
    for attempt in range(retries):
        response = session.get(OPEN_METEO_URL, params=params, timeout=60)
        if response.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** attempt * 2)
            continue
        response.raise_for_status()
        return response.json()
    response.raise_for_status()
    return response.json()


def to_frame(city_code, payload, start, end) -> pd.DataFrame:
    """API answer -> one row per day. Missing or impossible values stay empty and are flagged, never invented."""
    daily = pd.DataFrame(payload.get("daily", {}))
    if daily.empty:
        daily = pd.DataFrame(columns=["time"] + DAILY_VARIABLES)
    daily["weather_date"] = pd.to_datetime(daily["time"])

    all_days = pd.DataFrame({"weather_date": pd.date_range(start, end)})  # complete calendar, no gaps
    df = all_days.merge(daily.drop(columns=["time"]), on="weather_date", how="left")
    for column in DAILY_VARIABLES:
        if column not in df:
            df[column] = np.nan
        df[column] = pd.to_numeric(df[column], errors="coerce")
        low, high = VALID_RANGES[column]
        df.loc[(df[column] < low) | (df[column] > high), column] = np.nan
    df.insert(0, "city_code", city_code)
    df["weather_missing"] = df["temperature_2m_mean"].isna()
    return df


def collect_weather(cities: pd.DataFrame, start=WINDOW_START, end=WINDOW_END, save_raw=True) -> pd.DataFrame:
    """Download daily weather for every city in the seed table and stack the results."""
    frames = []
    if save_raw:
        (RAW_DIR / "open_meteo").mkdir(parents=True, exist_ok=True)
    with requests.Session() as session:
        for city in cities.itertuples():
            payload = fetch_city(city.latitude, city.longitude, start, end, session=session)
            if save_raw:  # keep the original answer so the run can be checked later
                (RAW_DIR / "open_meteo" / f"{city.city_code}.json").write_text(json.dumps(payload))
            frames.append(to_frame(city.city_code, payload, start, end))
            time.sleep(0.5)  # be polite to the free API
    return pd.concat(frames, ignore_index=True)
