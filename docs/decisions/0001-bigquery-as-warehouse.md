# 0001 — BigQuery as the warehouse

**Status:** accepted

**Context.** We need one place to store raw traffic, events and weather, run dbt models and serve the dashboard. The options were PostgreSQL (already in Docker for Airflow metadata) or BigQuery.

**Decision.** BigQuery (`saudi-industrial-mobility`, region `me-central1`, Doha) for raw and modelled data. PostgreSQL stays only as the Airflow metadata database.

**Consequences.**
- No database server to run. dbt-bigquery and the Streamlit BigQuery client work the same from laptops, Docker and the cloud.
- The data currently stays in the Doha region (`me-central1`). A future production deployment can review moving it to the Dammam region (`me-central2`).
- Docker and local runs use Google Cloud credentials. The public demo uses a read-only service account stored in Streamlit Secrets and falls back to a bundled snapshot if BigQuery is unavailable (see 0004).
- Cost is close to zero at 48 mart rows. At 100× it would still be cheap if tables are partitioned by month.
