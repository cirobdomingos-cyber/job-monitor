# Job Monitor

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?logo=streamlit&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Storage-003B57?logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/Status-Local%20Project-2E7D32)

A Python-based remote job monitoring pipeline that:
- Scrapes jobs from multiple remote job sources
- Filters for data and analytics roles using configurable keyword rules
- De-duplicates jobs using URL hashing
- Persists results into SQLite
- Visualizes saved jobs in a Streamlit dashboard

## Sources

Current scraper sources:
- himalayas
- remotive
- weworkremotely
- remoteco

## Requirements

- Python 3.11+
- pip

## Setup

From the repository root:

```bash
python -m venv .venv
# Windows PowerShell
. .venv/Scripts/Activate.ps1
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

Notes:
- `pip install -e .` enables package imports like `import job_monitor...` from this repo.
- The project metadata is in `pyproject.toml`.

## Environment (Optional)

This project currently runs without required environment variables, but supports an optional `DB_PATH` override for SQLite location.

Set it in your shell (PowerShell):

```powershell
$env:DB_PATH = "job_monitor/data/jobs.db"
```

Or add it to a `.env` file in the repository root:

```env
# Optional custom DB location
DB_PATH=job_monitor/data/jobs.db
```

Current behavior:
- If `DB_PATH` is set as an environment variable, it is used.
- Otherwise, if `DB_PATH` exists in `.env`, it is used.
- Otherwise, the default path is `job_monitor/data/jobs.db`.

## Run The Scrapers

Run all enabled sources:

```bash
python runner.py
```

Run only selected sources:

```bash
python runner.py --source himalayas remotive
```

Dry run (fetch + filter, no DB writes):

```bash
python runner.py --dry-run
```

## Filtering Rules

Filtering is applied in this order:
1. Title must match at least one `TITLE_KEYWORDS` entry
2. Description/tags must match at least one `BODY_KEYWORDS` entry
3. Job must not match any `GEO_EXCLUSIONS` phrase

Edit these rules in:
- `job_monitor/config.py`

## Data Storage

SQLite database path:
- `job_monitor/data/jobs.db`

Tables:
- `jobs`: saved job records
- `seen_urls`: URL hashes used for de-duplication
- `runs`: run-level counters and timestamps

If you want to reset local state, stop running processes and remove `job_monitor/data/jobs.db`.

## Dashboard

Start the Streamlit dashboard:

```bash
streamlit run job_monitor/dashboard/app.py
```

Dashboard features include:
- Source/day/keyword filtering
- Source breakdown chart
- CSV export
- Job detail viewer

### Screenshot

Add a dashboard screenshot to this section after your first run, for example:

```md
![Job Monitor Dashboard](docs/dashboard.png)
```

## Project Layout

```text
job_monitor/
  config.py
  core/
    models.py
    filters.py
    dedup.py
  scrapers/
    base.py
    himalayas.py
    remotive.py
    weworkremotely.py
    remoteco.py
  storage/
    db.py
  dashboard/
    app.py
runner.py
requirements.txt
pyproject.toml
```

## Troubleshooting

- `ModuleNotFoundError: job_monitor`
  - Run `pip install -e .` from the repo root.

- Dashboard shows no jobs
  - Run `python runner.py` first to populate the database.

- No new jobs found
  - This may be expected if all fetched URLs were already seen in previous runs.

## License

No license file is currently included in this repository.
 