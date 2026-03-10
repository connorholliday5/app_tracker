from __future__ import annotations

import streamlit as st

from app.dashboard import render_application_table, render_metrics
from app.database import (
    create_application,
    delete_application,
    get_all_applications,
    get_application_by_id,
    initialize_database,
    update_application,
)
from app.models import Application


st.set_page_config(page_title="grad-app-tracker", layout="wide")
initialize_database()

STATUS_OPTIONS = ["applied", "interview", "rejected", "offer"]
FILTER_OPTIONS = ["all"] + STATUS_OPTIONS


def application_from_form(
    university: str,
    department_lab: str,
    job_title: str,
    job_id: str,
    location: str,
    application_date,
    status: str,
    interview_stage: str,
    contact_name: str,
    contact_email: str,
    follow_up_date,
    notes: str,
) -> Application:
    return Application(
        university=university,
        department_lab=department_lab,
        job_title=job_title,
        job_id=job_id or None,
        location=location or None,
        application_date=application_date.isoformat() if application_date else "",
        status=status,
        interview_stage=interview_stage or None,
        contact_name=contact_name or None,
        contact_email=contact_email or None,
        follow_up_date=follow_up_date.isoformat() if follow_up_date else None,
        notes=notes or None,
    )


st.title("grad-app-tracker")
st.caption("Graduate school and research application tracker")

render_metrics()

st.divider()

left_col, right_col = st.columns([1.2, 1.8])

with left_col:
    st.subheader("Add Application")

    with st.form("add_application_form", clear_on_submit=True):
        add_university = st.text_input("University *")
        add_department_lab = st.text_input("Department / Lab *")
        add_job_title = st.text_input("Job Title *")
        add_job_id = st.text_input("Job ID")
        add_location = st.text_input("Location")
        add_application_date = st.date_input("Application Date *")
        add_status = st.selectbox("Status *", STATUS_OPTIONS, index=0)
        add_interview_stage = st.text_input("Interview Stage")
        add_contact_name = st.text_input("Contact Name")
        add_contact_email = st.text_input("Contact Email")
        add_follow_up_date = st.date_input("Follow-Up Date", value=None)
        add_notes = st.text_area("Notes")

        add_submitted = st.form_submit_button("Add Application")

        if add_submitted:
            try:
                new_application = application_from_form(
                    university=add_university,
                    department_lab=add_department_lab,
                    job_title=add_job_title,
                    job_id=add_job_id,
                    location=add_location,
                    application_date=add_application_date,
                    status=add_status,
                    interview_stage=add_interview_stage,
                    contact_name=add_contact_name,
                    contact_email=add_contact_email,
                    follow_up_date=add_follow_up_date,
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
        f'ID {row["id"]} | {row["university"]} | {row["job_title"]}': row["id"]
        for row in all_rows
    }

    if not application_options:
        st.info("Add at least one application before editing or deleting.")
    else:
        selected_label = st.selectbox(
            "Select Application",
            options=list(application_options.keys()),
        )
        selected_id = application_options[selected_label]
        selected_row = get_application_by_id(selected_id)

        if selected_row:
            with st.form("edit_application_form"):
                edit_university = st.text_input("University *", value=selected_row["university"])
                edit_department_lab = st.text_input("Department / Lab *", value=selected_row["department_lab"])
                edit_job_title = st.text_input("Job Title *", value=selected_row["job_title"])
                edit_job_id = st.text_input("Job ID", value=selected_row["job_id"] or "")
                edit_location = st.text_input("Location", value=selected_row["location"] or "")
                edit_application_date = st.date_input("Application Date *", value=selected_row["application_date"])
                edit_status = st.selectbox(
                    "Status *",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(selected_row["status"]),
                )
                edit_interview_stage = st.text_input("Interview Stage", value=selected_row["interview_stage"] or "")
                edit_contact_name = st.text_input("Contact Name", value=selected_row["contact_name"] or "")
                edit_contact_email = st.text_input("Contact Email", value=selected_row["contact_email"] or "")
                edit_follow_up_date = st.date_input(
                    "Follow-Up Date",
                    value=selected_row["follow_up_date"],
                )
                edit_notes = st.text_area("Notes", value=selected_row["notes"] or "")

                update_submitted = st.form_submit_button("Update Application")
                delete_submitted = st.form_submit_button("Delete Application")

                if update_submitted:
                    try:
                        updated_application = application_from_form(
                            university=edit_university,
                            department_lab=edit_department_lab,
                            job_title=edit_job_title,
                            job_id=edit_job_id,
                            location=edit_location,
                            application_date=edit_application_date,
                            status=edit_status,
                            interview_stage=edit_interview_stage,
                            contact_name=edit_contact_name,
                            contact_email=edit_contact_email,
                            follow_up_date=edit_follow_up_date,
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

st.divider()

st.subheader("Filter Applications")
selected_filter = st.selectbox("Status Filter", FILTER_OPTIONS, index=0)

render_application_table(selected_filter)
