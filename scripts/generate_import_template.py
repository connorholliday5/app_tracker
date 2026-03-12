import pandas as pd

columns = [
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

df = pd.DataFrame(columns=columns)

df.to_csv("exports/import_template.csv", index=False)

print("Template created: exports/import_template.csv")
