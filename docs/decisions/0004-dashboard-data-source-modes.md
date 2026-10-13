# 0004 — Dashboard data source: BigQuery in Docker, snapshot fallback for the public demo

**Status:** accepted (architecture review item #4)

**Context.** The dashboard runs in three places: Docker (team demo, has GCP credentials), Streamlit Community Cloud (public link, no credentials) and laptops (sometimes no credentials). The review said that relying on `load()` fallback hides whether we are cloud-ready.

**Decision.** `MASAR_DATA_SOURCE` picks the source:
- **Docker:** `bigquery`, set in the Dockerfile, `docker-compose.yml` and `.env.example`. There is no fallback. If BigQuery is unreachable, the page shows a clear error.
- **Public demo and local:** `auto` (the code default). It tries BigQuery → local CSV → bundled snapshot.

The page always shows which source it used ("Live BigQuery", "Public demo dataset", or a not-live warning).

**Consequences.**
- The demo proves the live path: `docker compose exec streamlit printenv MASAR_DATA_SOURCE` prints `bigquery`.
- The public link keeps working without exposing credentials.
- The snapshot must be refreshed when the data changes. Today it matches the mart (48 rows, 20,707,074).
