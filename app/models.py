from dataclasses import dataclass
from typing import Optional


@dataclass
class Application:
    organization: str
    department_lab: str
    job_title: str
    job_id: Optional[str]
    location: Optional[str]
    application_date: str
    status: str
    interview_stage: Optional[str]
    contact_name: Optional[str]
    contact_email: Optional[str]
    follow_up_date: Optional[str]
    notes: Optional[str]
    company: Optional[str] = None
    job_type: Optional[str] = None
    follow_up_needed: bool = False
    id: Optional[int] = None
