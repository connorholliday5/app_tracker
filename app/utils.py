from __future__ import annotations

from datetime import date, datetime
from typing import Optional


DATE_FORMAT = "%Y-%m-%d"


def normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    cleaned = str(value).strip()

    if not cleaned:
        return None

    if cleaned.lower() in {"nan", "none", "nat"}:
        return None

    return cleaned


def normalize_required_text(value: str, field_name: str) -> str:
    cleaned = normalize_text(value)
    if not cleaned:
        raise ValueError(f"{field_name} is required.")
    return cleaned


def parse_iso_date(value: Optional[str], field_name: str, required: bool = False) -> Optional[date]:
    cleaned = normalize_text(value)

    if not cleaned:
        if required:
            raise ValueError(f"{field_name} is required and must use YYYY-MM-DD format.")
        return None

    try:
        return datetime.strptime(cleaned, DATE_FORMAT).date()
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.") from exc


def date_to_iso(value: Optional[date]) -> Optional[str]:
    if value is None:
        return None
    return value.strftime(DATE_FORMAT)


def normalize_status(value: str) -> str:
    allowed_statuses = {"applied", "interview", "rejected", "offer", "withdrawn", "ghosted", "waitlisted"}
    cleaned = normalize_required_text(value, "status").lower()

    if cleaned not in allowed_statuses:
        allowed = ", ".join(sorted(allowed_statuses))
        raise ValueError(f"status must be one of: {allowed}")

    return cleaned



def clean_value(value) -> str | None:
    import pandas as pd
    if pd.isna(value):
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    if cleaned.lower() in {"nan", "none", "nat"}:
        return None
    return cleaned
