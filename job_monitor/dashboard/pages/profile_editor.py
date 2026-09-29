"""
Profile Editor — Create, edit, and delete search profiles from the UI.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from job_monitor.core.profile import (  # noqa: E402
    FilterConfig,
    Profile,
    ScoringConfig,
    delete_profile,
    list_profiles,
    load_profile,
    save_profile,
)

st.set_page_config(page_title="Profile Editor", page_icon="✏️", layout="wide")
st.title("✏️ Profile Editor")
st.caption("Create a new profile or edit an existing one. All changes are saved to YAML files in the profiles/ directory.")

ALL_SCRAPERS = ["himalayas", "remotive", "weworkremotely", "remoteok", "greenhouse", "remoteco"]

# ---------------------------------------------------------------------------
# Mode selector: New or Edit
# ---------------------------------------------------------------------------
available = list_profiles()
mode = st.radio("Mode", ["Edit existing", "Create new"], horizontal=True)

if mode == "Edit existing":
    if not available:
        st.warning("No profiles found. Create one first.")
        st.stop()
    selected_name = st.selectbox("Select profile to edit", available)
    profile = load_profile(selected_name)
    file_name = selected_name
else:
    profile = Profile(
        name="",
        filters=FilterConfig(),
        scoring=ScoringConfig(),
        enabled_scrapers={s: True for s in ALL_SCRAPERS[:5]},
    )
    file_name = ""

st.markdown("---")

# ---------------------------------------------------------------------------
# Profile name & file name
# ---------------------------------------------------------------------------
col_name, col_file = st.columns(2)
with col_name:
    profile_display_name = st.text_input(
        "Profile display name",
        value=profile.name,
        placeholder="e.g. Senior Data Analyst — LATAM",
    )
with col_file:
    save_as = st.text_input(
        "File name (no extension)",
        value=file_name,
        placeholder="e.g. my_search",
        help="This becomes profiles/<name>.yaml",
    )

# ---------------------------------------------------------------------------
# Tabs for organized editing
# ---------------------------------------------------------------------------
tab_filters, tab_scoring, tab_scrapers = st.tabs(["Filters", "Scoring", "Scrapers"])

# ===== FILTERS TAB =====
with tab_filters:
    st.subheader("Title Keywords")
    st.caption("Job title must contain at least ONE of these (case-insensitive). One per line.")
    title_keywords_text = st.text_area(
        "Title keywords",
        value="\n".join(profile.filters.title_keywords),
        height=200,
        label_visibility="collapsed",
    )

    st.subheader("Title Exclusions")
    st.caption("Job is DROPPED if title contains ANY of these. One per line.")
    title_exclusions_text = st.text_area(
        "Title exclusions",
        value="\n".join(profile.filters.title_exclusions),
        height=150,
        label_visibility="collapsed",
    )

    st.subheader("Body / Description Keywords")
    st.caption("Description or tags must contain at least ONE of these. One per line.")
    body_keywords_text = st.text_area(
        "Body keywords",
        value="\n".join(profile.filters.body_keywords),
        height=200,
        label_visibility="collapsed",
    )

    st.subheader("Geo Exclusions")
    st.caption("Job is DROPPED if description/location contains ANY of these phrases. One per line.")
    geo_exclusions_text = st.text_area(
        "Geo exclusions",
        value="\n".join(profile.filters.geo_exclusions),
        height=200,
        label_visibility="collapsed",
    )

# ===== SCORING TAB =====
with tab_scoring:
    st.subheader("Salary Range (USD)")
    sal_col1, sal_col2 = st.columns(2)
    with sal_col1:
        salary_min = st.number_input(
            "Minimum ($)",
            min_value=0, max_value=500_000, step=5_000,
            value=profile.scoring.salary_min,
        )
    with sal_col2:
        salary_max = st.number_input(
            "Maximum ($)",
            min_value=0, max_value=500_000, step=5_000,
            value=profile.scoring.salary_max,
        )

    st.markdown("---")
    st.subheader("Seniority Keywords")
    sen_col1, sen_col2 = st.columns(2)
    with sen_col1:
        st.caption("High seniority (20 pts) — one per line")
        seniority_high_text = st.text_area(
            "High seniority",
            value="\n".join(profile.scoring.seniority_high),
            height=150,
            label_visibility="collapsed",
        )
    with sen_col2:
        st.caption("Mid seniority (10 pts) — one per line")
        seniority_mid_text = st.text_area(
            "Mid seniority",
            value="\n".join(profile.scoring.seniority_mid),
            height=150,
            label_visibility="collapsed",
        )

    st.markdown("---")
    st.subheader("Tech Stack Keywords & Weights")
    st.caption(
        "One keyword per line, format: `keyword: weight` (weight 1-3). "
        f"Total score is capped at {profile.scoring.stack_max_score}."
    )
    stack_lines = [f"{kw}: {w}" for kw, w in profile.scoring.stack_keywords.items()]
    stack_keywords_text = st.text_area(
        "Stack keywords",
        value="\n".join(stack_lines),
        height=300,
        label_visibility="collapsed",
    )
    stack_max = st.number_input(
        "Stack max score",
        min_value=1, max_value=50, step=1,
        value=profile.scoring.stack_max_score,
    )

    st.markdown("---")
    st.subheader("Location Signals")
    loc_col1, loc_col2, loc_col3 = st.columns(3)
    with loc_col1:
        st.caption("Preferred (20 pts) — one per line")
        location_preferred_text = st.text_area(
            "Preferred locations",
            value="\n".join(profile.scoring.location_preferred),
            height=200,
            label_visibility="collapsed",
        )
    with loc_col2:
        st.caption("Neutral regions (8 pts) — one per line")
        location_neutral_text = st.text_area(
            "Neutral regions",
            value="\n".join(profile.scoring.location_neutral_regions),
            height=200,
            label_visibility="collapsed",
        )
    with loc_col3:
        st.caption("Excluded (0 pts) — one per line")
        location_excluded_text = st.text_area(
            "Excluded locations",
            value="\n".join(profile.scoring.location_excluded),
            height=200,
            label_visibility="collapsed",
        )

    st.markdown("---")
    st.subheader("Company Signals")
    comp_col1, comp_col2 = st.columns(2)
    with comp_col1:
        st.caption("High signal (3 pts each) — one per line")
        company_high_text = st.text_area(
            "Company high signals",
            value="\n".join(profile.scoring.company_high),
            height=200,
            label_visibility="collapsed",
        )
    with comp_col2:
        st.caption("Mid signal (1 pt each) — one per line")
        company_mid_text = st.text_area(
            "Company mid signals",
            value="\n".join(profile.scoring.company_mid),
            height=200,
            label_visibility="collapsed",
        )

# ===== SCRAPERS TAB =====
with tab_scrapers:
    st.subheader("Enabled Scrapers")
    st.caption("Toggle which job sources to scrape.")
    scraper_toggles = {}
    for scraper in ALL_SCRAPERS:
        scraper_toggles[scraper] = st.checkbox(
            scraper.replace("_", " ").title(),
            value=profile.enabled_scrapers.get(scraper, False),
            key=f"scraper_{scraper}",
        )


# ---------------------------------------------------------------------------
# Helper: parse text areas into lists
# ---------------------------------------------------------------------------

def _lines(text: str) -> list[str]:
    """Split text area into non-empty trimmed lines."""
    return [line.strip() for line in text.strip().splitlines() if line.strip()]


def _parse_stack_keywords(text: str) -> dict[str, int]:
    """Parse 'keyword: weight' lines into a dict."""
    result = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            parts = line.rsplit(":", 1)
            keyword = parts[0].strip()
            try:
                weight = int(parts[1].strip())
            except ValueError:
                weight = 1
            if keyword:
                result[keyword] = weight
        else:
            result[line] = 1
    return result


# ---------------------------------------------------------------------------
# Save / Delete buttons
# ---------------------------------------------------------------------------
st.markdown("---")

btn_col1, btn_col2, btn_col3 = st.columns([2, 1, 1])

with btn_col1:
    if st.button("💾 Save profile", type="primary", use_container_width=True):
        if not save_as.strip():
            st.error("File name is required.")
        elif not profile_display_name.strip():
            st.error("Profile display name is required.")
        else:
            new_profile = Profile(
                name=profile_display_name.strip(),
                filters=FilterConfig(
                    title_keywords=_lines(title_keywords_text),
                    title_exclusions=_lines(title_exclusions_text),
                    body_keywords=_lines(body_keywords_text),
                    geo_exclusions=_lines(geo_exclusions_text),
                ),
                scoring=ScoringConfig(
                    salary_min=int(salary_min),
                    salary_max=int(salary_max),
                    seniority_high=_lines(seniority_high_text),
                    seniority_mid=_lines(seniority_mid_text),
                    stack_keywords=_parse_stack_keywords(stack_keywords_text),
                    stack_max_score=int(stack_max),
                    location_preferred=_lines(location_preferred_text),
                    location_neutral_regions=_lines(location_neutral_text),
                    location_excluded=_lines(location_excluded_text),
                    company_high=_lines(company_high_text),
                    company_mid=_lines(company_mid_text),
                ),
                enabled_scrapers=scraper_toggles,
            )
            filepath = save_profile(new_profile, save_as.strip())
            st.success(f"Saved to `{filepath.name}`")
            st.cache_data.clear()

with btn_col2:
    if mode == "Create new":
        # "Duplicate from" helper
        if available:
            dup_source = st.selectbox("Copy from", ["(blank)"] + available, key="dup_from")
            if st.button("📋 Load template"):
                st.query_params["dup"] = dup_source
                st.rerun()

with btn_col3:
    if mode == "Edit existing" and selected_name != "default":
        if st.button("🗑️ Delete profile", type="secondary"):
            if delete_profile(selected_name):
                st.success(f"Deleted `{selected_name}.yaml`")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Profile not found.")
