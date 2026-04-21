from __future__ import annotations

import pandas as pd
import streamlit as st

from app.database import get_all_applications, get_dashboard_metrics


STATUS_CONFIG = {
    "applied":    {"emoji": "🔵", "label": "Applied"},
    "interview":  {"emoji": "🟢", "label": "Interview"},
    "offer":      {"emoji": "⭐", "label": "Offer"},
    "rejected":   {"emoji": "🔴", "label": "Rejected"},
    "withdrawn":  {"emoji": "⚪", "label": "Withdrawn"},
    "ghosted":    {"emoji": "👻", "label": "Ghosted"},
    "waitlisted": {"emoji": "🟠", "label": "Waitlisted"},
}

PIPELINE_COLUMNS = [
    "id", "organization", "job_title", "status_badge",
    "application_date", "location", "job_type", "interview_stage", "follow_up_needed",
]

ALL_COLUMNS = [
    "id", "organization", "company", "department_lab", "job_title", "job_id",
    "location", "application_date", "status", "job_type", "interview_stage",
    "contact_name", "contact_email", "follow_up_date", "follow_up_needed", "notes",
]


def _fmt_date(val) -> str:
    s = str(val).strip()
    if not s or s in {"None", "nan", "NaT"}:
        return "—"
    try:
        return pd.to_datetime(s).strftime("%b %d, %Y")
    except Exception:
        return s


def _fmt_text(val) -> str:
    s = str(val).strip() if val is not None else ""
    return "—" if not s or s in {"None", "nan"} else s


def _status_badge(status: str) -> str:
    cfg = STATUS_CONFIG.get(str(status).lower(), {"emoji": "⬜", "label": status.title()})
    return f"{cfg['emoji']} {cfg['label']}"


@st.cache_data(ttl=300)
def _get_all_df() -> pd.DataFrame:
    applications = get_all_applications()
    if not applications:
        return pd.DataFrame()
    return pd.DataFrame([dict(row) for row in applications])


def _build_pipeline_df(status_filters: list, search_text: str = "", sort_by: str = "Date (newest)") -> pd.DataFrame:
    applications = get_all_applications()

    if not applications:
        return pd.DataFrame()

    df = pd.DataFrame([dict(row) for row in applications])

    if status_filters:
        df = df[df["status"].isin(status_filters)]

    if search_text.strip():
        q = search_text.strip().lower()
        cols = ["organization", "company", "job_title", "notes", "contact_name", "location", "job_id", "job_type"]
        mask = df[cols].fillna("").astype(str).agg(" ".join, axis=1).str.lower().str.contains(q)
        df = df[mask]

    if df.empty:
        return pd.DataFrame()

    if sort_by == "Date (oldest)":
        df = df.sort_values("application_date", ascending=True)
    elif sort_by == "Organization":
        df = df.sort_values("organization", ascending=True)
    elif sort_by == "Status":
        df = df.sort_values("status", ascending=True)
    else:
        df = df.sort_values("application_date", ascending=False)

    df["status_badge"] = df["status"].apply(_status_badge)
    df["application_date"] = df["application_date"].apply(_fmt_date)
    df["follow_up_needed"] = df["follow_up_needed"].apply(lambda v: "⚠️" if int(v) == 1 else "")

    for col in ["location", "job_type", "interview_stage", "organization", "job_title"]:
        df[col] = df[col].apply(_fmt_text)

    available = [c for c in PIPELINE_COLUMNS if c in df.columns]
    return df[available].rename(columns={
        "id": "ID",
        "organization": "Organization",
        "job_title": "Role",
        "status_badge": "Status",
        "application_date": "Applied",
        "location": "Location",
        "job_type": "Type",
        "interview_stage": "Stage",
        "follow_up_needed": "⚠️",
    })


def render_metrics() -> None:
    from datetime import date as _date
    import pandas as pd
    metrics = get_dashboard_metrics()
    df = _get_all_df()
    active = offers = rejected = apps_today = 0
    follow_ups = metrics["follow_ups_needed"]
    total = metrics["total_applications"]
    if not df.empty:
        active = int(df["status"].isin(["applied", "interview", "waitlisted"]).sum())
        offers = int((df["status"] == "offer").sum())
        rejected = int((df["status"] == "rejected").sum())
        today_str = _date.today().isoformat()
        apps_today = int((df["application_date"] == today_str).sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Active", active)
    c2.metric("Rejected", rejected)
    c3.metric("Total", total)

    r1, r2, r3 = st.columns(3)
    r1.metric("Offers", offers)
    r2.metric("Follow-Ups", follow_ups)
    r3.metric("Applied Today", apps_today)


def render_job_search_stats() -> None:
    pass


def render_status_breakdown() -> None:
    st.markdown("**Status Breakdown**")
    df = _get_all_df()
    if df.empty:
        st.info("No data yet.")
        return

    counts = df["status"].value_counts().to_dict()

    st.caption("Active")
    a1, a2, a3 = st.columns(3)
    a1.metric("🔵 Applied", counts.get("applied", 0))
    a2.metric("🟢 Active", counts.get("interview", 0))
    a3.metric("🟠 Waitlist", counts.get("waitlisted", 0))

    st.caption("Closed")
    b1, b2, b3 = st.columns(3)
    b1.metric("🔴 Rejected", counts.get("rejected", 0))
    b2.metric("⭐ Offer", counts.get("offer", 0))
    b3.metric("👻 Ghosted", counts.get("ghosted", 0))


def render_follow_up_alerts() -> None:
    st.subheader("Follow-Up Queue")
    df = _get_all_df()
    if df.empty:
        st.info("No applications yet.")
        return

    follow_up_df = df[df["follow_up_needed"] == 1].copy()
    if follow_up_df.empty:
        st.success("No follow-ups needed right now.")
        return

    follow_up_df["application_date"] = pd.to_datetime(follow_up_df["application_date"], errors="coerce")
    follow_up_df["follow_up_date"] = pd.to_datetime(follow_up_df["follow_up_date"], errors="coerce")
    follow_up_df["reference_date"] = follow_up_df["follow_up_date"].fillna(follow_up_df["application_date"])
    follow_up_df["days_waiting"] = (pd.Timestamp.today().normalize() - follow_up_df["reference_date"]).dt.days
    follow_up_df["application_date"] = follow_up_df["application_date"].apply(
        lambda v: v.strftime("%b %d, %Y") if pd.notna(v) else "—"
    )
    follow_up_df["contact_email"] = follow_up_df["contact_email"].apply(_fmt_text)

    display = follow_up_df[["organization", "job_title", "application_date", "days_waiting", "contact_email"]].rename(columns={
        "organization": "Organization",
        "job_title": "Role",
        "application_date": "Applied",
        "days_waiting": "Days Waiting",
        "contact_email": "Contact",
    })

    st.caption(f"{len(display)} application(s) ready for follow-up")
    st.dataframe(display, hide_index=True, width='stretch')


def _timeline_counts(df: pd.DataFrame) -> pd.DataFrame:
    t = df.copy()
    t["application_date"] = pd.to_datetime(t["application_date"], errors="coerce")
    t = t.dropna(subset=["application_date"])
    if t.empty:
        return pd.DataFrame()
    t["week"] = t["application_date"].dt.to_period("W").astype(str)
    return t["week"].value_counts().sort_index().rename_axis("Week").reset_index(name="Applications")


def _org_counts(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df["organization"].fillna("Unknown").replace("", "Unknown")
        .value_counts().rename_axis("Organization").reset_index(name="Applications")
    )


def _status_counts(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df["status"].fillna("Unknown").replace("", "Unknown")
        .value_counts().rename_axis("Status").reset_index(name="Count")
    )


def _job_type_counts(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df["job_type"].fillna("Unspecified").replace("", "Unspecified")
        .value_counts().rename_axis("Job Type").reset_index(name="Applications")
    )


def render_analytics() -> None:
    st.subheader("Analytics")
    df = _get_all_df()
    if df.empty:
        st.info("No data yet.")
        return

    timeline = _timeline_counts(df)
    if not timeline.empty:
        st.markdown("**Applications Over Time**")
        st.line_chart(timeline.set_index("Week"), width='stretch')

    st.markdown("**Applications by Organization**")
    st.bar_chart(_org_counts(df).set_index("Organization"), width='stretch')

    a_l, a_r = st.columns(2)
    with a_l:
        st.markdown("**By Status**")
        st.bar_chart(_status_counts(df).rename(columns={"Count": "Applications"}).set_index("Status"), width="stretch")
    with a_r:
        st.markdown("**By Job Type**")
        st.bar_chart(_job_type_counts(df).set_index("Job Type"), width="stretch")


def render_application_table(status_filters: list, search_text: str = "", sort_by: str = "Date (newest)") -> None:
    df = _build_pipeline_df(status_filters, search_text, sort_by)
    if df.empty:
        st.info("No applications match the current filters.")
        return

    st.caption(f"{len(df)} application(s)")
    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        column_config={
            "ID":           st.column_config.NumberColumn(width="small"),
            "Organization": st.column_config.TextColumn(width="medium"),
            "Role":         st.column_config.TextColumn(width="large"),
            "Status":       st.column_config.TextColumn(width="small"),
            "Applied":      st.column_config.TextColumn(width="small"),
            "Location":     st.column_config.TextColumn(width="small"),
            "Type":         st.column_config.TextColumn(width="small"),
            "Stage":        st.column_config.TextColumn(width="small"),
            "⚠️":           st.column_config.TextColumn(width="small"),
        },
    )






