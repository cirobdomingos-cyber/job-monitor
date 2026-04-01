"""
Streamlit dashboard for the job monitor.

Run with:
    streamlit run dashboard/app.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

# Make sure the project root is on the path when running directly
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from job_monitor.storage.db import init_db, load_jobs  # noqa: E402

# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Job Monitor",
    page_icon="🔍",
    layout="wide",
)
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300)  # refresh cache every 5 min
def get_jobs(source_filter, days_back, limit) -> pd.DataFrame:
    init_db()
    since = datetime.utcnow() - timedelta(days=days_back) if days_back else None
    raw = load_jobs(source=source_filter or None, since=since, limit=limit)
    if not raw:
        return pd.DataFrame()

    df = pd.DataFrame(raw)
    df["tags"] = df["tags"].apply(lambda v: ", ".join(json.loads(v)) if v else "")
    df["posted_at"] = pd.to_datetime(df["posted_at"], errors="coerce")
    df["fetched_at"] = pd.to_datetime(df["fetched_at"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Sidebar — filters
# ---------------------------------------------------------------------------
st.sidebar.title("🔍 Job Monitor")
st.sidebar.markdown("---")

source_options = ["", "himalayas", "remotive", "weworkremotely", "remoteco"]
source_filter = st.sidebar.selectbox("Source", source_options, format_func=lambda x: x or "All sources")

days_back = st.sidebar.slider("Show jobs from last N days", min_value=1, max_value=30, value=7)

keyword_filter = st.sidebar.text_input("Search keyword (title/company)", "")

limit = st.sidebar.number_input("Max results", min_value=10, max_value=1000, value=200, step=10)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh data"):
    st.cache_data.clear()

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("🔍 Remote Job Monitor")
st.caption(f"Filtered for Senior Data & AI roles · Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")

df = get_jobs(source_filter, days_back, limit)

if df.empty:
    st.info("No jobs in the database yet. Run `python runner.py` first.")
    st.stop()

# Apply keyword filter
if keyword_filter:
    mask = (
        df["title"].str.contains(keyword_filter, case=False, na=False)
        | df["company"].str.contains(keyword_filter, case=False, na=False)
        | df["tags"].str.contains(keyword_filter, case=False, na=False)
    )
    df = df[mask]

# ---------------------------------------------------------------------------
# Metrics row
# ---------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total jobs", len(df))
col2.metric("Sources", df["source"].nunique() if not df.empty else 0)
col3.metric("Companies", df["company"].nunique() if not df.empty else 0)
col4.metric(
    "Newest",
    df["fetched_at"].max().strftime("%b %d") if not df.empty and not df["fetched_at"].isna().all() else "—",
)

st.markdown("---")

# ---------------------------------------------------------------------------
# Jobs table
# ---------------------------------------------------------------------------
if not df.empty:
    display_cols = ["title", "company", "source", "location", "salary", "tags", "fetched_at", "url"]
    display_cols = [c for c in display_cols if c in df.columns]
    display_df = df[display_cols].copy()

    # Make URL clickable
    display_df["url"] = display_df["url"].apply(lambda u: f'<a href="{u}" target="_blank">🔗 Link</a>')

    st.write(
        display_df.to_html(escape=False, index=False),
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ---------------------------------------------------------------------------
    # Source breakdown chart
    # ---------------------------------------------------------------------------
    with st.expander("📊 Breakdown by source", expanded=True):
        source_counts = df["source"].value_counts().reset_index()
        source_counts.columns = ["source", "count"]
        st.bar_chart(source_counts.set_index("source"))

    # ---------------------------------------------------------------------------
    # CSV export
    # ---------------------------------------------------------------------------
    csv = df.drop(columns=["id", "url_hash", "description"], errors="ignore").to_csv(index=False)
    st.download_button(
        label="⬇️ Export to CSV",
        data=csv,
        file_name=f"jobs_{datetime.utcnow().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

    # ---------------------------------------------------------------------------
    # Job detail expander
    # ---------------------------------------------------------------------------
    with st.expander("📄 View job descriptions"):
        job_titles = df["title"] + " @ " + df["company"]
        selected = st.selectbox("Select a job", job_titles.tolist())
        if selected:
            idx = job_titles[job_titles == selected].index[0]
            row = df.loc[idx]
            st.subheader(f"{row['title']} @ {row['company']}")
            st.markdown(f"**Source:** {row['source']}  |  **Location:** {row.get('location','—')}  |  **Salary:** {row.get('salary','—')}")
            st.markdown(f"[Open job posting]({row['url']})")
            st.markdown("---")
            st.markdown(row.get("description", "_No description available._") or "_No description available._")
