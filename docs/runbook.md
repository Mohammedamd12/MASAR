# MASAR runbook

What to do when something breaks. Every fix below is based on how the code works today.

## Debug by layer first

Count rows at each layer. The first layer where the number is wrong is where the bug is.

| Layer | Where | Expected (Jan–Jun 2026) |
|---|---|---|
| Source | `Traffic (3).xlsx`, `Traffic (4).xlsx` | — |
| Processed | `data/processed/traffic_monthly_clean.csv` | 48 rows |
| Rejects | `data/processed/traffic_rejects.csv` | read the `reject_reason` column |
| Raw | `masar_raw.traffic_monthly` | 48 rows |
| Mart | `masar_staging.fct_city_movement_monthly` | 48 rows, `SUM(total_movement)` = 20,707,074 |
| Dashboard | header badge | **Live BigQuery**, total 20,707,074 |

```sql
-- raw vs mart in one query
SELECT
  (SELECT COUNT(*) FROM `saudi-industrial-mobility.masar_raw.traffic_monthly`) AS raw_rows,
  (SELECT COUNT(*) FROM `saudi-industrial-mobility.masar_staging.fct_city_movement_monthly`) AS mart_rows,
  (SELECT SUM(total_movement) FROM `saudi-industrial-mobility.masar_staging.fct_city_movement_monthly`) AS mart_total;
```

## Rerun the pipeline

Airflow → DAG `masar_core_pipeline` → **Trigger**. You can also rerun one failed task: open the task → **Clear** (downstream tasks run again too).

**Safe to rerun:** every BigQuery load uses `WRITE_TRUNCATE`, and dbt rebuilds the tables, so a rerun replaces the data. It never adds a second copy (see ADR 0005).

Run dbt by hand:
```powershell
docker compose run --rm airflow-cli bash -lc "cd /opt/airflow/project/dbt && dbt build --profiles-dir ."
```

---

## Failure playbook

### 1. A column was renamed in the source Excel (schema drift)
**Symptom:** `run_ingestion` fails with `KeyError` or `No usable sheets found`, or the row counts drop.
**Why:** `ingestion/excel_utils.py` finds the header row by matching known Arabic column names from `ingestion/labels.py`. A new name is not in the list.
**Fix:**
1. Open `data/processed/traffic_sheet_log.csv` (or `events_sheet_log.csv`) to see which sheet was skipped.
2. Add the new header spelling to the right set in `ingestion/labels.py` (`TRAFFIC_HEADERS` or `EVENT_HEADERS`). Keep the old spelling too.
3. Run `python -m pytest tests -v`, then rerun the DAG.
4. Check the row counts with the table above.

### 2. Permission denied on GCS or BigQuery
**Symptom:** `upload_*_to_gcs` or `load_*_to_bigquery` fails with `403` or `Permission denied`.
**Why:** the service account lost a role, or the local login expired.
**Fix:**
1. Check the roles. The pipeline needs `roles/bigquery.dataEditor`, `roles/bigquery.jobUser` and `roles/storage.objectAdmin` (`google_project_iam_member.pipeline_roles` in `terraform/main.tf`).
2. Restore them with Terraform, not by clicking in the console:
   ```powershell
   cd terraform; terraform plan; terraform apply
   ```
3. If you use your own login: `gcloud auth application-default login`, then `docker compose restart airflow-scheduler streamlit`.
4. If the error says `google_cloud_default isn't defined`, follow section F of `airflow/MASAR_AIRFLOW_SETUP.md`.

### 3. The same file was dropped twice (idempotency)
**Symptom:** for example a `Traffic (3) - Copy.xlsx` appears next to the original. `Traffic*.xlsx` matches both files.
**What happens:** nothing is counted twice. `clean_traffic` keeps the first row for each city + month + direction and sends the copy to `traffic_rejects.csv` with `duplicate_row`. Events are deduplicated by government request number (`duplicate_request_number`).
**Check:**
1. Look in `traffic_rejects.csv` for many `duplicate_row` rows.
2. Confirm the mart is still 48 rows with total 20,707,074.
3. Remove the extra file.

### 4. Weather API returns 429 or 5xx (rate limit)
**Symptom:** `run_ingestion` is slow, or fails during the weather step.
**Why:** Open-Meteo is busy.
**What happens:** `ingestion/weather.py` retries 5 times with backoff (2, 4, 8, 16, 32 s), and Airflow retries the task 2 more times.
**Fix:** if it still fails, wait 10 minutes and clear the task. To unblock traffic and events right away, run `python -m ingestion.run --skip-weather` by hand. Weather is context only, so the main numbers are not affected.

### 5. A month is missing (late or missing data)
**Symptom:** a city has fewer than 6 months, or the dashboard shows a gap.
**What happens:** missing months are reported in `data/processed/traffic_coverage.csv` (`has_data = False`) and never filled. Growth uses the average monthly movement, so a missing month does not make growth look smaller (see ADR 0003).
**Fix:** check the source file. If the month really is missing, tell the stakeholder. Do not invent a value. Known gaps today: Tabuk (April), Sudair (April, May).

### 6. dbt test fails
**Symptom:** `build_dbt` fails at `dbt test`.
**Fix:**
1. Read the failing test name in the task log.
2. Run the compiled SQL from `dbt/target/compiled/` in BigQuery to see the bad rows.
3. Fix the data upstream (ingestion or seed), not the test.

### 7. Dashboard shows "Data is not available right now" (Docker)
**Why:** the container is forced to `MASAR_DATA_SOURCE=bigquery` and cannot reach BigQuery. This is on purpose, so there is no silent fallback (ADR 0004).
**Fix:** run `gcloud auth application-default login` on the host, then `docker compose restart streamlit`. For a demo without credentials, use https://masar-saudi.streamlit.app (snapshot).

### 8. A container is killed (out of memory)
**Check:** `docker stats`.
**Fix:** raise the limit in `.env` (`AIRFLOW_MEMORY_LIMIT`, `STREAMLIT_MEMORY_LIMIT`, `POSTGRES_MEMORY_LIMIT`), then `docker compose up -d`.

---

## Rotate credentials
1. Never commit `.env`, `gcp-key.json` or `*.tfstate`. They are already in `.gitignore`.
2. If a key leaks: disable it in IAM → create a new one → update the local file → `docker compose restart`.
3. Do not rotate the Airflow Fernet key casually. Stored connections become unreadable (see `airflow/MASAR_AIRFLOW_SETUP.md`).

## After grading: teardown
```powershell
cd terraform
terraform destroy
```
The datasets have `delete_contents_on_destroy = false` and the bucket has `force_destroy = false`, so empty them first or Terraform will stop. Confirm in the console that nothing is left.

---

## Postmortem template (10 lines)

```
Date / time:
What broke:
How we noticed:
Impact (which numbers / pages were wrong, for how long):
Root cause:
Fix applied:
How we confirmed (row counts / total 20,707,074):
Why it was not caught earlier:
Action to prevent it (owner):
Runbook section updated: yes / no
```
