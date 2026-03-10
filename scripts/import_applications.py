import sys
import pandas as pd

from app.database import create_application_if_not_exists, initialize_database
from app.models import Application


REQUIRED_COLUMNS = [
    "university",
    "department_lab",
    "job_title",
    "application_date",
    "status",
]

ALL_COLUMNS = [
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
    "notes",
]


def clean_value(value):
    if pd.isna(value):
        return None

    cleaned = str(value).strip()

    if cleaned == "":
        return None

    if cleaned.lower() in {"nan", "none", "nat"}:
        return None

    return cleaned


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.import_applications <csv_path>")
        sys.exit(1)

    csv_path = sys.argv[1]

    initialize_database()

    df = pd.read_csv(csv_path)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    for column in ALL_COLUMNS:
        if column not in df.columns:
            df[column] = None

    inserted = 0
    skipped = 0

    for row_number, (_, row) in enumerate(df.iterrows(), start=2):
        try:
            app = Application(
                university=clean_value(row.get("university")) or "",
                department_lab=clean_value(row.get("department_lab")) or "",
                job_title=clean_value(row.get("job_title")) or "",
                job_id=clean_value(row.get("job_id")),
                location=clean_value(row.get("location")),
                application_date=clean_value(row.get("application_date")) or "",
                status=clean_value(row.get("status")) or "",
                interview_stage=clean_value(row.get("interview_stage")),
                contact_name=clean_value(row.get("contact_name")),
                contact_email=clean_value(row.get("contact_email")),
                follow_up_date=clean_value(row.get("follow_up_date")),
                notes=clean_value(row.get("notes")),
            )

            created, _ = create_application_if_not_exists(app)

            if created:
                inserted += 1
            else:
                skipped += 1

        except Exception as exc:
            raise ValueError(f"Import failed on CSV row {row_number}: {exc}") from exc

    print(f"Imported {inserted} applications successfully")
    print(f"Skipped {skipped} duplicate applications")


if __name__ == "__main__":
    main()
