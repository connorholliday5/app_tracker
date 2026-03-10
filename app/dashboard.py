from __future__ import annotations

import pandas as pd
import streamlit as st

from app.database import get_all_applications, get_dashboard_metrics


def render_metrics() -> None:
    metrics = get_dashboard_metrics()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Applications", metrics["total_applications"])
    col2.metric("Interviews", metrics["interviews"])
    col3.metric("Rejections", metrics["rejections"])
    col4.metric("Follow-Ups Needed", metrics["follow_ups_needed"])


def render_application_table(status_filter: str) -> None:
    applications = (
        get_all_applications()
        if status_filter == "all"
        else get_all_applications(status=status_filter)
    )

    st.subheader("Applications")

    if not applications:
        st.info("No applications found for the selected filter.")
        return

    df = pd.DataFrame([dict(row) for row in applications])

    def highlight_follow_ups(row):
        if row["follow_up_needed"] == 1:
            return ["background-color: #fff3cd"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df.style.apply(highlight_follow_ups, axis=1),
        use_container_width=True,
    )

    follow_up_df = df[df["follow_up_needed"] == 1]
    if not follow_up_df.empty:
        st.warning("Highlighted rows need follow-up based on the 14-day applied rule.")
