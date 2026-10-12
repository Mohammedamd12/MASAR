# MASAR — Airflow Setup & Troubleshooting

This guide helps a teammate run the MASAR Airflow pipeline locally using Docker Compose, Google Cloud credentials, and the Airflow 3 web interface.

> **Project:** Saudi Industrial Mobility Intelligence (MASAR)
> **DAG:** `masar_core_pipeline`
> **Airflow:** 3.3.1 (Docker)
> **Cloud project:** `saudi-industrial-mobility`
> **Important:** Use your own Google account credentials. Never commit credentials, JWT/Fernet keys, or your local `.env` file.

## 0. Before starting

You need:

- Access to the MASAR GitHub repository and the Google Cloud project.
- Docker Engine/Desktop with Docker Compose (`docker compose version`).
- Git and Python 3 on your host machine; Google Cloud CLI (`gcloud`) for authentication.
- Enough free memory for Docker, Airflow, PostgreSQL, and Streamlit. Stop unrelated Docker projects if needed.
- Access to the source Excel workbooks: `Traffic (3).xlsx`, `Traffic (4).xlsx`, `Public Sector Events Q1 2026.xlsx`, and `Public Sector Events Q2 2026.xlsx`. Put them in the **repository root**, alongside `docker-compose.yml`. These are expected by the current ingestion glob patterns.

**Run commands in the repository root** (the directory containing `docker-compose.yml`), unless otherwise specified. The Linux/Ubuntu commands below are bash commands. For Windows, use WSL/Ubuntu bash, or see the Windows notes.

## 1. Get the repository

If you have not cloned it:

```bash
git clone https://github.com/Mohammedamd12/MASAR.git
cd MASAR
```

Otherwise:

```bash
cd /path/to/MASAR
git status --short
git pull --ff-only
```

**Do not run `git pull` if you have uncommitted work without first coordinating or preserving it.** The instructions assume the current team branch contains the Docker setup, Airflow DAG, ingestion code, and dbt project.

Check prerequisites:

```bash
docker --version
docker compose version
python3 --version
gcloud --version
```

## 2. Authenticate to Google Cloud on your own computer

Set up Application Default Credentials (ADC) **on your host**, not inside Airflow:

```bash
gcloud auth application-default login
gcloud config set project saudi-industrial-mobility
```

For Linux/Ubuntu, the default ADC file is usually:

```text
~/.config/gcloud/application_default_credentials.json
```

Verify the file exists (this command **does not display its contents**):

```bash
test -f "$HOME/.config/gcloud/application_default_credentials.json" && echo 'ADC file found'
```

**Access may still fail even with ADC:** ask the project owner to verify the account has the required GCS/BigQuery permissions and that APIs are enabled. Do not create or share service-account JSON keys as a quick fix.

### Windows note

If you run Docker Compose directly from **Windows PowerShell**, `${APPDATA}/gcloud` in the shared `docker-compose.yml` normally points to the Windows Google Cloud credentials directory. Google Cloud CLI may store ADC under `%APPDATA%\gcloud`.

If you run Docker Compose from **Ubuntu/WSL/VMware**, use the Linux procedure in this guide. Windows paths cannot automatically be assumed to exist inside Ubuntu. A VMware VM also has a different `localhost` and filesystem from Windows.

## 3. Create local-only secrets and Compose settings (Linux/Ubuntu)

Our shared Compose file contains an `${APPDATA}/gcloud` mount. Define a valid Linux path to avoid repeated `APPDATA` warnings, and create one common JWT secret and Fernet key for all three Airflow services.

**If `.env` already exists, do not overwrite it blindly.** Preserve any team-provided database settings. The snippet below creates or updates only the three named variables while preserving other lines.

```bash
python3 - <<'PY'
from pathlib import Path
import base64, secrets, os

p = Path('.env')
lines = p.read_text().splitlines() if p.exists() else []
keys = {'APPDATA', 'AIRFLOW__API_AUTH__JWT_SECRET', 'AIRFLOW__CORE__FERNET_KEY'}
existing = {}
for line in lines:
    if '=' in line and not line.lstrip().startswith('#'):
        k, v = line.split('=', 1)
        if k in keys and v:
            existing[k] = v
updated = [line for line in lines if not any(line.startswith(k + '=') for k in keys)]
values = {
    'APPDATA': (str(Path.home() / '.config') if existing.get('APPDATA') in (None, '/tmp') else existing['APPDATA']),
    'AIRFLOW__API_AUTH__JWT_SECRET': existing.get('AIRFLOW__API_AUTH__JWT_SECRET', secrets.token_urlsafe(48)),
    'AIRFLOW__CORE__FERNET_KEY': existing.get('AIRFLOW__CORE__FERNET_KEY', base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()),
}
p.write_text('\n'.join(updated + [f'{k}={v}' for k, v in values.items()]) + '\n')
p.chmod(0o600)
print('Local .env configured (secret values are not shown).')
PY
```

Create the host credentials mount location if it is missing:

```bash
mkdir -p "$HOME/.config/gcloud"
```

> **Existing installation?** Changing the Fernet key after Airflow connections are stored can make their encrypted fields unreadable. Keep your original Fernet value and do not rotate it casually. The above script reuses existing `.env` values; if your prior Fernet key is stored elsewhere, restore that original key before recreating containers.

Create a local file named `docker-compose.override.yml` in the repository root with **exactly this structure** for a Linux host using the default ADC location:

```yaml
x-masar-local: &masar-local
  environment:
    GOOGLE_APPLICATION_CREDENTIALS: /opt/airflow/gcp/adc.json
    GOOGLE_CLOUD_PROJECT: saudi-industrial-mobility
    AIRFLOW__CORE__EXECUTION_API_SERVER_URL: http://airflow-api-server:8080/execution/
    AIRFLOW__API_AUTH__JWT_SECRET: ${AIRFLOW__API_AUTH__JWT_SECRET}
    AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW__CORE__FERNET_KEY}
  volumes:
    - ${HOME}/.config/gcloud/application_default_credentials.json:/opt/airflow/gcp/adc.json:ro

services:
  airflow-api-server:
    <<: *masar-local
  airflow-scheduler:
    <<: *masar-local
  airflow-dag-processor:
    <<: *masar-local
```

**Important:** This is a local override for the team's current Compose layout. Docker Compose normally merges service environment mappings and volumes by their container target, but you must **verify the effective merged configuration** before starting. Do not start if original DB settings or repository mounts are missing.

For a custom ADC path (e.g. a separate `~/.config/gcloud-masar/application_default_credentials.json`), change only the **host side** of the volume path. In WSL/VMware, `HOME` and the ADC file must belong to the Linux environment where Docker Compose runs.

Exclude secrets from Git locally:

```bash
printf '\n.env\ndocker-compose.override.yml\n.masar-jwt-key\n.masar-fernet-key\n' >> .git/info/exclude
```

> If the team already tracks any of these names, `.git/info/exclude` will not stop Git from tracking them. Check `git status --short` before every commit. **Never use `git add .` for local secrets.**

### Validate the *effective* Compose configuration

```bash
docker compose config --quiet
```

Then inspect the **effective values** for the scheduler without dumping JWT/Fernet secrets:

```bash
docker compose config --format json | python3 -c 'import json,sys; c=json.load(sys.stdin); s=c["services"]["airflow-scheduler"]; e=s.get("environment",{}); print("Command:", s.get("command")); print("DB configured:", bool(e.get("AIRFLOW__DATABASE__SQL_ALCHEMY_CONN"))); print("Project dir:", e.get("MASAR_PROJECT_DIR")); print("Execution API:", e.get("AIRFLOW__CORE__EXECUTION_API_SERVER_URL")); print("Mounts:", [x.get("target","") for x in s.get("volumes",[])])'
```

The effective scheduler config must still contain the original **database connection**, **MASAR_PROJECT_DIR**, repository/DAG/logs mounts, and the new ADC mount. If anything is missing, **stop here and coordinate the override** before `docker compose up`; don't keep restarting a broken setup.

## 4. Build and start MASAR

```bash
docker compose build
docker compose up -d postgres
```

Wait until Postgres is healthy:

```bash
docker compose ps
```

Initialize or migrate Airflow's metadata DB (on a fresh installation, or after upgrading Airflow):

```bash
docker compose run --rm airflow-init
```

Start the services:

```bash
docker compose up -d airflow-api-server airflow-scheduler airflow-dag-processor streamlit
```

Verify:

```bash
docker compose ps
```

The API server's health may say `starting` briefly; give it some time. For problems, inspect logs:

```bash
docker compose logs --tail 60 airflow-api-server airflow-scheduler
```

## 5. Configure the Airflow GCP connection

Airflow's Google Cloud tasks use `google_cloud_default`. For a *fresh installation*, create it with the project ID, using the mounted ADC file for authentication:

```bash
docker compose exec airflow-scheduler airflow connections add google_cloud_default \
  --conn-type google_cloud_platform \
  --conn-extra '{"project":"saudi-industrial-mobility"}'
```

If it already exists, **do not delete it immediately**. Inspect it without printing secrets, or ask the team's Airflow owner to confirm it is working. Duplicate connection attempts may fail harmlessly with an “already exists” message.

Check CLI dependencies:

```bash
docker compose exec airflow-scheduler dbt --version
```

The tested setup used `dbt-core==1.12.5` with `dbt-bigquery==1.10.0`. Ensure the dependency-pinning PR is merged into the branch you are running (or coordinate with its author), then rebuild the Airflow image when `airflow/requirements.txt` changes.

## 6. Log in to Airflow and run the DAG

Open Airflow:

```text
http://localhost:8080
```

**VMware/remote Ubuntu:** open `http://<UBUNTU_VM_IP>:8080` from your Windows browser, not Windows `localhost:8080`. Find the VM IP in Ubuntu with:

```bash
hostname -I
```

If your Airflow instance uses Simple Auth Manager and needs a generated password, on **your own computer**:

```bash
docker compose exec airflow-api-server cat /opt/airflow/simple_auth_manager_passwords.json.generated
```

**Do not paste or screenshot that password in chats or issues.**

In the UI:

1. Open **Dags** → `masar_core_pipeline`.
2. Check that the DAG appears and the task graph shows 11 tasks.
3. Use **Trigger** → **Single Run** (not Backfill). For a manual one-time test, confirm what the `Unpause ... on trigger` option will do. If the run stays **Queued** because the DAG is paused, unpause temporarily.
4. Track the run until **DAG Run = Success** and **all 11 tasks = Success**.
5. **Pause the DAG again after testing** so its current `@daily` schedule does not reload BigQuery unexpectedly.

The successful pipeline follows this dependency order:

```text
profile_workbooks
      ↓
run_ingestion
      ↓
4 CSV uploads → GCS
      ↓
4 table loads → BigQuery raw
      ↓
build_dbt (dbt seed → dbt run → dbt test)
```

Streamlit is a separate dashboard service reading BigQuery results; it is **not an Airflow task**. Dashboard URL (when published): `http://localhost:8501`, or `http://<VM_IP>:8501` from Windows.

## 7. Typical errors and practical fixes

### A. `WARN ... "APPDATA" variable is not set`

**Cause:** Team Compose contains `${APPDATA}/gcloud`, which is commonly defined on Windows but not in Ubuntu.

**Fix (Ubuntu):** `.env` should contain `APPDATA=/home/<linux-user>/.config` (use your *real* home directory), not a dummy path. Check `docker compose config --quiet`. Make sure the credentials directory exists before creating containers.

### B. `ModuleNotFoundError: No module named 'pandas'` when running `python -m ingestion.run`

**Cause:** You ran the ingestion command in a host Python environment without its dependencies.

**Fix:** Run the pipeline through the Airflow Docker container after building it. Do not install or change packages on your host unless you explicitly need a separate local Python environment.

### C. Airflow UI works, but the triggered DAG stays `Queued`

**Check:** Is the DAG **Paused**? If so, unpause temporarily and refresh. Do **not** keep hitting Trigger or Clear repeatedly. Wait for scheduler state updates. Pause again after the test.

### D. `httpx.ConnectError: [Errno 111] Connection refused`

**Cause (observed on our VM):** LocalExecutor tried to contact the task Execution API at an unusable address.

**Fix:** Confirm the scheduler has:

```text
AIRFLOW__CORE__EXECUTION_API_SERVER_URL=http://airflow-api-server:8080/execution/
```

Test internal networking from the scheduler:

```bash
docker compose exec airflow-scheduler python -c "import urllib.request; print(urllib.request.urlopen('http://airflow-api-server:8080/api/v2/version', timeout=10).status)"
```

Expected: HTTP `200`. After editing Compose, recreate the relevant Airflow services; do not assume file changes affect already-running containers.

### E. `ServerResponseError: Invalid auth token`

**Cause (observed on our VM):** The Airflow services did not share an explicit `AIRFLOW__API_AUTH__JWT_SECRET`.

**Fix:** Use the *same* strong JWT secret in the API server, scheduler, and DAG processor through your local `.env`/Compose override. **Never show or share the secret.** Recreate the three Airflow containers so the new environment is applied.

### F. GCS/BigQuery reports `google_cloud_default isn't defined`

**Cause:** The Airflow connection was not created in the metadata DB, or its encrypted content cannot be read.

**Fix:** First check that the three containers use the same persistent Fernet key. Then create `google_cloud_default` once via step 5. Do not delete existing connections or rotate Fernet keys without checking whether they contain credentials you still need.

### G. `403 Permission Denied` from GCS or BigQuery

**Cause:** The Google account authenticated with ADC lacks permissions, APIs are disabled, or the project/dataset is wrong.

**Fix:** Confirm the correct ADC is mounted inside the containers, verify project `saudi-industrial-mobility`, and ask the project owner to grant the required *least-privilege* access. **Do not ask teammates to share their ADC or service-account private key.**

### H. `dbt` is missing, uses the wrong version, or dbt tests fail

**Fix:** Confirm `airflow/requirements.txt` includes the tested dependency versions, rebuild the Airflow image, and inspect the **build_dbt** task log. A dbt data-quality failure is different from a missing package; do not blindly reinstall everything.

### I. Docker services exit or become slow

**Fix:** Run `docker compose ps`, `docker stats --no-stream`, and `free -h` on Ubuntu. Close unused Airflow projects or other resource-heavy containers. Don't assume every `SIGKILL` is caused by insufficient memory; read the task tracebacks too.

### J. `APPDATA` warnings disappear, but Docker mounts the wrong folder

**Cause:** Setting `APPDATA=/tmp` may silence warnings while making the host mount point incorrect.

**Fix:** Use your actual host configuration directory and verify the ADC volume points at a real file. Correcting `.env` alone does **not** update running containers: recreate the affected service after reviewing the merged configuration.

## 8. Safe Git workflow for the guide

The guide belongs in Git; local authentication material does not.

```bash
git status --short
git add airflow/README.md airflow/MASAR_AIRFLOW_SETUP.md
git diff --cached --stat
git commit -m "docs: add Airflow setup and troubleshooting guide"
git push -u origin <your-documentation-branch>
```

Open a Pull Request to `main` for review. Never include `.env`, `docker-compose.override.yml`, `application_default_credentials.json`, `.masar-jwt-key`, or `.masar-fernet-key` in a PR.

## 9. Current MVP scope / important limitation

Our current pipeline performs an **idempotent table reload** using `WRITE_TRUNCATE`: rerunning the same files replaces BigQuery raw tables instead of appending duplicate copies of rows. **It does not yet skip unchanged Excel files**, so it does not fully implement file-level deduplication. Do not describe those two behaviors as equivalent. The latter is a possible follow-up enhancement, subject to team/instructor approval.

---

**Quick check:** `docker compose ps` → Airflow UI → one manual Trigger → all 11 tasks green → pause DAG. If something fails, inspect the specific failed task and its logs first.
