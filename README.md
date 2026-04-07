# Career Application Tracker

A workflow-oriented job application tracker built with Streamlit and SQLite. Tracks applications across industry, research, academic, internship, fellowship, and contract opportunities through a clean dashboard with analytics, bulk import/export, and automated follow-up reminders.

---

## Dashboard Preview

![Career Application Tracker Dashboard](images/dashboard.png)

---

## Overview

Built with:

- Python 3.11
- Streamlit
- SQLite
- Pandas
- Docker

---

## Core Features

### Application Tracking

- add, edit, and delete applications
- track status and interview stage
- store contact information, notes, and follow-up dates

Supported statuses: `applied`, `interview`, `rejected`, `offer`, `withdrawn`, `ghosted`, `waitlisted`

Supported interview stages: `Phone Screen`, `Technical`, `Onsite`, `Final Round`, `Other`

### Job URL Parser

Paste a job posting URL to auto-extract organization, title, location, job ID, department, and job type.

### Automated Follow-Up Detection

An application is flagged for follow-up when:

- status is `applied`
- 14 or more days have passed since the application date
- no follow-up date has been logged

### Dashboard Metrics

- Total Applications
- Active Applications
- Interviews
- Offers
- Follow-Ups Needed
- Response Rate, Interview Rate, Offer Rate

### Analytics

- applications over time
- applications by organization, company, job type, status, and outcome
- pipeline funnel view

### Bulk Import / Export

- import applications from CSV
- export to CSV or Excel
- duplicate detection on: `organization`, `job_title`, `job_id`, `application_date`

### Follow-Up Email Draft Generator

Generates a ready-to-send follow-up email draft for flagged applications and opens it directly in Gmail.

---

## Project Structure

    grad-app-tracker/
        app/
            __init__.py
            main.py
            dashboard.py
            database.py
            job_parser.py
            models.py
            utils.py
        data/
            applications.db
        scripts/
            import_applications.py
        .streamlit/
            config.toml
            secrets.toml.example
        images/
            dashboard.png
        Dockerfile
        docker-compose.yml
        requirements.txt
        .python-version
        .gitignore
        README.md

---

## Database Fields

| Field | Description |
|---|---|
| organization | primary organization name |
| company | company name if different |
| department_lab | team, department, or lab |
| job_title | role title |
| job_id | job posting ID |
| location | location or remote/hybrid |
| application_date | date applied |
| status | current application status |
| job_type | industry, research, internship, etc. |
| interview_stage | current interview stage |
| contact_name | recruiter or contact name |
| contact_email | recruiter or contact email |
| follow_up_date | date follow-up was sent |
| notes | free-text notes |
| follow_up_needed | auto-computed flag |

---

## Local Setup
```powershell
git clone https://github.com/connorholliday5/app_tracker.git
cd app_tracker\grad-app-tracker

py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create your secrets file:
```powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Edit `.streamlit/secrets.toml` with your name and email, then run:
```powershell
python -m streamlit run app/main.py
```

Open `http://localhost:8501`

---

## Bulk CSV Import (CLI)
```powershell
python -m scripts.import_applications path\to\file.csv
```

---

## Deployment

Includes `Dockerfile` and `docker-compose.yml` for containerized deployment. Uses SQLite, suitable for local use and portfolio demonstrations.

---

## Author

Connor Holliday
https://github.com/connorholliday5/app_tracker
