from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path

from airflow.sdk import dag, task


PROJECT_DIR = Path(os.environ.get("MASAR_PROJECT_DIR", "/opt/airflow/project"))


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
    def build_dbt(_: str) -> None:
        dbt_dir = PROJECT_DIR / "dbt"
        run_command("dbt", "seed", "--profiles-dir", ".", cwd=dbt_dir)
        run_command("dbt", "run", "--profiles-dir", ".", cwd=dbt_dir)
        run_command("dbt", "test", "--profiles-dir", ".", cwd=dbt_dir)

    build_dbt(profile_workbooks())


masar_core_pipeline()

