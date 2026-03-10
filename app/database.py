from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models import Application
from app.utils import (
    date_to_iso,
    normalize_required_text,
    normalize_status,
    normalize_text,
    parse_iso_date,
)


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "applications.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def calculate_follow_up_needed(status: str, application_date: str, follow_up_date: Optional[str]) -> bool:
    normalized_status = normalize_status(status)
    applied_on = parse_iso_date(application_date, "application_date", required=True)
    followed_up_on = parse_iso_date(follow_up_date, "follow_up_date", required=False)

    if normalized_status != "applied":
        return False

    if followed_up_on is not None:
        return False

    from datetime import date
    days_since_application = (date.today() - applied_on).days
    return days_since_application >= 14


def initialize_database() -> None:
    with get_connection() as conn:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                university TEXT NOT NULL,
                department_lab TEXT NOT NULL,
                job_title TEXT NOT NULL,
                job_id TEXT,
                location TEXT,
                application_date TEXT NOT NULL,
                status TEXT NOT NULL,
                interview_stage TEXT,
                contact_name TEXT,
                contact_email TEXT,
                follow_up_date TEXT,
                notes TEXT,
                follow_up_needed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        conn.commit()

    refresh_follow_up_flags()


def refresh_follow_up_flags() -> None:
    with get_connection() as conn:
        rows = conn.execute(
            '''
            SELECT id, status, application_date, follow_up_date
            FROM applications
            '''
        ).fetchall()

        for row in rows:
            follow_up_needed = int(
                calculate_follow_up_needed(
                    status=row["status"],
                    application_date=row["application_date"],
                    follow_up_date=row["follow_up_date"],
                )
            )

            conn.execute(
                '''
                UPDATE applications
                SET follow_up_needed = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                ''',
                (follow_up_needed, row["id"]),
            )

        conn.commit()


def validate_application_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    validated = {
        "university": normalize_required_text(payload.get("university"), "university"),
        "department_lab": normalize_required_text(payload.get("department_lab"), "department_lab"),
        "job_title": normalize_required_text(payload.get("job_title"), "job_title"),
        "job_id": normalize_text(payload.get("job_id")),
        "location": normalize_text(payload.get("location")),
        "application_date": date_to_iso(
            parse_iso_date(payload.get("application_date"), "application_date", required=True)
        ),
        "status": normalize_status(payload.get("status")),
        "interview_stage": normalize_text(payload.get("interview_stage")),
        "contact_name": normalize_text(payload.get("contact_name")),
        "contact_email": normalize_text(payload.get("contact_email")),
        "follow_up_date": date_to_iso(
            parse_iso_date(payload.get("follow_up_date"), "follow_up_date", required=False)
        ),
        "notes": normalize_text(payload.get("notes")),
    }

    validated["follow_up_needed"] = int(
        calculate_follow_up_needed(
            status=validated["status"],
            application_date=validated["application_date"],
            follow_up_date=validated["follow_up_date"],
        )
    )

    return validated


def application_exists(
    university: str,
    job_title: str,
    job_id: Optional[str],
    application_date: str,
) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            '''
            SELECT id
            FROM applications
            WHERE university = ?
              AND job_title = ?
              AND COALESCE(job_id, '') = COALESCE(?, '')
              AND application_date = ?
            LIMIT 1
            ''',
            (university, job_title, job_id, application_date),
        ).fetchone()

    return row is not None


def create_application(application: Application) -> int:
    payload = validate_application_payload(application.__dict__)

    with get_connection() as conn:
        cursor = conn.execute(
            '''
            INSERT INTO applications (
                university,
                department_lab,
                job_title,
                job_id,
                location,
                application_date,
                status,
                interview_stage,
                contact_name,
                contact_email,
                follow_up_date,
                notes,
                follow_up_needed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                payload["university"],
                payload["department_lab"],
                payload["job_title"],
                payload["job_id"],
                payload["location"],
                payload["application_date"],
                payload["status"],
                payload["interview_stage"],
                payload["contact_name"],
                payload["contact_email"],
                payload["follow_up_date"],
                payload["notes"],
                payload["follow_up_needed"],
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def create_application_if_not_exists(application: Application) -> tuple[bool, Optional[int]]:
    payload = validate_application_payload(application.__dict__)

    if application_exists(
        university=payload["university"],
        job_title=payload["job_title"],
        job_id=payload["job_id"],
        application_date=payload["application_date"],
    ):
        return False, None

    with get_connection() as conn:
        cursor = conn.execute(
            '''
            INSERT INTO applications (
                university,
                department_lab,
                job_title,
                job_id,
                location,
                application_date,
                status,
                interview_stage,
                contact_name,
                contact_email,
                follow_up_date,
                notes,
                follow_up_needed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                payload["university"],
                payload["department_lab"],
                payload["job_title"],
                payload["job_id"],
                payload["location"],
                payload["application_date"],
                payload["status"],
                payload["interview_stage"],
                payload["contact_name"],
                payload["contact_email"],
                payload["follow_up_date"],
                payload["notes"],
                payload["follow_up_needed"],
            ),
        )
        conn.commit()
        return True, int(cursor.lastrowid)


def get_all_applications(status: Optional[str] = None) -> List[sqlite3.Row]:
    refresh_follow_up_flags()

    query = "SELECT * FROM applications"
    params: tuple = ()

    if status:
        query += " WHERE status = ?"
        params = (normalize_status(status),)

    query += " ORDER BY application_date DESC, id DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return rows


def get_application_by_id(application_id: int) -> Optional[sqlite3.Row]:
    refresh_follow_up_flags()

    with get_connection() as conn:
        row = conn.execute(
            '''
            SELECT *
            FROM applications
            WHERE id = ?
            ''',
            (application_id,),
        ).fetchone()

    return row


def update_application(application_id: int, application: Application) -> bool:
    payload = validate_application_payload(application.__dict__)

    with get_connection() as conn:
        cursor = conn.execute(
            '''
            UPDATE applications
            SET university = ?,
                department_lab = ?,
                job_title = ?,
                job_id = ?,
                location = ?,
                application_date = ?,
                status = ?,
                interview_stage = ?,
                contact_name = ?,
                contact_email = ?,
                follow_up_date = ?,
                notes = ?,
                follow_up_needed = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''',
            (
                payload["university"],
                payload["department_lab"],
                payload["job_title"],
                payload["job_id"],
                payload["location"],
                payload["application_date"],
                payload["status"],
                payload["interview_stage"],
                payload["contact_name"],
                payload["contact_email"],
                payload["follow_up_date"],
                payload["notes"],
                payload["follow_up_needed"],
                application_id,
            ),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_application(application_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            '''
            DELETE FROM applications
            WHERE id = ?
            ''',
            (application_id,),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_dashboard_metrics() -> Dict[str, int]:
    refresh_follow_up_flags()

    with get_connection() as conn:
        total_applications = conn.execute(
            "SELECT COUNT(*) AS count FROM applications"
        ).fetchone()["count"]

        interviews = conn.execute(
            "SELECT COUNT(*) AS count FROM applications WHERE status = 'interview'"
        ).fetchone()["count"]

        rejections = conn.execute(
            "SELECT COUNT(*) AS count FROM applications WHERE status = 'rejected'"
        ).fetchone()["count"]

        follow_ups_needed = conn.execute(
            "SELECT COUNT(*) AS count FROM applications WHERE follow_up_needed = 1"
        ).fetchone()["count"]

    return {
        "total_applications": int(total_applications),
        "interviews": int(interviews),
        "rejections": int(rejections),
        "follow_ups_needed": int(follow_ups_needed),
    }
