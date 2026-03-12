from __future__ import annotations

from datetime import datetime
from io import BytesIO
from urllib.parse import quote

import pandas as pd
import streamlit as st

from app.dashboard import (
    render_analytics,
    render_application_table,
    render_follow_up_alerts,
    render_job_search_stats,
    render_metrics,
    render_status_breakdown,
)
from app.database import (
    create_application,
    create_application_if_not_exists,
    delete_application,
    get_all_applications,
    get_application_by_id,
    initialize_database,
    update_application,
)
from app.models import Application


st.set_page_config(page_title="Career Application Tracker", layout="wide")
initialize_database()

STATUS_OPTIONS = ["applied", "interview", "rejected", "offer"]
FILTER_OPTIONS = ["all"] + STATUS_OPTIONS
JOB_TYPE_OPTIONS = ["", "industry", "research", "internship", "fellowship", "academic", "contract", "other"]
TEMPLATE_COLUMNS = [
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
    "notes",
]


def parse_date_or_none(value: str):
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    return datetime.strptime(cleaned, "%Y-%m-%d").date()


def clean_value(value):
    if pd.isna(value):
        return None

    cleaned = str(value).strip()

    if cleaned == "":
        return None

    if cleaned.lower() in {"nan", "none", "nat"}:
        return None

    return cleaned


def application_from_form(
    university: str,
    company: str,
    department_lab: str,
    job_title: str,
    job_id: str,
    location: str,
    application_date,
    status: str,
    job_type: str,
    interview_stage: str,
    contact_name: str,
    contact_email: str,
    follow_up_date_text: str,
    notes: str,
) -> Application:
    follow_up_date = parse_date_or_none(follow_up_date_text)

    return Application(
        university=university or company or "",
        company=company or None,
        department_lab=department_lab or "",
        job_title=job_title,
        job_id=job_id or None,
        location=location or None,
        application_date=application_date.isoformat() if application_date else "",
        status=status,
        job_type=job_type or None,
        interview_stage=interview_stage or None,
        contact_name=contact_name or None,
        contact_email=contact_email or None,
        follow_up_date=follow_up_date.isoformat() if follow_up_date else None,
        notes=notes or None,
    )


def application_from_series(row: pd.Series) -> Application:
    organization_value = clean_value(row.get("university")) or clean_value(row.get("company")) or ""

    return Application(
        university=organization_value,
        company=clean_value(row.get("company")),
        department_lab=clean_value(row.get("department_lab")) or "",
        job_title=clean_value(row.get("job_title")) or "",
        job_id=clean_value(row.get("job_id")),
        location=clean_value(row.get("location")),
        application_date=clean_value(row.get("application_date")) or "",
        status=clean_value(row.get("status")) or "",
        job_type=clean_value(row.get("job_type")),
        interview_stage=clean_value(row.get("interview_stage")),
        contact_name=clean_value(row.get("contact_name")),
        contact_email=clean_value(row.get("contact_email")),
        follow_up_date=clean_value(row.get("follow_up_date")),
        notes=clean_value(row.get("notes")),
    )


def get_template_csv_bytes() -> bytes:
    template_df = pd.DataFrame(columns=TEMPLATE_COLUMNS)
    return template_df.to_csv(index=False).encode("utf-8")


def get_export_dataframe() -> pd.DataFrame:
    rows = get_all_applications()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([dict(row) for row in rows])


def get_export_excel_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="applications")
    return output.getvalue()


def generate_follow_up_email(row) -> tuple[str, str]:
    contact_name = (row["contact_name"] or "").strip()
    greeting_name = contact_name if contact_name else "Hiring Team"
    organization_name = row["company"] or row["university"]
    job_title = row["job_title"]
    application_date = row["application_date"]

    subject = f"Follow-Up on {job_title} Application"

    body = f"""Dear {greeting_name},

I hope you are doing well. I wanted to follow up on my application for the {job_title} position at {organization_name}, which I submitted on {application_date}.

I remain very interested in this opportunity and genuinely excited about the chance to contribute. The position stands out to me because of how closely it aligns with my background, my interests, and the kind of work I am hoping to grow in.

I would be grateful for any update you may be able to share regarding the status of my application. Thank you again for your time and consideration.

Best,
Connor Holliday
connholl@bu.edu
"""
    return subject, body


def build_gmail_draft_url(to_email: str | None, subject: str, body: str) -> str:
    recipient = to_email or ""
    base_url = "https://mail.google.com/mail/?view=cm&fs=1"
    return (
        f"{base_url}"
        f"&to={quote(recipient)}"
        f"&su={quote(subject)}"
        f"&body={quote(body)}"
    )


st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}
[data-testid="stMetric"] {
    background-color: #ffffff;
    border: 1px solid #E5E7EB;
    padding: 1rem 1rem 0.9rem 1rem;
    border-radius: 14px;
}
div[data-testid="stMetricLabel"] {
    font-weight: 600;
}
.hero-card {
    background: linear-gradient(135deg, #EFF6FF 0%, #FFFFFF 100%);
    border: 1px solid #DBEAFE;
    border-radius: 20px;
    padding: 1.35rem 1.4rem 1.2rem 1.4rem;
    margin-bottom: 1rem;
}
.hero-title {
    font-size: 2.2rem;
    font-weight: 800;
    color: #0F172A;
    line-height: 1.1;
    margin-bottom: 0.35rem;
}
.hero-subtitle {
    font-size: 1rem;
    color: #475467;
    margin-bottom: 0.9rem;
}
.hero-meta {
    font-size: 0.95rem;
    color: #344054;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-card">
    <div class="hero-title">Career Application Tracker</div>
    <div class="hero-subtitle">Track applications, follow-ups, and job search analytics in one place.</div>
    <div class="hero-meta">Built for industry, research, academic, internship, and other professional application workflows.</div>
</div>
""", unsafe_allow_html=True)

tab_dashboard, tab_pipeline, tab_manage, tab_import_export, tab_followups = st.tabs(
    ["Overview", "Pipeline", "Manage Applications", "Import / Export", "Follow-Ups"]
)

with tab_dashboard:
    render_metrics()
    st.divider()
    render_job_search_stats()
    st.divider()

    top_left, top_right = st.columns([1.1, 1.9])

    with top_left:
        render_status_breakdown()

    with top_right:
        render_follow_up_alerts()

    st.divider()
    render_analytics()

with tab_pipeline:
    st.subheader("Applications")

    filter_col, search_col = st.columns([1, 1.4])

    with filter_col:
        selected_filter = st.selectbox(
            "Filter by Status",
            FILTER_OPTIONS,
            index=0,
            key="applications_status_filter"
        )

    with search_col:
        search_text = st.text_input(
            "Search Applications",
            placeholder="Search organization, company, role title, notes, contact, location, job ID, or job type",
            key="applications_search_text"
        )

    render_application_table(selected_filter, search_text)

with tab_manage:
    left_col, right_col = st.columns([1.15, 1.85])

    with left_col:
        st.subheader("Add Application")

        with st.form("add_application_form", clear_on_submit=True):
            add_university = st.text_input("Organization *")
            add_company = st.text_input("Company")
            add_department_lab = st.text_input("Team / Department / Lab")
            add_job_title = st.text_input("Role Title *")
            add_job_id = st.text_input("Job ID")
            add_location = st.text_input("Location")
            add_application_date = st.date_input("Application Date *")
            add_status = st.selectbox("Status *", STATUS_OPTIONS, index=0)
            add_job_type = st.selectbox("Job Type", JOB_TYPE_OPTIONS, index=0)
            add_interview_stage = st.text_input("Interview Stage")
            add_contact_name = st.text_input("Contact Name")
            add_contact_email = st.text_input("Contact Email")
            add_follow_up_date_text = st.text_input("Follow-Up Date (YYYY-MM-DD)")
            add_notes = st.text_area("Notes")

            add_submitted = st.form_submit_button("Add Application")

            if add_submitted:
                try:
                    new_application = application_from_form(
                        university=add_university,
                        company=add_company,
                        department_lab=add_department_lab,
                        job_title=add_job_title,
                        job_id=add_job_id,
                        location=add_location,
                        application_date=add_application_date,
                        status=add_status,
                        job_type=add_job_type,
                        interview_stage=add_interview_stage,
                        contact_name=add_contact_name,
                        contact_email=add_contact_email,
                        follow_up_date_text=add_follow_up_date_text,
                        notes=add_notes,
                    )
                    new_id = create_application(new_application)
                    st.success(f"Application added successfully with ID {new_id}.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Failed to add application: {exc}")

    with right_col:
        st.subheader("Edit or Delete Application")

        all_rows = get_all_applications()
        application_options = {
            f'ID {row["id"]} | {(row["company"] or row["university"])} | {row["job_title"]}': row["id"]
            for row in all_rows
        }

        if not application_options:
            st.info("Add at least one application before editing or deleting.")
        else:
            selected_label = st.selectbox(
                "Select Application",
                options=list(application_options.keys()),
                key="edit_application_select",
            )
            selected_id = application_options[selected_label]
            selected_row = get_application_by_id(selected_id)

            if selected_row:
                existing_follow_up_date = selected_row["follow_up_date"] or ""
                existing_job_type = selected_row["job_type"] or ""

                with st.form("edit_application_form"):
                    edit_university = st.text_input("Organization *", value=selected_row["university"])
                    edit_company = st.text_input("Company", value=selected_row["company"] or "")
                    edit_department_lab = st.text_input("Team / Department / Lab", value=selected_row["department_lab"] or "")
                    edit_job_title = st.text_input("Role Title *", value=selected_row["job_title"])
                    edit_job_id = st.text_input("Job ID", value=selected_row["job_id"] or "")
                    edit_location = st.text_input("Location", value=selected_row["location"] or "")
                    edit_application_date = st.date_input(
                        "Application Date *",
                        value=datetime.strptime(selected_row["application_date"], "%Y-%m-%d").date(),
                    )
                    edit_status = st.selectbox(
                        "Status *",
                        STATUS_OPTIONS,
                        index=STATUS_OPTIONS.index(selected_row["status"]),
                    )
                    edit_job_type = st.selectbox(
                        "Job Type",
                        JOB_TYPE_OPTIONS,
                        index=JOB_TYPE_OPTIONS.index(existing_job_type) if existing_job_type in JOB_TYPE_OPTIONS else 0,
                    )
                    edit_interview_stage = st.text_input("Interview Stage", value=selected_row["interview_stage"] or "")
                    edit_contact_name = st.text_input("Contact Name", value=selected_row["contact_name"] or "")
                    edit_contact_email = st.text_input("Contact Email", value=selected_row["contact_email"] or "")
                    edit_follow_up_date_text = st.text_input(
                        "Follow-Up Date (YYYY-MM-DD)",
                        value=existing_follow_up_date,
                    )
                    edit_notes = st.text_area("Notes", value=selected_row["notes"] or "")

                    update_submitted = st.form_submit_button("Update Application")
                    delete_submitted = st.form_submit_button("Delete Application")

                    if update_submitted:
                        try:
                            updated_application = application_from_form(
                                university=edit_university,
                                company=edit_company,
                                department_lab=edit_department_lab,
                                job_title=edit_job_title,
                                job_id=edit_job_id,
                                location=edit_location,
                                application_date=edit_application_date,
                                status=edit_status,
                                job_type=edit_job_type,
                                interview_stage=edit_interview_stage,
                                contact_name=edit_contact_name,
                                contact_email=edit_contact_email,
                                follow_up_date_text=edit_follow_up_date_text,
                                notes=edit_notes,
                            )
                            updated = update_application(selected_id, updated_application)
                            if updated:
                                st.success(f"Application ID {selected_id} updated successfully.")
                                st.rerun()
                            else:
                                st.error("No application was updated.")
                        except Exception as exc:
                            st.error(f"Failed to update application: {exc}")

                    if delete_submitted:
                        try:
                            deleted = delete_application(selected_id)
                            if deleted:
                                st.success(f"Application ID {selected_id} deleted successfully.")
                                st.rerun()
                            else:
                                st.error("No application was deleted.")
                        except Exception as exc:
                            st.error(f"Failed to delete application: {exc}")

with tab_import_export:
    st.subheader("Import / Export")

    import_col, export_col = st.columns(2)

    with import_col:
        st.markdown("### CSV Import")
        st.download_button(
            label="Download CSV Template",
            data=get_template_csv_bytes(),
            file_name="career_application_tracker_template.csv",
            mime="text/csv",
        )

        uploaded_file = st.file_uploader("Upload Applications CSV", type="csv")

        if uploaded_file is not None:
            try:
                preview_df = pd.read_csv(uploaded_file)
                st.markdown("**Preview**")
                st.dataframe(preview_df, width="stretch", hide_index=True)

                if st.button("Import Uploaded CSV", key="import_uploaded_csv_button"):
                    required_columns = [
                        "job_title",
                        "application_date",
                        "status",
                    ]

                    missing = [column for column in required_columns if column not in preview_df.columns]
                    if missing:
                        st.error(f"Missing required columns: {missing}")
                    elif "university" not in preview_df.columns and "company" not in preview_df.columns:
                        st.error("CSV must include at least one of: university or company")
                    else:
                        for column in TEMPLATE_COLUMNS:
                            if column not in preview_df.columns:
                                preview_df[column] = None

                        inserted = 0
                        skipped = 0

                        for row_number, (_, row) in enumerate(preview_df.iterrows(), start=2):
                            try:
                                app = application_from_series(row)
                                created, _ = create_application_if_not_exists(app)
                                if created:
                                    inserted += 1
                                else:
                                    skipped += 1
                            except Exception as exc:
                                st.error(f"Import failed on CSV row {row_number}: {exc}")
                                st.stop()

                        st.success(f"Imported {inserted} applications successfully.")
                        st.info(f"Skipped {skipped} duplicate applications.")
                        st.rerun()
            except Exception as exc:
                st.error(f"Unable to read uploaded CSV: {exc}")

    with export_col:
        st.markdown("### Data Export")

        export_df = get_export_dataframe()

        if export_df.empty:
            st.info("No application data available to export.")
        else:
            csv_bytes = export_df.to_csv(index=False).encode("utf-8")
            excel_bytes = get_export_excel_bytes(export_df)

            st.download_button(
                label="Download CSV Export",
                data=csv_bytes,
                file_name="career_application_tracker_export.csv",
                mime="text/csv",
            )

            st.download_button(
                label="Download Excel Export",
                data=excel_bytes,
                file_name="career_application_tracker_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

with tab_followups:
    st.subheader("Follow-Up Queue")

    all_rows_for_email = get_all_applications()
    follow_up_candidates = [row for row in all_rows_for_email if int(row["follow_up_needed"]) == 1]

    if not follow_up_candidates:
        st.info("No follow-up email drafts are needed right now.")
    else:
        st.caption("Select an application below to generate a follow-up email draft and open it in Gmail.")
        email_options = {
            f'ID {row["id"]} | {(row["company"] or row["university"])} | {row["job_title"]}': row["id"]
            for row in follow_up_candidates
        }

        selected_email_label = st.selectbox(
            "Select Application for Follow-Up Draft",
            options=list(email_options.keys()),
            key="followup_draft_select",
        )
        selected_email_id = email_options[selected_email_label]
        selected_email_row = get_application_by_id(selected_email_id)

        if selected_email_row:
            followup_meta_left, followup_meta_right = st.columns(2)

            with followup_meta_left:
                st.markdown(f"**Organization:** {selected_email_row['university']}")
                st.markdown(f"**Company:** {selected_email_row['company'] or 'Not saved'}")
                st.markdown(f"**Role Title:** {selected_email_row['job_title']}")

            with followup_meta_right:
                st.markdown(f"**Applied On:** {selected_email_row['application_date']}")
                st.markdown(f"**Job Type:** {selected_email_row['job_type'] or 'Not specified'}")
                if selected_email_row["contact_email"]:
                    st.markdown(f"**Contact Email:** {selected_email_row['contact_email']}")
                else:
                    st.markdown("**Contact Email:** Not saved")

            subject, body = generate_follow_up_email(selected_email_row)
            email_draft = f"Subject: {subject}\n\n{body}"
            gmail_url = build_gmail_draft_url(
                selected_email_row["contact_email"],
                subject,
                body,
            )

            st.text_area("Generated Follow-Up Email", value=email_draft, height=320)

            followup_action_left, followup_action_right = st.columns(2)

            with followup_action_left:
                st.link_button("Open Gmail Draft", gmail_url, use_container_width=True)

            with followup_action_right:
                if selected_email_row["contact_email"]:
                    st.caption(f"Recipient: {selected_email_row['contact_email']}")
                else:
                    st.caption("Recipient: no contact email saved for this application")

