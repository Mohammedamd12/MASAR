# 0004 — Dashboard data source: BigQuery with a visible snapshot fallback

**Status:** accepted (architecture review item #4)

**Context.** The dashboard runs in three places: Docker, Streamlit Community Cloud and team laptops. Docker and authenticated laptops use Google Cloud credentials. The public app uses a read-only service account stored in Streamlit Secrets. The review said that relying on an invisible `load()` fallback hides whether the dashboard is reading live data.

**Decision.** `MASAR_DATA_SOURCE` picks the source:
- **Docker:** `bigquery`, set in the Dockerfile, `docker-compose.yml` and `.env.example`. There is no fallback. If BigQuery is unreachable, the page shows a clear error.
- **Public demo:** `auto` (the code default). It reads live BigQuery through the read-only `masar-dashboard-reader` service account. If the secret is missing or BigQuery is unavailable, it tries local CSV and then the bundled snapshot.
- **Local:** `auto`. It tries BigQuery through local Google credentials, then local CSV, then the bundled snapshot.

The page always shows which source it used ("Live BigQuery", "Public demo dataset", or a not-live warning).

**Consequences.**
- The demo proves the live path: `docker compose exec streamlit printenv MASAR_DATA_SOURCE` prints `bigquery`.
- The public link reads the live mart without exposing credentials in the repository.
- The snapshot keeps the page available during a credential or BigQuery outage. It must be refreshed when the data changes. Today it matches the mart (48 rows, 20,707,074).
