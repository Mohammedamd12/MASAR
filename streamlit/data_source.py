"""Where the dashboard gets its data.

MASAR_DATA_SOURCE=bigquery  -> dbt mart + raw weather/event tables in BigQuery (final)
MASAR_DATA_SOURCE=local     -> CSV files written by `python -m ingestion.run` in data/processed
MASAR_DATA_SOURCE=auto      -> BigQuery if it works, else local files, else the snapshot (default)

City -> region and coordinates always come from the dbt seeds (dbt/seeds/*.csv).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import metrics

HERE = Path(__file__).resolve().parent
PROJECT_DIR = Path(os.environ.get("MASAR_PROJECT_DIR", HERE.parent))
SEEDS_DIR = PROJECT_DIR / "dbt" / "seeds"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
SNAPSHOT = HERE / "snapshot" / "city_month_snapshot.csv"
BUNDLED_SEEDS = HERE / "snapshot"

GCP_PROJECT = os.environ.get("MASAR_GCP_PROJECT", "saudi-industrial-mobility")
MART_TABLE = os.environ.get("MASAR_BQ_MART",
                            f"{GCP_PROJECT}.masar_staging.fct_city_movement_monthly")
RAW_DATASET = os.environ.get("MASAR_BQ_RAW_DATASET", f"{GCP_PROJECT}.masar_raw")


@dataclass
class LoadResult:
    data: pd.DataFrame | None
    source: str                      # bigquery | local | snapshot
    label: str                       # shown to the user
    updated: str | None = None       # "data last updated"
    notes: list[str] = field(default_factory=list)
    error: str | None = None


def _fmt_time(ts) -> str | None:
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        ts = datetime.fromtimestamp(ts, tz=timezone.utc)
    return pd.Timestamp(ts).tz_convert("Asia/Riyadh").strftime("%d %b %Y, %H:%M")


def load_seeds() -> tuple[pd.DataFrame, pd.DataFrame]:
    """dbt seeds from the repo; the bundled copy is a fallback."""
    folder = SEEDS_DIR if (SEEDS_DIR / "industrial_cities.csv").exists() else BUNDLED_SEEDS
    return (pd.read_csv(folder / "industrial_cities.csv"),
            pd.read_csv(folder / "regions.csv"))

def _bq_client():
    """Use the Streamlit Cloud secret if present, otherwise local gcloud credentials."""
    from google.cloud import bigquery
    try:
        import streamlit as st
        info = st.secrets.get("gcp_service_account")
    except Exception:  # no secrets file locally / in Docker
        info = None
    if info:
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_info(dict(info))
        return bigquery.Client(project=GCP_PROJECT, credentials=creds)
    return bigquery.Client(project=GCP_PROJECT)

# --------------------------------------------------------------------------- BigQuery
def load_bigquery() -> LoadResult:
    label = f"BigQuery · {MART_TABLE}"
    try:
        from google.cloud import bigquery
    except ImportError:
        return LoadResult(None, "bigquery", label, error="google-cloud-bigquery is not installed.")
    try:
        #client = bigquery.Client(project=GCP_PROJECT)
        client = _bq_client()
        mart = client.query(f"SELECT * FROM `{MART_TABLE}`").to_dataframe()
        updated = _fmt_time(client.get_table(MART_TABLE).modified)
    except Exception as exc:
        return LoadResult(
            None,
            "bigquery",
            label,
            error=f"Could not read the mart ({type(exc).__name__}): {exc!r}",
    )
    if mart.empty:
        return LoadResult(None, "bigquery", label, error="The mart returned no rows.")

    notes = []

    def optional(table: str, sql: str):
        try:
            return client.query(sql).to_dataframe()
        except Exception:  # noqa: BLE001
            notes.append(f"{table} not available yet")
            return None

    flags = optional("traffic quality flags",
                     f"SELECT city_code, month_start, quality_flag FROM `{RAW_DATASET}.traffic_monthly`")
    weather = optional("weather", f"SELECT city_code, weather_date, temperature_2m_mean, "
                                  f"temperature_2m_max, precipitation_sum FROM `{RAW_DATASET}.weather_daily`")
    events = optional("events", f"SELECT gov_request_number, city_code, event_date "
                                f"FROM `{RAW_DATASET}.event_days`")
    cities, regions = load_seeds()
    data = metrics.build_city_month(mart, cities, regions, weather, events)
    if flags is not None and not flags.empty:
        flags["month_start"] = pd.to_datetime(flags["month_start"])
        data = data.drop(columns="quality_flag").merge(flags, on=["city_code", "month_start"], how="left")
    return LoadResult(data, "bigquery", label, updated, notes)


# --------------------------------------------------------------------------- local files
def load_local() -> LoadResult:
    traffic_file = PROCESSED_DIR / "traffic_monthly_clean.csv"
    label = "Local pipeline files · data/processed"
    if not traffic_file.exists():
        return LoadResult(None, "local", label,
                          error=f"{traffic_file} not found. Run `python -m ingestion.run` first.")
    notes = []

    def optional(name: str):
        path = PROCESSED_DIR / name
        if path.exists():
            return pd.read_csv(path)
        notes.append(f"{name} not found")
        return None

    cities, regions = load_seeds()
    data = metrics.build_city_month(pd.read_csv(traffic_file), cities, regions,
                                    optional("weather_daily.csv"), optional("event_days.csv"))
    return LoadResult(data, "local", label, _fmt_time(traffic_file.stat().st_mtime), notes)


def load_snapshot() -> LoadResult:
    label = "Bundled snapshot of the pipeline output"
    if not SNAPSHOT.exists():
        return LoadResult(None, "snapshot", label, error="Snapshot file is missing.")
    data = pd.read_csv(SNAPSHOT, parse_dates=["month_start"])
    return LoadResult(data, "snapshot", label, _fmt_time(SNAPSHOT.stat().st_mtime),
                      ["weather not in the snapshot yet"])


# --------------------------------------------------------------------------- entry point
def load() -> LoadResult:
    mode = os.environ.get("MASAR_DATA_SOURCE", "auto").strip().lower()
    if mode == "bigquery":
        return load_bigquery()
    if mode == "local":
        return load_local()
    if mode == "snapshot":
        return load_snapshot()

    tried = []
    for loader in (load_bigquery, load_local, load_snapshot):
        result = loader()
        if result.data is not None:
            if tried:
                result.notes.insert(0, "Fell back from: " + "; ".join(tried))
            return result
        tried.append(f"{result.source} ({result.error})")
    return LoadResult(None, "none", "No data source", error=" | ".join(tried))