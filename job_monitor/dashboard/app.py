"""
Streamlit dashboard for the job monitor.

Run with:
    streamlit run job_monitor/dashboard/app.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from job_monitor.core.profile import load_profile, list_profiles  # noqa: E402
from job_monitor.storage.db import init_db, load_jobs  # noqa: E402

st.set_page_config(page_title="Job Monitor", page_icon="🔍", layout="wide")


def _score_badge(score) -> str:
    if score is None or (isinstance(score, float) and pd.isna(score)):
        return "—"
    s = int(score)
    if s >= 80:
        return f"🟢 {s}"
    if s >= 60:
        return f"🟡 {s}"
    if s >= 40:
        return f"🟠 {s}"
    return f"🔴 {s}"


def _location_score(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        return json.loads(raw.replace("'", '"')).get("location")
    except Exception:
        return None


def _breakdown_str(raw: str | None) -> str:
    if not raw:
        return ""
    try:
        d = json.loads(raw.replace("'", '"'))
        return (
            f"Seniority {d.get('seniority',0)} | "
            f"Stack {d.get('stack',0)} | "
            f"Salary {d.get('salary',0)} | "
            f"Location {d.get('location',0)} | "
            f"Company {d.get('company',0)}"
        )
    except Exception:
        return ""


@st.cache_data(ttl=300)
def get_jobs(source_filter, days_back, min_score, limit) -> pd.DataFrame:
    init_db()
    since = datetime.utcnow() - timedelta(days=days_back) if days_back else None
    raw = load_jobs(
        source=source_filter or None,
        since=since,
        min_score=min_score if min_score > 0 else None,
        limit=limit,
    )
    if not raw:
        return pd.DataFrame()

    df = pd.DataFrame(raw)
    df["tags"] = df["tags"].apply(lambda v: ", ".join(json.loads(v)) if v else "")
    df["posted_at"] = pd.to_datetime(df["posted_at"], errors="coerce")
    df["fetched_at"] = pd.to_datetime(df["fetched_at"], errors="coerce")
    df["score"] = pd.to_numeric(df.get("score"), errors="coerce")
    df["score_badge"] = df["score"].apply(_score_badge)
    df["breakdown"] = df.get("score_breakdown", pd.Series(dtype=str)).apply(_breakdown_str)
    df["location_score"] = df.get("score_breakdown", pd.Series(dtype=str)).apply(_location_score)
    df = df.sort_values("score", ascending=False, na_position="last")
    return df


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("🔍 Job Monitor")
st.sidebar.markdown("---")

# Profile selector
available_profiles = list_profiles()
profile_name = st.sidebar.selectbox(
    "Profile",
    available_profiles or ["default"],
    help="Select a search profile (YAML files in profiles/ directory)",
)
profile = load_profile(profile_name)
st.sidebar.caption(f"Active: **{profile.name}**")

st.sidebar.markdown("---")

source_options = ["", "himalayas", "remotive", "weworkremotely", "remoteok", "greenhouse", "remoteco"]
source_filter = st.sidebar.selectbox("Source", source_options, format_func=lambda x: x or "All sources")
days_back = st.sidebar.slider("Last N days", 1, 30, 7)
min_score = st.sidebar.slider("Min score", 0, 100, 0, step=5)
keyword_filter = st.sidebar.text_input("Search keyword (title/company/tags)", "")
salary_only = st.sidebar.checkbox("Has salary listed")
location_friendly = st.sidebar.checkbox(
    "Preferred locations only",
    help="Keeps only jobs matching your profile's preferred locations",
)
limit = st.sidebar.number_input("Max results", 10, 1000, 200, step=10)

st.sidebar.markdown("---")

# Show profile summary
with st.sidebar.expander("📋 Profile details"):
    st.markdown(f"**Title keywords:** {len(profile.filters.title_keywords)}")
    st.markdown(f"**Body keywords:** {len(profile.filters.body_keywords)}")
    st.markdown(f"**Stack keywords:** {len(profile.scoring.stack_keywords)}")
    st.markdown(f"**Salary range:** ${profile.scoring.salary_min:,}–${profile.scoring.salary_max:,}")
    st.markdown(f"**Geo exclusions:** {len(profile.filters.geo_exclusions)}")

if st.sidebar.button("🔄 Refresh"):
    st.cache_data.clear()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
st.title("🔍 Remote Job Monitor")
st.caption(f"{profile.name} · Scored for your profile · {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")

df = get_jobs(source_filter, days_back, min_score, int(limit))

if df.empty:
    st.info("No jobs in the database yet. Run `python runner.py` first.")
    st.stop()

if keyword_filter:
    mask = (
        df["title"].str.contains(keyword_filter, case=False, na=False)
        | df["company"].str.contains(keyword_filter, case=False, na=False)
        | df["tags"].str.contains(keyword_filter, case=False, na=False)
    )
    df = df[mask]

if salary_only:
    df = df[df["salary"].notna() & (df["salary"].astype(str).str.strip() != "")]

if location_friendly:
    df = df[df["location_score"].isna() | (df["location_score"] >= 10)]

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total", len(df))
c2.metric("Strong match (≥80)", int((df["score"] >= 80).sum()) if "score" in df else "—")
c3.metric("Good match (≥60)", int((df["score"] >= 60).sum()) if "score" in df else "—")
c4.metric("Sources", df["source"].nunique())
c5.metric("Avg score", f"{df['score'].mean():.0f}" if "score" in df and not df["score"].isna().all() else "—")

st.markdown("---")

# ---------------------------------------------------------------------------
# Score distribution chart
# ---------------------------------------------------------------------------
with st.expander("📊 Score distribution", expanded=False):
    if "score" in df and not df["score"].isna().all():
        bins = pd.cut(df["score"], bins=[0, 40, 60, 80, 100], labels=["Weak", "Possible", "Good", "Strong"])
        st.bar_chart(bins.value_counts().sort_index())

# ---------------------------------------------------------------------------
# Jobs table (sorted by score desc)
# ---------------------------------------------------------------------------
display_cols = ["score_badge", "title", "company", "source", "location", "salary", "breakdown", "fetched_at", "url"]
display_cols = [c for c in display_cols if c in df.columns]
display_df = df[display_cols].copy()
display_df = display_df.rename(columns={
    "score_badge": "Score",
    "breakdown": "Score breakdown",
    "fetched_at": "Found",
})
display_df["url"] = display_df["url"].apply(lambda u: f'<a href="{u}" target="_blank">Open</a>')

st.write(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# Job detail
# ---------------------------------------------------------------------------
with st.expander("📄 Job detail & score breakdown"):
    job_labels = df["title"] + " @ " + df["company"] + " [" + df["score_badge"] + "]"
    selected = st.selectbox("Select job", job_labels.tolist())
    if selected:
        idx = job_labels[job_labels == selected].index[0]
        row = df.loc[idx]

        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(f"{row['title']} @ {row['company']}")
            st.markdown(
                f"**Source:** {row['source']}  |  "
                f"**Location:** {row.get('location', '—')}  |  "
                f"**Salary:** {row.get('salary', '—')}"
            )
            st.markdown(f"[Open job posting]({row['url']})")
        with col2:
            score_val = row.get("score")
            st.metric("Match score", f"{int(score_val)}/100" if pd.notna(score_val) else "—")
            if row.get("score_breakdown"):
                try:
                    bd = json.loads(row["score_breakdown"].replace("'", '"'))
                    st.markdown(
                        f"- Seniority: **{bd.get('seniority', 0)}/20**\n"
                        f"- Tech stack: **{bd.get('stack', 0)}/25**\n"
                        f"- Salary fit: **{bd.get('salary', 0)}/20**\n"
                        f"- Location: **{bd.get('location', 0)}/20**\n"
                        f"- Company fit: **{bd.get('company', 0)}/15**"
                    )
                except Exception:
                    pass

        st.markdown("---")
        st.markdown(row.get("description", "_No description._") or "_No description._")

# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------
csv = df.drop(columns=["id", "url_hash", "description", "score_badge"], errors="ignore").to_csv(index=False)
st.download_button("⬇️ Export CSV", csv, f"jobs_{datetime.utcnow().strftime('%Y%m%d')}.csv", "text/csv")
