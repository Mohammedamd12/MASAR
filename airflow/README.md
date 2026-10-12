# MASAR Airflow Pipeline

## Overview

The `masar_core_pipeline` DAG orchestrates the MASAR data pipeline using Apache Airflow, Google Cloud Storage (GCS), BigQuery, and dbt.

It profiles Excel workbooks, runs Python ingestion, uploads processed CSV files to GCS, loads the data into BigQuery, and runs dbt transformations and tests.

**For complete setup instructions, Docker commands, Google Cloud authentication, and troubleshooting, see [MASAR Airflow Setup Guide](MASAR_AIRFLOW_SETUP.md).**

## Pipeline Flow

The DAG contains 11 tasks:

1. `profile_workbooks` — Profiles source Excel workbooks.
2. `run_ingestion` — Runs Python ingestion and prepares CSV files.
3. `upload_traffic_to_gcs` — Uploads traffic data to GCS.
4. `upload_events_to_gcs` — Uploads event data to GCS.
5. `upload_event_days_to_gcs` — Uploads event-day records to GCS.
6. `upload_weather_to_gcs` — Uploads prepared weather data to GCS.
7. `load_traffic_to_bigquery` — Loads traffic data into BigQuery.
8. `load_events_to_bigquery` — Loads event data into BigQuery.
9. `load_event_days_to_bigquery` — Loads event-day data into BigQuery.
10. `load_weather_to_bigquery` — Loads weather data into BigQuery.
11. `build_dbt` — Runs `dbt seed`, `dbt run`, and `dbt test` after the required BigQuery loads succeed.

Each BigQuery load depends on its corresponding GCS upload. The dbt task runs after the data-loading dependencies succeed.

## Google Cloud Resources

- **GCP Project:** `saudi-industrial-mobility`
- **GCS Bucket:** `saudi-industrial-mobility-raw-data`
- **Airflow Connection:** `google_cloud_default`
- **BigQuery Raw Dataset:** `masar_raw`

### Validated Data

The following row counts were verified during pipeline testing:

| Dataset | Rows |
|---|---:|
| Traffic | 48 |
| Events | 711 |
| Event days | 4,001 |
| Weather | 2,172 |

These values describe the tested dataset, not guaranteed counts for future runs.

## Local Setup

Follow the [MASAR Airflow Setup Guide](MASAR_AIRFLOW_SETUP.md) for:

- Docker Compose setup and startup commands.
- Google Cloud Application Default Credentials (ADC).
- Airflow connection configuration.
- Airflow 3 Execution API and JWT configuration.
- Running and monitoring the DAG.
- Common errors and troubleshooting.

Each developer must use their own authorized Google Cloud credentials. Never commit `.env`, credential files, JWT secrets, or Fernet keys.

## Testing and Validation

### October 10, 2026

The initial integrated test validated Python ingestion, GCS uploads, and BigQuery loading.

### October 11, 2026

The full pipeline was successfully tested through the Airflow web interface:

- **DAG:** `masar_core_pipeline`
- **Run type:** Manual Trigger
- **Result:** Success
- **Tasks:** 11 of 11 succeeded
- **Duration:** Approximately 1 minute and 37 seconds

The successful run included data ingestion, GCS uploads, BigQuery loads, and dbt execution.

The dbt task completed its seed, run, and test commands against the configured BigQuery environment.

## Current Limitations

- Weather data was loaded successfully during testing, but live weather API collection is not enabled as part of the Airflow ingestion flow.
- BigQuery loading uses `WRITE_TRUNCATE`, replacing the contents of the destination tables on each successful load.
- This avoids accumulating rows from previous loads, but it does not skip unchanged Excel files automatically.
- File-level tracking and skipping unchanged quarterly files are not currently implemented.
- Local Google Cloud credentials and Airflow authentication settings must be configured separately on each developer's machine.

## Related Documentation

- [Airflow Setup & Troubleshooting Guide](MASAR_AIRFLOW_SETUP.md)
- [MASAR Project README](../README.md)