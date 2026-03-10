# grad-app-tracker

A lightweight application tracking system for graduate school, university, and research job applications. The project combines a Streamlit dashboard, SQLite database, CSV import/export workflows, analytics, and automated follow-up reminders to make a job search more organized and data-driven.

---

## Overview

`grad-app-tracker` is a small full-stack data application built with:

- Python  
- Streamlit  
- SQLite  
- Pandas  
- Docker  
- GitHub  

The system helps manage applications across universities and research groups while providing useful metrics and insights about the job search process.

---

## Core Features

### Application Tracking

Users can:

- add applications
- edit applications
- delete applications
- track status
- store contact information
- store notes and follow-up dates

Supported statuses:

- applied
- interview
- rejected
- offer

---

### Automated Follow-Up Detection

The system automatically flags applications that require follow-up.

If:

- status = applied  
- and 14 days have passed since application_date  

Then:

follow_up_needed = True

These appear in the **Follow-Up Alerts** section of the dashboard.

---

### Dashboard Metrics

The dashboard shows:

- Total Applications
- Interviews
- Rejections
- Follow-Ups Needed

These metrics update automatically from the database.

---

### Job Search Analytics

The dashboard also includes analytics:

- Applications by university
- Applications by status
- Applications over time
- Response rate
- Interview rate
- Offer rate

These analytics help turn a job search into a measurable process.

---

### Bulk Import / Export

Applications can be imported and exported easily.

Import options:

- download CSV template
- fill it in Excel or Google Sheets
- upload directly in the UI
- preview before importing

Export options:

- CSV export
- Excel export

The importer automatically **skips duplicates**.

Duplicate detection uses:

- university
- job_title
- job_id
- application_date

---

### Follow-Up Email Draft Generator

For applications that require follow-up, the system generates a ready-to-send email draft.

Example:

Subject: Follow-Up on Research Assistant Application

Dear Hiring Team,

I hope you are doing well. I wanted to follow up on my application for the Research Assistant position that I submitted earlier this month.

I remain very interested in this opportunity and would truly welcome the chance to contribute. The position strongly aligns with my background and the type of work I am hoping to pursue.

I would be grateful for any update regarding the status of my application.

Best,  
Connor Holliday

---

## Project Structure

```
grad-app-tracker/
│
├── app/
│   ├── main.py
│   ├── dashboard.py
│   ├── database.py
│   ├── models.py
│   └── utils.py
│
├── data/
│   └── applications.db
│
├── exports/
├── scripts/
│   ├── generate_import_template.py
│   └── import_applications.py
│
├── tests/
│
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
│
├── Dockerfile
├── docker-compose.yml
├── Procfile
├── runtime.txt
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Database Fields

Each application record contains:

- university
- department_lab
- job_title
- job_id
- location
- application_date
- status
- interview_stage
- contact_name
- contact_email
- follow_up_date
- notes
- follow_up_needed

---

## Local Setup

Clone the repository:

```
git clone https://github.com/connorholliday5/app_tracker.git
cd app_tracker
```

Create a virtual environment:

```
py -3.11 -m venv .venv
```

Activate it:

```
.venv\Scripts\Activate.ps1
```

Install dependencies:

```
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the app:

```
python -m streamlit run app/main.py
```

Open:

```
http://localhost:8501
```

---

## Deployment

The repository includes configuration for deployment:

- Dockerfile
- docker-compose.yml
- Procfile
- runtime.txt
- Streamlit configuration

The application currently uses SQLite which works well for local use and portfolio demonstrations.

---

## Why This Project Matters

This project demonstrates practical skills across multiple areas:

### Software Engineering
- modular Python architecture
- backend logic
- database interaction

### Data Engineering
- CSV ingestion pipeline
- duplicate-safe import
- data validation

### Data Analytics
- dashboard metrics
- trend visualization
- job search analytics

### Product Thinking
- automated follow-ups
- workflow optimization
- user-focused UI design

---

## Future Improvements

Potential upgrades include:

- PostgreSQL support
- authentication system
- email sending integration
- reminder scheduling
- richer analytics dashboards

---

## Author

Connor Holliday

GitHub  
https://github.com/connorholliday5/app_tracker
