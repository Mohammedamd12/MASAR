# 0005 — Full refresh on every run (WRITE_TRUNCATE) instead of incremental loads

**Status:** accepted

**Context.** The sources are a few Excel workbooks (48 city-months, a few hundred events). A rerun must not create duplicates, and the same file can be dropped twice.

**Decision.** Every run rebuilds everything:
- Ingestion reads all workbooks and removes duplicates (`duplicate_row` for traffic, `duplicate_request_number` for events). Bad rows go to `*_rejects.csv` with a reason, so nothing is dropped silently.
- BigQuery loads use `write_disposition="WRITE_TRUNCATE"`.
- dbt marts are tables, rebuilt on every run.

**Consequences.**
- Reruns and backfills are safe: run the DAG again and get the same result.
- The whole run takes minutes at this size.
- At 100× the data, a full rebuild gets slow and costly. The next step would be partitioning by `month_start` and incremental dbt models, triggered by a GCS upload.
