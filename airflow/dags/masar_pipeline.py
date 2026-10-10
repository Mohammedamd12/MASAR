
from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path

from airflow.sdk import dag, task
from airflow.providers.google.cloud.transfers.local_to_gcs import (
    LocalFilesystemToGCSOperator,
)
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import (
    GCSToBigQueryOperator,
)


PROJECT_DIR = Path(os.environ.get("MASAR_PROJECT_DIR", "/opt/airflow/project"))
GCP_PROJECT = "saudi-industrial-mobility"
GCS_BUCKET = "saudi-industrial-mobility-raw-data"
GCP_CONN_ID = "google_cloud_default"


def run_command(*command: str, cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd, check=True)


@dag(
    dag_id="masar_core_pipeline",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["masar", "core"],
)
def masar_core_pipeline():

    @task
    def profile_workbooks() -> str:
        output = PROJECT_DIR / "data" / "processed" / "workbook_inventory.csv"

        run_command(
            "python",
            str(PROJECT_DIR / "airflow" / "scripts" / "profile_workbooks.py"),
            "--input-dir",
            str(PROJECT_DIR),
            "--output",
            str(output),
        )

        return str(output)

    @task
    def run_ingestion(_: str) -> str:
        # Run Hassan's ingestion pipeline.
        # Weather is temporarily skipped during local testing.
        run_command(
            "python",
            "-m",
            "ingestion.run",
            "--skip-weather",
            cwd=PROJECT_DIR,
        )

        return str(PROJECT_DIR / "data" / "processed")

    @task
    def build_dbt(_: str) -> None:
        # Run dbt after all BigQuery load tasks finish.
        dbt_dir = PROJECT_DIR / "dbt"

        run_command("dbt", "seed", "--profiles-dir", ".", cwd=dbt_dir)
        run_command("dbt", "run", "--profiles-dir", ".", cwd=dbt_dir)
        run_command("dbt", "test", "--profiles-dir", ".", cwd=dbt_dir)

    # Step 1: Profile source workbooks and prepare clean CSV files.
    ingestion_output = run_ingestion(profile_workbooks())

    # Step 2A: Upload cleaned traffic data to GCS.
    upload_traffic_to_gcs = LocalFilesystemToGCSOperator(
        task_id="upload_traffic_to_gcs",
        src=str(PROJECT_DIR / "data" / "processed" / "traffic_monthly_clean.csv"),
        dst="processed/traffic_monthly_clean.csv",
        bucket=GCS_BUCKET,
        gcp_conn_id=GCP_CONN_ID,
        mime_type="text/csv",
    )

    # Step 2B: Upload cleaned events data to GCS.
    upload_events_to_gcs = LocalFilesystemToGCSOperator(
        task_id="upload_events_to_gcs",
        src=str(PROJECT_DIR / "data" / "processed" / "events_clean.csv"),
        dst="processed/events_clean.csv",
        bucket=GCS_BUCKET,
        gcp_conn_id=GCP_CONN_ID,
        mime_type="text/csv",
    )

    # Step 2C: Upload expanded event-day records to GCS.
    upload_event_days_to_gcs = LocalFilesystemToGCSOperator(
        task_id="upload_event_days_to_gcs",
        src=str(PROJECT_DIR / "data" / "processed" / "event_days.csv"),
        dst="processed/event_days.csv",
        bucket=GCS_BUCKET,
        gcp_conn_id=GCP_CONN_ID,
        mime_type="text/csv",
    )

    # Step 3A: Load traffic CSV from GCS into BigQuery.
    load_traffic_to_bigquery = GCSToBigQueryOperator(
        task_id="load_traffic_to_bigquery",
        bucket=GCS_BUCKET,
        source_objects=["processed/traffic_monthly_clean.csv"],
        destination_project_dataset_table=(
            f"{GCP_PROJECT}.masar_raw.traffic_monthly"
        ),
        source_format="CSV",
        skip_leading_rows=1,
        schema_fields=[
            {"name": "city_code", "type": "STRING", "mode": "NULLABLE"},
            {"name": "city_name", "type": "STRING", "mode": "NULLABLE"},
            {"name": "region_code", "type": "STRING", "mode": "NULLABLE"},
            {"name": "month_start", "type": "DATE", "mode": "NULLABLE"},
            {"name": "entries", "type": "INTEGER", "mode": "NULLABLE"},
            {"name": "exits", "type": "INTEGER", "mode": "NULLABLE"},
            {"name": "quality_flag", "type": "STRING", "mode": "NULLABLE"},
            {"name": "source_file", "type": "STRING", "mode": "NULLABLE"},
            {"name": "layout_version", "type": "STRING", "mode": "NULLABLE"},
        ],
        write_disposition="WRITE_TRUNCATE",
        create_disposition="CREATE_IF_NEEDED",
        gcp_conn_id=GCP_CONN_ID,
    )

    # Step 3B: Load cleaned event records into BigQuery.
    load_events_to_bigquery = GCSToBigQueryOperator(
        task_id="load_events_to_bigquery",
        bucket=GCS_BUCKET,
        source_objects=["processed/events_clean.csv"],
        destination_project_dataset_table=(
            f"{GCP_PROJECT}.masar_raw.events_clean"
        ),
        source_format="CSV",
        skip_leading_rows=1,
        schema_fields=[
            {"name": "gov_request_number", "type": "STRING", "mode": "NULLABLE"},
            {"name": "event_name", "type": "STRING", "mode": "NULLABLE"},
            {"name": "event_type", "type": "STRING", "mode": "NULLABLE"},
            {"name": "venue_type", "type": "STRING", "mode": "NULLABLE"},
            {"name": "event_city", "type": "STRING", "mode": "NULLABLE"},
            {"name": "start_date", "type": "DATE", "mode": "NULLABLE"},
            {"name": "end_date", "type": "DATE", "mode": "NULLABLE"},
            {"name": "duration_days", "type": "INTEGER", "mode": "NULLABLE"},
            {"name": "attendance", "type": "FLOAT", "mode": "NULLABLE"},
            {"name": "relevance", "type": "STRING", "mode": "NULLABLE"},
            {"name": "region_code", "type": "STRING", "mode": "NULLABLE"},
            {"name": "industrial_city_codes", "type": "STRING", "mode": "NULLABLE"},
            {"name": "source_file", "type": "STRING", "mode": "NULLABLE"},
            {"name": "source_row", "type": "INTEGER", "mode": "NULLABLE"},
        ],
        write_disposition="WRITE_TRUNCATE",
        create_disposition="CREATE_IF_NEEDED",
        gcp_conn_id=GCP_CONN_ID,
        allow_quoted_newlines=True,
    )

    # Step 3C: Load daily event-city records into BigQuery.
    load_event_days_to_bigquery = GCSToBigQueryOperator(
        task_id="load_event_days_to_bigquery",
        bucket=GCS_BUCKET,
        source_objects=["processed/event_days.csv"],
        destination_project_dataset_table=(
            f"{GCP_PROJECT}.masar_raw.event_days"
        ),
        source_format="CSV",
        skip_leading_rows=1,
        schema_fields=[
            {"name": "gov_request_number", "type": "STRING", "mode": "NULLABLE"},
            {"name": "city_code", "type": "STRING", "mode": "NULLABLE"},
            {"name": "event_date", "type": "DATE", "mode": "NULLABLE"},
            {"name": "relevance", "type": "STRING", "mode": "NULLABLE"},
        ],
        write_disposition="WRITE_TRUNCATE",
        create_disposition="CREATE_IF_NEEDED",
        gcp_conn_id=GCP_CONN_ID,
    )

    # Step 4: Each upload must finish before its matching BigQuery load.
    ingestion_output >> [
        upload_traffic_to_gcs,
        upload_events_to_gcs,
        upload_event_days_to_gcs,
    ]

    upload_traffic_to_gcs >> load_traffic_to_bigquery
    upload_events_to_gcs >> load_events_to_bigquery
    upload_event_days_to_gcs >> load_event_days_to_bigquery

    # Step 5: dbt waits for all three BigQuery load tasks.
    dbt_task = build_dbt(ingestion_output)

    [
        load_traffic_to_bigquery,
        load_events_to_bigquery,
        load_event_days_to_bigquery,
    ] >> dbt_task


masar_core_pipeline()
