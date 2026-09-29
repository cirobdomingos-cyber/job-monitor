"""
Central configuration for the job monitor.
Edit this file to tune filters without touching any scraper logic.
"""

# ---------------------------------------------------------------------------
# Title keywords — job must match at least ONE (case-insensitive substring)
# Tip: keep these specific to avoid intern/junior noise
# ---------------------------------------------------------------------------
TITLE_KEYWORDS: list[str] = [
    "data analyst",
    "senior data analyst",
    "analytics engineer",
    "lead analyst",
    "data product",
    "product analyst",
    "analytics lead",
    "senior analyst",
    "business intelligence",
    "bi engineer",
    "analytics manager",
    "data product manager",
]

# ---------------------------------------------------------------------------
# Title EXCLUSIONS — job is dropped if title contains ANY of these
# (checked before body keywords; catches intern/junior noise)
# ---------------------------------------------------------------------------
TITLE_EXCLUSIONS: list[str] = [
    "intern",
    "internship",
    "junior",
    "jr.",
    "entry level",
    "entry-level",
    "graduate",
    "apprentice",
    "trainee",
    "staff augmentation",   # body-shop roles
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
    "data platform",
    "data modeling",
    "data model",
]

# ---------------------------------------------------------------------------
# Geo exclusion phrases — job is dropped if ANY appear in
# description or location (case-insensitive)
# ---------------------------------------------------------------------------
GEO_EXCLUSIONS: list[str] = [
    # NOTE: "401k" / "401(k)" removed — too broad, causes false positives.
    # Many global companies list 401k as a US benefit while still hiring internationally.
    # Use explicit restriction phrases instead:

    # --- US-only phrases ---
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
    "north america only",
    "canada or us only",
    "canada and us only",
    "remote - us",          # "Remote - US" in WWR location tags
    "remote (us)",          # "Remote (US)" in job descriptions
    "headquarters: remote (us)",
    "usa only",
    "us-based only",
    "open to us residents",
    "open to us applicants",

    # --- Non-LATAM country-specific restrictions (Himalayas locationRestrictions) ---
    "germany only",
    "uk only",
    "united kingdom only",
    "australia only",
    "india only",
    "china only",
    "france only",
    "netherlands only",
    "spain only",
    "poland only",
    "czech republic only",
    "romania only",
    "portugal only",
    "italy only",
    "sweden only",
    "norway only",
    "denmark only",
    "finland only",
    "israel only",
    "singapore only",
    "new zealand only",
    "south africa only",
    "nigeria only",
    "kenya only",
    "pakistan only",
    "philippines only",
    "ukraine only",
    "canada only",
    "eu only",
    "europe only",
    "emea only",
    "apac only",
    "asia only",
]

# ---------------------------------------------------------------------------
# Scraper toggles — set False to disable a source
# ---------------------------------------------------------------------------
ENABLED_SCRAPERS: dict[str, bool] = {
    "himalayas": True,
    "remotive": True,
    "weworkremotely": True,
    "remoteok": True,
    "greenhouse": True,
    "remoteco": False,      # disabled: times out in sandboxed environments
}
