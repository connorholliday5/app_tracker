from __future__ import annotations

from datetime import date, datetime
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
from app.utils import clean_value
from app.database import (
    create_application,
    create_application_if_not_exists,
    delete_application,
    get_all_applications,
    get_application_by_id,
    initialize_database,
    mark_follow_up_sent,
    update_application,
)
from app.job_parser import extract_job_application_defaults
from app.models import Application

st.set_page_config(page_title="Career Application Tracker", layout="wide")

def _check_auth() -> bool:
    import os
    pw = st.secrets.get("passwords", {}).get("admin") or os.environ.get("APP_PASSWORD")
    if not pw:
        return True
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if st.session_state["authenticated"]:
        return True
    st.markdown("### Career Application Tracker")
    entered = st.text_input("Password", type="password", key="auth_password_input")
    if st.button("Sign In", key="auth_signin_btn"):
        if entered == pw:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

_check_auth()
initialize_database()

STATUS_OPTIONS = ["applied", "interview", "rejected", "offer", "withdrawn", "ghosted", "waitlisted"]
FILTER_OPTIONS = ["all"] + STATUS_OPTIONS
INTERVIEW_STAGE_OPTIONS = ["", "Phone Screen", "Technical", "Onsite", "Final Round", "Other"]
JOB_TYPE_OPTIONS = ["", "industry", "research", "internship", "fellowship", "academic", "contract", "other"]
TEMPLATE_COLUMNS = [
    "organization",
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

ADD_FORM_DEFAULTS = {
    "job_url_input": "",
    "add_organization": "",
    "add_company": "",
    "add_department_lab": "",
    "add_job_title": "",
    "add_job_id": "",
    "add_location": "",
    "add_application_date": date.today(),
    "add_status": "applied",
    "add_job_type": "",
    "add_interview_stage": "",
    "add_contact_name": "",
    "add_contact_email": "",
    "add_follow_up_date": None,
    "add_notes": "",
    "extracted_application_ready": False,
    "reset_add_application_requested": False,
}

for state_key, default_value in ADD_FORM_DEFAULTS.items():
    if state_key not in st.session_state:
        st.session_state[state_key] = default_value

if st.session_state.get("reset_add_application_requested"):
    st.session_state["job_url_input"] = ""
    st.session_state["add_organization"] = ""
    st.session_state["add_company"] = ""
    st.session_state["add_department_lab"] = ""
    st.session_state["add_job_title"] = ""
    st.session_state["add_job_id"] = ""
    st.session_state["add_location"] = ""
    st.session_state["add_application_date"] = date.today()
    st.session_state["add_status"] = "applied"
    st.session_state["add_job_type"] = ""
    st.session_state["add_interview_stage"] = ""
    st.session_state["add_contact_name"] = ""
    st.session_state["add_contact_email"] = ""
    st.session_state["add_follow_up_date"] = None
    st.session_state["add_notes"] = ""
    st.session_state["extracted_application_ready"] = False
    st.session_state["reset_add_application_requested"] = False






def application_from_form(
    organization: str,
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
    follow_up_date,
    notes: str,
) -> Application:

    return Application(
        organization=organization or company or "",
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
        follow_up_date=follow_up_date.isoformat() if hasattr(follow_up_date, 'isoformat') else follow_up_date,
        notes=notes or None,
    )


def application_from_series(row: pd.Series) -> Application:
    organization_value = clean_value(row.get("organization")) or clean_value(row.get("company")) or ""

    return Application(
        organization=organization_value,
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
    organization_name = row["company"] or row["organization"]
    job_title = row["job_title"]
    application_date = row["application_date"]

    subject = f"Follow-Up on {job_title} Application"

    body = f"""Dear {greeting_name},

I hope you are doing well. I wanted to follow up on my application for the {job_title} position at {organization_name}, which I submitted on {application_date}.

I remain very interested in this opportunity and genuinely excited about the chance to contribute. The position stands out to me because of how closely it aligns with my background, my interests, and the kind of work I am hoping to grow in.

I would be grateful for any update you may be able to share regarding the status of my application. Thank you again for your time and consideration.

Best,
{st.secrets.get("user", {}).get("name", "Your Name")}
{st.secrets.get("user", {}).get("email", "your@email.com")}
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
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}
[data-testid="stMetric"] {
    background-color: #ffffff;
    border: 1px solid #E5E7EB;
    padding: 0.75rem 1rem;
    border-radius: 12px;
}
div[data-testid="stMetricLabel"] {
    font-weight: 600;
    font-size: 0.8rem;
}
.app-header {
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
    padding-top: 0.25rem;
}
.app-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #0F172A;
}
.app-subtitle {
    font-size: 0.85rem;
    color: #6B7280;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="app-header">
    <span class="app-title">Career Application Tracker</span>
    <span class="app-subtitle">— track applications, follow-ups, and analytics</span>
</div>
""", unsafe_allow_html=True)

tab_dashboard, tab_pipeline, tab_analytics, tab_manage = st.tabs(
    ["Dashboard", "Applications", "Analytics", "Add / Edit"]
)

with tab_dashboard:
    render_metrics()
    st.markdown("---")
    left_col, right_col = st.columns([1, 1.8])
    with left_col:
        render_status_breakdown()
    with right_col:
        render_follow_up_alerts()
        fu_rows = get_all_applications()
        fu_candidates = [row for row in fu_rows if int(row["follow_up_needed"]) == 1]
        if fu_candidates:
            fu_options = {
                f'ID {row["id"]} | {row["organization"]} | {row["job_title"]}': row["id"]
                for row in fu_candidates
            }
            selected_fu_label = st.selectbox(
                "Generate email draft:",
                options=list(fu_options.keys()),
                key="dashboard_followup_select",
            )
            selected_fu_id = fu_options[selected_fu_label]
            selected_fu_row = get_application_by_id(selected_fu_id)
            if selected_fu_row:
                subject, body = generate_follow_up_email(selected_fu_row)
                gmail_url = build_gmail_draft_url(selected_fu_row["contact_email"], subject, body)
                email_draft = f"Subject: {subject}\n\n{body}"
                st.text_area("Draft", value=email_draft, height=160, key="dashboard_email_draft")
                btn_l, btn_r = st.columns(2)
                with btn_l:
                    st.link_button("Open in Gmail", gmail_url, width="stretch")
                with btn_r:
                    if st.button("Mark Sent", key=f"dash_mark_sent_{selected_fu_id}", width="stretch"):
                        if mark_follow_up_sent(selected_fu_id):
                            st.success("Marked as sent.")
                            st.rerun()


with tab_pipeline:
    f_col, s_col, sort_col = st.columns([1.2, 2, 1])

    with f_col:
        selected_statuses = st.multiselect(
            "Filter by Status",
            STATUS_OPTIONS,
            default=[],
            placeholder="All statuses",
            key="applications_status_filter"
        )

    with s_col:
        search_text = st.text_input(
            "Search",
            placeholder="Organization, role, location, notes...",
            key="applications_search_text",
            label_visibility="collapsed"
        )

    with sort_col:
        sort_by = st.selectbox(
            "Sort by",
            ["Date (newest)", "Date (oldest)", "Organization", "Status"],
            key="applications_sort",
            label_visibility="collapsed"
        )

    render_application_table(selected_statuses, search_text, sort_by)

with tab_analytics:
    render_analytics()

with tab_manage:
    left_col, right_col = st.columns([1.15, 1.85])

    with left_col:
        st.subheader("Add Application")
        st.text_input("Paste Job Posting URL", key="job_url_input")

        extract_col, clear_col = st.columns(2)

        with extract_col:
            if st.button("Extract Application", key="extract_job_details_button", use_container_width=True):
                try:
                    progress_bar = st.progress(0, text="Starting extraction...")
                    progress_bar.progress(20, text="Fetching job posting...")
                    extracted = extract_job_application_defaults(st.session_state["job_url_input"])
                    progress_bar.progress(70, text="Parsing and structuring fields...")

                    st.session_state["add_organization"] = extracted.get("university") or ""
                    st.session_state["add_company"] = extracted.get("company") or ""
                    st.session_state["add_department_lab"] = extracted.get("department_lab") or ""
                    st.session_state["add_job_title"] = extracted.get("job_title") or ""
                    st.session_state["add_job_id"] = extracted.get("job_id") or ""
                    st.session_state["add_location"] = extracted.get("location") or ""

                    extracted_date = extracted.get("application_date")
                    st.session_state["add_application_date"] = (
                        datetime.strptime(extracted_date, "%Y-%m-%d").date()
                        if extracted_date else date.today()
                    )

                    st.session_state["add_status"] = extracted.get("status") or "applied"
                    extracted_job_type = extracted.get("job_type") or ""
                    st.session_state["add_job_type"] = (
                        extracted_job_type if extracted_job_type in JOB_TYPE_OPTIONS else ""
                    )
                    st.session_state["add_interview_stage"] = extracted.get("interview_stage") or ""
                    st.session_state["add_contact_name"] = extracted.get("contact_name") or ""
                    st.session_state["add_contact_email"] = extracted.get("contact_email") or ""
                    fu = extracted.get("follow_up_date")
                    st.session_state["add_follow_up_date"] = datetime.strptime(fu, "%Y-%m-%d").date() if fu else None
                    st.session_state["add_notes"] = extracted.get("notes") or ""
                    st.session_state["extracted_application_ready"] = True

                    progress_bar.progress(100, text="Extraction complete.")
                    st.success("Application fields populated from the URL.")
                    st.rerun()
                except Exception as exc:
                    st.session_state["extracted_application_ready"] = False
                    st.error(f"Failed to extract job details: {exc}")

        with clear_col:
            if st.button("Delete Application", key="clear_job_details_button", use_container_width=True):
                st.session_state["reset_add_application_requested"] = True
                st.rerun()

        if st.session_state["extracted_application_ready"]:
            st.markdown("### Populated Fields")

            preview_rows = [
                ("Organization", st.session_state["add_organization"] or "Not found"),
                ("Company", st.session_state["add_company"] or "Not found"),
                ("Team / Department / Lab", st.session_state["add_department_lab"] or "Not found"),
                ("Role Title", st.session_state["add_job_title"] or "Not found"),
                ("Job ID", st.session_state["add_job_id"] or "Not found"),
                ("Location", st.session_state["add_location"] or "Not found"),
                ("Application Date", st.session_state["add_application_date"].isoformat() if st.session_state["add_application_date"] else "Not found"),
                ("Status", st.session_state["add_status"] or "Not found"),
                ("Job Type", st.session_state["add_job_type"] or "Not found"),
                ("Interview Stage", st.session_state["add_interview_stage"] or "Not found"),
                ("Contact Name", st.session_state["add_contact_name"] or "Not found"),
                ("Contact Email", st.session_state["add_contact_email"] or "Not found"),
                ("Follow-Up Date", st.session_state["add_follow_up_date"].isoformat() if st.session_state["add_follow_up_date"] else "Not found"),
                ("Notes", st.session_state["add_notes"] or "Not found"),
            ]

            preview_df = pd.DataFrame(preview_rows, columns=["Field", "Value"])
            st.dataframe(preview_df, width="stretch", hide_index=True)

            if st.button("Add Application", key="add_extracted_application_button", use_container_width=True):
                try:
                    new_application = application_from_form(
                        organization=st.session_state["add_organization"],
                        company=st.session_state["add_company"],
                        department_lab=st.session_state["add_department_lab"],
                        job_title=st.session_state["add_job_title"],
                        job_id=st.session_state["add_job_id"],
                        location=st.session_state["add_location"],
                        application_date=st.session_state["add_application_date"],
                        status=st.session_state["add_status"],
                        job_type=st.session_state["add_job_type"],
                        interview_stage=st.session_state["add_interview_stage"],
                        contact_name=st.session_state["add_contact_name"],
                        contact_email=st.session_state["add_contact_email"],
                        follow_up_date=st.session_state["add_follow_up_date"],
                        notes=st.session_state["add_notes"],
                    )
                    new_id = create_application(new_application)
                    st.success(f"Application added successfully with ID {new_id}.")
                    st.cache_data.clear()
                    st.session_state["reset_add_application_requested"] = True
                    st.rerun()
                except Exception as exc:
                    st.error(f"Failed to add application: {exc}")

    with right_col:
        st.subheader("Edit or Delete Application")

        all_rows = get_all_applications()
        application_options = {
            f'ID {row["id"]} | {(row["company"] or row["organization"])} | {row["job_title"]}': row["id"]
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
                existing_follow_up_date = datetime.strptime(selected_row["follow_up_date"], "%Y-%m-%d").date() if selected_row["follow_up_date"] else None
                existing_job_type = selected_row["job_type"] or ""

                with st.form("edit_application_form"):
                    edit_organization = st.text_input("Organization *", value=selected_row["organization"])
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
                    _stage_val = selected_row["interview_stage"] or ""
                    _stage_idx = INTERVIEW_STAGE_OPTIONS.index(_stage_val) if _stage_val in INTERVIEW_STAGE_OPTIONS else 0
                    edit_interview_stage = st.selectbox("Interview Stage", INTERVIEW_STAGE_OPTIONS, index=_stage_idx)
                    edit_contact_name = st.text_input("Contact Name", value=selected_row["contact_name"] or "")
                    edit_contact_email = st.text_input("Contact Email", value=selected_row["contact_email"] or "")
                    edit_follow_up_date = st.date_input("Follow-Up Date", value=existing_follow_up_date)
                    edit_notes = st.text_area("Notes", value=selected_row["notes"] or "")

                    update_submitted = st.form_submit_button("Update Application")


                    if update_submitted:
                        try:
                            updated_application = application_from_form(
                                organization=edit_organization,
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
                                follow_up_date=edit_follow_up_date,
                                notes=edit_notes,
                            )
                            updated = update_application(selected_id, updated_application)
                            if updated:
                                st.success(f"Application ID {selected_id} updated successfully.")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("No application was updated.")
                        except Exception as exc:
                            st.error(f"Failed to update application: {exc}")

            if st.button("Delete Application", key="delete_btn", type="secondary"):
                st.session_state["confirm_delete_id"] = selected_id

            if st.session_state.get("confirm_delete_id") == selected_id:
                st.warning(f"Delete application ID {selected_id}? This cannot be undone.")
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button("Confirm Delete", key="confirm_delete_btn", type="primary"):
                        try:
                            deleted = delete_application(selected_id)
                            if deleted:
                                st.session_state.pop("confirm_delete_id", None)
                                st.success(f"Application ID {selected_id} deleted.")
                                st.cache_data.clear()
                                st.rerun()
                        except Exception as exc:
                            st.error(f"Failed to delete: {exc}")
                with cancel_col:
                    if st.button("Cancel", key="cancel_delete_btn"):
                        st.session_state.pop("confirm_delete_id", None)
                        st.rerun()







