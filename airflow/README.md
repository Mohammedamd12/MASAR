# MASAR Airflow Pipeline

## Overview

The `masar_core_pipeline` DAG orchestrates the MASAR data pipeline using Apache Airflow, Google Cloud Storage (GCS), and BigQuery.

It profiles the source workbooks, runs the ingestion pipeline, uploads cleaned CSV files to GCS, and loads them into BigQuery.

## Pipeline Flow

1. `profile_workbooks` — Profiles the source Excel workbooks.
2. `run_ingestion` — Runs the ingestion module and generates processed CSV files.
3. `upload_traffic_to_gcs` — Uploads cleaned traffic data.
4. `upload_events_to_gcs` — Uploads cleaned event data.
5. `upload_event_days_to_gcs` — Uploads expanded event-day records.
6. `load_traffic_to_bigquery` — Loads traffic data into BigQuery.
7. `load_events_to_bigquery` — Loads event data into BigQuery.
8. `load_event_days_to_bigquery` — Loads event-day data into BigQuery.
9. `build_dbt` — Runs dbt commands after all three BigQuery loads complete.

Each BigQuery load depends on the corresponding GCS upload.

## Google Cloud Resources

- GCP Project: `saudi-industrial-mobility`
- GCS Bucket: `saudi-industrial-mobility-raw-data`
- Airflow Connection: `google_cloud_default`

### BigQuery Tables

| Table | Validated Rows |
|---|---:|
| `masar_raw.traffic_monthly` | 48 |
| `masar_raw.events_clean` | 711 |
| `masar_raw.event_days` | 4,001 |

These counts reflect the October 10, 2026 test dataset.

## Local Setup

1. Clone the MASAR repository.
2. Configure the environment variables using `.env.example`. On Linux, set `AIRFLOW_UID` to your user ID (`id -u`).
3. Configure Google Cloud Application Default Credentials (ADC) with access to the MASAR project.
4. Make the ADC credentials file available inside the Airflow containers, using a local Docker Compose override or an equivalent secure mount.
5. Set `GOOGLE_APPLICATION_CREDENTIALS` inside the containers to the mounted credentials file.
6. Build and start the services with `docker compose up -d --build`.
7. Open Airflow at `http://localhost:8080`.

Do not commit ADC credential files, service-account JSON keys, or local secrets to Git.

### Airflow Google Connection

Create the connection from the repository root:

```bash
docker compose exec airflow-scheduler airflow connections add google_cloud_default \
  --conn-type google_cloud_platform \
  --conn-extra '{"project":"saudi-industrial-mobility"}'
```

The Google Provider uses ADC when explicit credentials are not supplied. Each developer must configure their own authorized credentials.

## Testing

List the DAG tasks:

```bash
docker compose exec airflow-scheduler airflow tasks list masar_core_pipeline
```

Test the pipeline without running dbt:

```bash
docker compose exec airflow-scheduler airflow dags test masar_core_pipeline 2026-10-10 --mark-success-pattern '^build_dbt$'
```

This executes ingestion, GCS uploads, and BigQuery loads. It marks `build_dbt` successful without executing it.

**Warning:** BigQuery load tasks use `WRITE_TRUNCATE`, which replaces the contents of their destination tables.

## Validated Results

On October 10, 2026:

- All eight non-dbt tasks completed successfully in an integrated DAG test.
- Traffic: 48 rows loaded and verified in BigQuery.
- Events: 711 rows loaded and verified.
- Event days: 4,001 rows loaded and verified.
- Google Cloud authentication was tested using service-account impersonation without committing a static service-account key.

## Pending Integration

- Weather ingestion remains disabled with `--skip-weather`.
- The dbt task is defined but has not been validated against the final BigQuery-backed dbt configuration.
- Each developer must configure their own Google Cloud authentication and local Airflow Connection before running the DAG.
- The current dbt profile uses DuckDB (`dbt/profiles.yml`).
  The dbt owner must configure and validate the final BigQuery
  target before enabling the complete cloud pipeline.
- The `industrial_cities.csv` reference dataset is located in
  `dbt/seeds/` and is expected to be managed through `dbt seed`.
  Its BigQuery loading has not been validated yet.