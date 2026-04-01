"""
Central configuration for the job monitor.
Edit this file to tune filters without touching any scraper logic.
"""

# ---------------------------------------------------------------------------
# Title keywords  — job must match at least ONE (case-insensitive substring)
# ---------------------------------------------------------------------------
TITLE_KEYWORDS: list[str] = [
    "data analyst",
    "analytics engineer",
    "lead analyst",
    "data product",
    "product analyst",
    "analytics lead",
    "senior analyst",
    "business intelligence",
    "bi engineer",
    "data engineer",       # keep broad; filter tightens on description
]

# ---------------------------------------------------------------------------
# Body / description keywords — job must match at least ONE
# ---------------------------------------------------------------------------
BODY_KEYWORDS: list[str] = [
    "sql",
    "python",
    "databricks",
    "power bi",
    "powerbi",
    "tableau",
    "dbt",
    "analytics",
    "data pipeline",
    "spark",
    "looker",
    "metabase",
    "airflow",
    "bigquery",
    "snowflake",
    "redshift",
    "data warehouse",
]

# ---------------------------------------------------------------------------
# Geo exclusion phrases — job is dropped if ANY of these appear in
# description or location (case-insensitive)
# ---------------------------------------------------------------------------
GEO_EXCLUSIONS: list[str] = [
    "401k",
    "401(k)",
    "us work authorization",
    "must be located in the us",
    "must reside in the us",
    "must be based in the us",
    "us only",
    "united states only",
    "must be authorized to work in the united states",
    "legally authorized to work in the us",
    "eligible to work in the us",
    "must be a us citizen",
    "us citizens only",
    "north america only",           # too restrictive for BR timezone
    "canada or us only",
]

# ---------------------------------------------------------------------------
# Scraper toggles — set False to disable a source
# ---------------------------------------------------------------------------
ENABLED_SCRAPERS: dict[str, bool] = {
    "himalayas": True,
    "remotive": True,
    "weworkremotely": True,
    "remoteco": True,
}
