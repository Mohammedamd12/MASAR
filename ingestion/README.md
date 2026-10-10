# Data ingestion: Excel traffic, government events, Open-Meteo weather

Prepares the three data sources for Airflow and BigQuery. Code, column names and output files are all in English.
The Excel files are in Arabic, so the Arabic-to-English tables are in `labels.py` (written as escape codes, so the repo has no Arabic script).

## Run it (from the repo root, in the VS Code terminal)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r ingestion/requirements.txt

python -m ingestion.inspect_excel        # writes docs/excel_inspection.md
python -m ingestion.run --skip-weather   # traffic + events only (no internet needed)
python -m ingestion.run                  # everything, including the Open-Meteo weather
python -m pytest -v                      # tests
```

The `.xlsx` files are read from the repo root. Use `--input-dir <folder>` if they are somewhere else.
The results are written to `data/processed/` (CSV, UTF-8, dates like 2026-01-31).

## The files

| File | What it does |
|---|---|
| `config.py` | paths, file name patterns, date window (Jan-Jun 2026), API address |
| `excel_utils.py` | finds the header row of a sheet, renames the columns to English, cleans Arabic text |
| `labels.py` | Arabic to English tables (column headers, months, directions, city names, event types) |
| `event_names_en.csv` | English name of every government event request |
| `seeds.py` | loads the seed CSV files |
| `traffic.py` | checks the traffic rows and combines them into one monthly table |
| `events.py` | checks the event rows, removes duplicates, translates, applies the city rule |
| `weather.py` | downloads daily weather from Open-Meteo for each city |
| `run.py` | runs everything and writes the CSV files |
| `inspect_excel.py` | documents every sheet and column of the Excel files |

Seed files (loaded by `dbt seed`): `dbt/seeds/industrial_cities.csv` (12 cities with coordinates),
`dbt/seeds/regions.csv` (5 regions), `dbt/seeds/event_cities.csv` (which industrial cities an event city affects).

## Output files

| File | One row is | Notes |
|---|---|---|
| `traffic_monthly_clean.csv` | one industrial city in one month | `entries`, `exits`, `quality_flag`, `source_file`, `layout_version` |
| `traffic_rejects.csv` | one rejected Excel row | `reject_reason`, `source_row` (the row number in Excel) |
| `traffic_coverage.csv` | one city + month | `has_data` is True or False for all 12 x 6 combinations |
| `traffic_sheet_log.csv` | one Excel sheet | shows which sheets were read or skipped |
| `events_clean.csv` | one government event | see the columns below |
| `event_days.csv` | one event + industrial city + day | only events that affect a city |
| `events_rejects.csv` | one rejected event row | `reject_reason` |
| `events_sheet_log.csv` | one Excel sheet | shows which sheets were read or skipped |
| `weather_daily.csv` | one city + day | `weather_missing` is True when there is no weather value |

### Columns that need an explanation

- `gov_request_number`: the government's own ID of the event request (for example `GOV-2026-0005`). Each event has exactly one.
  It is the key used to remove duplicates and to join `event_days.csv` to `events_clean.csv`.
- `event_name`: the event name in English. The Excel files only have Arabic names, so the English names were translated
  once and saved in `event_names_en.csv`. A new request number that is not in that file shows `Not translated`
  and the run prints a warning. Please spot-check the translations.
- `layout_version`: describes the shape of the Excel sheet the row came from, for example `6 columns, header on row 2`.
  Q1 and Q2 have different shapes, so this tells you which layout a row came from.
- `source_file`, `source_row`: the Excel file and the row number, so any value can be checked in the original file.
- `quality_flag`: a warning on a traffic month. The numbers are not changed. `entry_exit_imbalance` means entries and
  exits differ by more than 30%. `repeated_previous_month_values` means the numbers are exactly the same as last month.
- `relevance`: `city`, `region` or `none` (see the rule below). `industrial_city_codes` lists the affected cities, like `DMM1|DMM2`.

## What the real files look like

- Traffic files are monthly. One row = city + month + direction (entry or exit) + vehicle count.
  Q1 (`Traffic_4`) has a 6th column with a camera footnote; Q2 (`Traffic_3`) has 5 columns.
  Only 48 of the 72 city-months exist (for example Al-Kharj and Zulfi have no Q2 data, Hafr Al-Batin has no Q1 data).
  Missing months are reported in `traffic_coverage.csv`, never filled in.
- Event files: Q1 has 10 columns (with attendance), Q2 has 9 (no attendance). Q2 repeats many Q1 events.

## Traffic rules

- The header row is found by the column names, so title rows, notes and column order do not matter.
- Bad rows are never dropped silently. They go to `traffic_rejects.csv` with a reason: `unknown_city`, `invalid_month`,
  `invalid_direction`, `invalid_count`, `missing_count`, `negative_count`, `non_integer_count`, `outside_window`, `duplicate_row`.
- If only entries or only exits exist for a month, the other one stays empty (NULL), not 0.

## Events source and city relevance rule

Source: `Public Sector Events Q1 2026.xlsx` and `Public Sector Events Q2 2026.xlsx` (approved government event requests).
<!-- TODO before the pull request: confirm the publisher and licence -->

Cleaning: an event is rejected if it has no valid start date, ends before it starts, or is outside Jan-Jun 2026.
Duplicates are found with `gov_request_number`, and the copy that has attendance is kept.
If an event has no end date it is treated as a one-day event.

City relevance rule, based on the city where the event is held (`dbt/seeds/event_cities.csv`):
1. `city`: the event is in the city of an industrial city, so it counts for that industrial city only
   (Riyadh -> RUH2 and RUH3, Jeddah -> JED, Dammam -> DMM1 and DMM2, Buraydah -> QAS, Al-Majmaah -> SDR, ...).
2. `region`: the event is in the same region as industrial cities but in another city (for example Khobar),
   so it counts for every industrial city of that region.
3. `none`: any other region. The event stays in `events_clean.csv` but is not in `event_days.csv`.

## Weather

Open-Meteo Historical Weather API (`archive-api.open-meteo.com/v1/archive`): daily maximum, minimum and mean
temperature, rain, wind speed and wind gusts. Timezone `Asia/Riyadh`, 2026-01-01 to 2026-06-30, one request per city
using the coordinates in `industrial_cities.csv`. The raw answers are saved in `data/raw/open_meteo/`.
Missing or impossible values stay empty and `weather_missing` is set. Nothing is guessed.

The city coordinates are estimates (about 1 to 10 km). The weather data is on a grid of about 10 km, so this changes
the weather very little, but check the coordinates against the official city locations before the final delivery.
