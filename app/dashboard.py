from __future__ import annotations

import pandas as pd
import streamlit as st

from app.database import get_all_applications, get_dashboard_metrics


DISPLAY_COLUMNS = [
    "id",
    "university",
    "department_lab",
    "job_title",
    "job_id",
    "location",
    "application_date",
    "status",
    "interview_stage",
    "contact_name",
    "contact_email",
    "follow_up_date",
    "follow_up_needed",
    "notes",
]


def _get_all_df() -> pd.DataFrame:
    applications = get_all_applications()
    if not applications:
        return pd.DataFrame()
    return pd.DataFrame([dict(row) for row in applications])


def _build_dataframe(status_filter: str) -> pd.DataFrame:
    applications = (
        get_all_applications()
        if status_filter == "all"
        else get_all_applications(status=status_filter)
    )

    if not applications:
        return pd.DataFrame()

    df = pd.DataFrame([dict(row) for row in applications])

    for column in DISPLAY_COLUMNS:
        if column not in df.columns:
            df[column] = None

    df = df[DISPLAY_COLUMNS].copy()

    df["follow_up_needed"] = df["follow_up_needed"].apply(
        lambda value: "Yes" if int(value) == 1 else "No"
    )

    df = df.rename(
        columns={
            "id": "ID",
            "university": "University",
            "department_lab": "Department / Lab",
            "job_title": "Job Title",
            "job_id": "Job ID",
            "location": "Location",
            "application_date": "Application Date",
            "status": "Status",
            "interview_stage": "Interview Stage",
            "contact_name": "Contact Name",
            "contact_email": "Contact Email",
            "follow_up_date": "Follow-Up Date",
            "follow_up_needed": "Follow-Up Needed",
            "notes": "Notes",
        }
    )

    return df


def render_metrics() -> None:
    metrics = get_dashboard_metrics()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Applications", metrics["total_applications"])
    col2.metric("Interviews", metrics["interviews"])
    col3.metric("Rejections", metrics["rejections"])
    col4.metric("Follow-Ups Needed", metrics["follow_ups_needed"])


def render_job_search_stats() -> None:
    st.subheader("Job Search Stats")

    df = _get_all_df()

    if df.empty:
        st.info("No application data available for job search stats yet.")
        return

    total = len(df)
    interviews = int((df["status"] == "interview").sum())
    rejections = int((df["status"] == "rejected").sum())
    offers = int((df["status"] == "offer").sum())
    active_responses = interviews + rejections + offers

    response_rate = round((active_responses / total) * 100, 1) if total else 0.0
    interview_rate = round((interviews / total) * 100, 1) if total else 0.0
    offer_rate = round((offers / total) * 100, 1) if total else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Response Rate", f"{response_rate}%")
    col2.metric("Interview Rate", f"{interview_rate}%")
    col3.metric("Offer Rate", f"{offer_rate}%")


def render_status_breakdown() -> None:
    applications = get_all_applications()

    st.subheader("Status Breakdown")

    if not applications:
        st.info("No application data available yet.")
        return

    df = pd.DataFrame([dict(row) for row in applications])
    status_counts = (
        df["status"]
        .value_counts(dropna=False)
        .rename_axis("status")
        .reset_index(name="count")
        .sort_values(by=["count", "status"], ascending=[False, True])
    )

    status_counts = status_counts.rename(
        columns={
            "status": "Status",
            "count": "Count",
        }
    )

    st.dataframe(status_counts, width="stretch", hide_index=True)


def render_follow_up_alerts() -> None:
    applications = get_all_applications()

    st.subheader("Follow-Up Alerts")

    if not applications:
        st.info("No applications available yet.")
        return

    df = pd.DataFrame([dict(row) for row in applications])
    follow_up_df = df[df["follow_up_needed"] == 1].copy()

    if follow_up_df.empty:
        st.success("No follow-ups are currently needed.")
        return

    follow_up_df = follow_up_df[
        [
            "id",
            "university",
            "department_lab",
            "job_title",
            "application_date",
            "status",
            "contact_name",
            "contact_email",
            "notes",
        ]
    ].rename(
        columns={
            "id": "ID",
            "university": "University",
            "department_lab": "Department / Lab",
            "job_title": "Job Title",
            "application_date": "Application Date",
            "status": "Status",
            "contact_name": "Contact Name",
            "contact_email": "Contact Email",
            "notes": "Notes",
        }
    )

    st.warning("These applications are still in 'applied' status and are at least 14 days old.")
    st.dataframe(follow_up_df, width="stretch", hide_index=True)


def render_analytics() -> None:
    st.subheader("Analytics")

    df = _get_all_df()

    if df.empty:
        st.info("No application data available for analytics yet.")
        return

    analytics_left, analytics_right = st.columns(2)

    with analytics_left:
        st.markdown("**Applications by University**")
        university_counts = (
            df["university"]
            .fillna("Unknown")
            .value_counts()
            .rename_axis("University")
            .reset_index(name="Applications")
        )
        st.bar_chart(university_counts.set_index("University"), width="stretch")

    with analytics_right:
        st.markdown("**Applications by Status**")
        status_counts = (
            df["status"]
            .fillna("Unknown")
            .value_counts()
            .rename_axis("Status")
            .reset_index(name="Applications")
        )
        st.bar_chart(status_counts.set_index("Status"), width="stretch")

    st.markdown("**Applications Over Time**")
    timeline_df = df.copy()
    timeline_df["application_date"] = pd.to_datetime(
        timeline_df["application_date"],
        errors="coerce"
    )
    timeline_df = timeline_df.dropna(subset=["application_date"])

    if timeline_df.empty:
        st.info("No valid application dates available for the timeline chart.")
        return

    timeline_df["application_week"] = timeline_df["application_date"].dt.to_period("W").astype(str)

    weekly_counts = (
        timeline_df["application_week"]
        .value_counts()
        .sort_index()
        .rename_axis("Application Week")
        .reset_index(name="Applications")
    )

    st.line_chart(weekly_counts.set_index("Application Week"), width="stretch")


def render_application_table(status_filter: str) -> None:
    st.subheader("Application Table")

    df = _build_dataframe(status_filter)

    if df.empty:
        st.info("No applications found for the selected filter.")
        return

    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
    )

    st.caption("Applications currently tracked in the system.")
