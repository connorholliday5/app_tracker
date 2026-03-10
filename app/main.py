import streamlit as st

from app.database import DB_PATH, get_all_applications, get_dashboard_metrics, initialize_database

st.set_page_config(page_title="grad-app-tracker", layout="wide")

initialize_database()
metrics = get_dashboard_metrics()
applications = get_all_applications()

st.title("grad-app-tracker")
st.caption("Graduate school and research application tracker")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Applications", metrics["total_applications"])
col2.metric("Interviews", metrics["interviews"])
col3.metric("Rejections", metrics["rejections"])
col4.metric("Follow-Ups Needed", metrics["follow_ups_needed"])

st.write(f"Database path: {DB_PATH}")

if applications:
    st.subheader("Applications")
    st.dataframe([dict(row) for row in applications], use_container_width=True)
else:
    st.info("Database initialized successfully. No applications have been added yet.")
