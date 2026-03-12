from __future__ import annotations

import pandas as pd
import streamlit as st

from app.database import get_all_applications, get_dashboard_metrics


DISPLAY_COLUMNS = [
    "id",
    "university",
    "company",
    "department_lab",
    "job_title",
    "job_id",
    "location",
    "application_date",
    "status",
    "job_type",
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


def _build_dataframe(status_filter: str, search_text: str = "") -> pd.DataFrame:
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

    if search_text.strip():
        search_value = search_text.strip().lower()
        search_columns = [
            "university",
            "company",
            "department_lab",
            "job_title",
            "notes",
            "contact_name",
            "contact_email",
            "location",
            "job_id",
            "job_type",
        ]

        combined_search = df[search_columns].fillna("").astype(str).agg(" | ".join, axis=1).str.lower()
        df = df[combined_search.str.contains(search_value, na=False)]

    if df.empty:
        return pd.DataFrame()

    df = df[DISPLAY_COLUMNS].copy()

    df["follow_up_needed"] = df["follow_up_needed"].apply(
        lambda value: "Yes" if int(value) == 1 else "No"
    )

    df = df.rename(
        columns={
            "id": "ID",
            "university": "Organization",
            "company": "Company",
            "department_lab": "Team / Department / Lab",
            "job_title": "Role Title",
            "job_id": "Job ID",
            "location": "Location",
            "application_date": "Application Date",
            "status": "Status",
            "job_type": "Job Type",
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
    df = _get_all_df()

    if df.empty:
        active_applications = 0
        offers = 0
    else:
        active_applications = int(df["status"].isin(["applied", "interview"]).sum())
        offers = int((df["status"] == "offer").sum())

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Applications", metrics["total_applications"])
    col2.metric("Active Applications", active_applications)
    col3.metric("Interviews", metrics["interviews"])
    col4.metric("Offers", offers)
    col5.metric("Follow-Ups Needed", metrics["follow_ups_needed"])


def render_job_search_stats() -> None:
    st.subheader("Pipeline Snapshot")

    df = _get_all_df()

    if df.empty:
        st.info("No application data available for pipeline stats yet.")
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

    st.subheader("Follow-Up Queue")

    if not applications:
        st.info("No applications available yet.")
        return

    df = pd.DataFrame([dict(row) for row in applications])
    follow_up_df = df[df["follow_up_needed"] == 1].copy()

    if follow_up_df.empty:
        st.success("No follow-ups are currently needed.")
        return

    follow_up_df["application_date"] = pd.to_datetime(
        follow_up_df["application_date"],
        errors="coerce"
    )
    follow_up_df["days_waiting"] = (
        pd.Timestamp.today().normalize() - follow_up_df["application_date"]
    ).dt.days

    follow_up_df = follow_up_df[
        [
            "id",
            "university",
            "company",
            "job_title",
            "job_type",
            "application_date",
            "days_waiting",
            "contact_name",
            "contact_email",
            "notes",
        ]
    ].rename(
        columns={
            "id": "ID",
            "university": "Organization",
            "company": "Company",
            "job_title": "Role Title",
            "job_type": "Job Type",
            "application_date": "Applied On",
            "days_waiting": "Days Waiting",
            "contact_name": "Contact Name",
            "contact_email": "Contact Email",
            "notes": "Notes",
        }
    )

    st.warning("These applications are still in applied status, are at least 14 days old, and do not have a recorded follow-up date.")
    st.dataframe(follow_up_df, width="stretch", hide_index=True)


def render_analytics() -> None:
    st.subheader("Analytics")

    df = _get_all_df()

    if df.empty:
        st.info("No application data available for analytics yet.")
        return

    analytics_top_left, analytics_top_right = st.columns(2)

    with analytics_top_left:
        st.markdown("**Applications by Organization**")
        organization_counts = (
            df["university"]
            .fillna("Unknown")
            .value_counts()
            .rename_axis("Organization")
            .reset_index(name="Applications")
        )
        st.bar_chart(organization_counts.set_index("Organization"), width="stretch")

    with analytics_top_right:
        st.markdown("**Applications by Status**")
        status_counts = (
            df["status"]
            .fillna("Unknown")
            .value_counts()
            .rename_axis("Status")
            .reset_index(name="Applications")
        )
        st.bar_chart(status_counts.set_index("Status"), width="stretch")

    analytics_middle_left, analytics_middle_right = st.columns(2)

    with analytics_middle_left:
        st.markdown("**Applications by Job Type**")
        job_type_counts = (
            df["job_type"]
            .fillna("Unspecified")
            .replace("", "Unspecified")
            .value_counts()
            .rename_axis("Job Type")
            .reset_index(name="Applications")
        )
        st.bar_chart(job_type_counts.set_index("Job Type"), width="stretch")

    with analytics_middle_right:
        st.markdown("**Applications by Outcome**")
        outcome_df = df.copy()
        outcome_df["outcome_bucket"] = outcome_df["status"].map(
            {
                "applied": "Active",
                "interview": "In Process",
                "rejected": "Closed - Rejected",
                "offer": "Closed - Offer",
            }
        ).fillna("Other")

        outcome_counts = (
            outcome_df["outcome_bucket"]
            .value_counts()
            .rename_axis("Outcome")
            .reset_index(name="Applications")
        )
        st.bar_chart(outcome_counts.set_index("Outcome"), width="stretch")

    analytics_bottom_left, analytics_bottom_right = st.columns(2)

    with analytics_bottom_left:
        st.markdown("**Pipeline Funnel**")
        applied_count = int((df["status"] == "applied").sum())
        interview_count = int((df["status"] == "interview").sum())
        offer_count = int((df["status"] == "offer").sum())

        funnel_df = pd.DataFrame(
            [
                {"Stage": "Applied", "Count": applied_count},
                {"Stage": "Interview", "Count": interview_count},
                {"Stage": "Offer", "Count": offer_count},
            ]
        )
        st.dataframe(funnel_df, width="stretch", hide_index=True)

    with analytics_bottom_right:
        st.markdown("**Applications by Company**")
        company_counts = (
            df["company"]
            .fillna("Unspecified")
            .replace("", "Unspecified")
            .value_counts()
            .rename_axis("Company")
            .reset_index(name="Applications")
        )
        st.bar_chart(company_counts.set_index("Company"), width="stretch")

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


def render_application_table(status_filter: str, search_text: str = "") -> None:
    df = _build_dataframe(status_filter, search_text)

    if df.empty:
        st.info("No applications match the current filters.")
        return

    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
    )

    st.caption("Filtered application pipeline results.")
