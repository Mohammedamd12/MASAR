# 0002 — Mart tables live in `masar_staging`, not `masar_marts`

**Status:** accepted (revisit after the bootcamp)

**Context.** Terraform creates three datasets: `masar_raw`, `masar_staging` and `masar_marts`. `dbt/profiles.yml` targets `masar_staging`, and the project has no custom schema per folder, so dbt writes staging views **and** mart tables to `masar_staging`.

**Decision.** Keep it as it is for the demo. Staging is separated by materialisation (views) and marts by name (`fct_*`, tables). The dashboard reads `masar_staging.fct_city_movement_monthly`, and the name can be changed with `MASAR_BQ_MART`.

**Consequences.**
- No risky change to the profile or dataset permissions just before the demo.
- `masar_marts` exists but is empty, which can confuse a new teammate. This is documented in `streamlit/README.md`.
- To fix later: add `+schema: marts` under `marts` in `dbt_project.yml` with a `generate_schema_name` macro, then set `MASAR_BQ_MART` to the new path.
