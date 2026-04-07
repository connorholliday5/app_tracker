from __future__ import annotations

import json
import re
from datetime import date
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

JOB_BOARD_DOMAINS = {
    "greenhouse.io", "lever.co", "workday.com", "myworkdayjobs.com",
    "linkedin.com", "indeed.com", "glassdoor.com", "jobvite.com",
    "smartrecruiters.com", "icims.com", "taleo.net", "successfactors.com",
}


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", str(value)).strip()
    return cleaned or None


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        cleaned = _clean(value)
        if cleaned:
            return cleaned
    return None


def _is_job_board(url: str) -> bool:
    host = urlparse(url).netloc.lower().replace("www.", "")
    return any(domain in host for domain in JOB_BOARD_DOMAINS)


JOB_LD_KEYS = {"title", "hiringOrganization", "jobLocation", "identifier", "datePosted", "description"}

def _looks_like_job_posting(data: dict) -> bool:
    return bool(JOB_LD_KEYS & set(data.keys()))

def _extract_json_ld(soup: BeautifulSoup) -> dict:
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        if item.get("@type") in ("JobPosting", "jobPosting") or _looks_like_job_posting(item):
                            return item
            elif isinstance(data, dict):
                if data.get("@type") in ("JobPosting", "jobPosting"):
                    return data
                if "@graph" in data:
                    for item in data["@graph"]:
                        if isinstance(item, dict) and (item.get("@type") in ("JobPosting", "jobPosting") or _looks_like_job_posting(item)):
                            return item
                if _looks_like_job_posting(data):
                    return data
        except (json.JSONDecodeError, AttributeError):
            continue
    return {}


def _parse_json_ld_location(job_data: dict) -> str | None:
    remote_type = _clean(str(job_data.get("jobLocationType", "")))
    if remote_type and "remote" in remote_type.lower():
        return "Remote"

    loc = job_data.get("jobLocation")
    if not loc:
        return None
    if isinstance(loc, list):
        loc = loc[0]
    if isinstance(loc, dict):
        address = loc.get("address", {})
        if isinstance(address, dict):
            parts = [
                address.get("addressLocality"),
                address.get("addressRegion"),
            ]
            result = ", ".join(p for p in parts if p)
            return _clean(result) or None
        if isinstance(address, str):
            return _clean(address)
    return None


def _parse_json_ld_org(job_data: dict) -> str | None:
    org = job_data.get("hiringOrganization")
    if not org:
        return None
    if isinstance(org, dict):
        return _clean(org.get("name"))
    if isinstance(org, str):
        return _clean(org)
    return None


def _parse_json_ld_job_id(job_data: dict) -> str | None:
    identifier = job_data.get("identifier")
    if isinstance(identifier, dict):
        return _clean(str(identifier.get("value", ""))) or None
    if isinstance(identifier, str):
        return _clean(identifier)
    return None


def _parse_json_ld_department(job_data: dict) -> str | None:
    for key in ("department", "occupationalCategory"):
        val = job_data.get(key)
        if val and isinstance(val, str):
            cleaned = _clean(val)
            if cleaned and len(cleaned) < 120:
                return cleaned
    return None


def _extract_site_name(soup: BeautifulSoup, url: str) -> str | None:
    meta_og = soup.find("meta", attrs={"property": "og:site_name"})
    if meta_og and meta_og.get("content"):
        return _clean(meta_og["content"])
    host = urlparse(url).netloc.lower().replace("www.", "")
    root = host.split(".")[0].replace("-", " ").replace("_", " ").strip()
    return root.title() if root else None


def _extract_visible_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()


def _extract_title_from_soup(soup: BeautifulSoup) -> str | None:
    meta_og = soup.find("meta", attrs={"property": "og:title"})
    meta_name = soup.find("meta", attrs={"name": "title"})
    h1 = soup.find("h1")
    page_title = soup.title.string if soup.title else None
    return _first_non_empty(
        meta_og["content"] if meta_og and meta_og.get("content") else None,
        meta_name["content"] if meta_name and meta_name.get("content") else None,
        h1.get_text(" ", strip=True) if h1 else None,
        page_title,
    )


def _derive_job_title(raw_title: str | None, site_name: str | None) -> str | None:
    if not raw_title:
        return None
    candidates = re.split(r"\s+[|\-\u2013\u2014]\s+", raw_title)
    candidates = [_clean(c) for c in candidates if _clean(c)]
    if not candidates:
        return None
    if site_name:
        site_lower = site_name.lower()
        for candidate in candidates:
            if candidate and site_lower not in candidate.lower():
                return candidate
    return candidates[0]


def _derive_organization_from_soup(title: str | None, site_name: str | None, text: str, url: str) -> str | None:
    org_keywords = (
        "university", "college", "school", "hospital", "health", "institute",
        "lab", "laboratory", "center", "centre", "company", "inc", "llc", "corp",
        "foundation", "association", "group", "partners",
    )

    title_parts = re.split(r"\s+[|\-\u2013\u2014]\s+", title or "")
    title_parts = [_clean(p) for p in title_parts if _clean(p)]

    for part in reversed(title_parts):
        if part and any(kw in part.lower() for kw in org_keywords):
            return part

    match = re.search(
        r"\b([A-Z][A-Za-z&.\- ]+(?:University|College|School|Institute|Hospital|Laboratory|Lab|Center|Centre|Inc|LLC|Corp|Foundation))\b",
        text,
    )
    if match:
        return _clean(match.group(1))

    if site_name and not _is_job_board(url):
        if any(kw in site_name.lower() for kw in org_keywords):
            return site_name

    host = urlparse(url).netloc.lower()
    path = urlparse(url).path.lower()
    for domain in JOB_BOARD_DOMAINS:
        if domain in host:
            subdomain = host.split("." + domain)[0].split(".")[0]
            subdomain = subdomain.replace("-", " ").replace("_", " ").strip()
            if subdomain and len(subdomain) > 2 and subdomain not in ("www", "jobs", "careers", "apply"):
                return subdomain.title()
            path_match = re.search(r"(?:staff-careers|careers|jobs)-([a-z]+)", path)
            if path_match:
                return path_match.group(1).title()

    return None


def _extract_job_id_from_text(text: str) -> str | None:
    patterns = [
        r"Job(?:\s+)ID[:#\s-]*([A-Z0-9\-]{4,})",
        r"Requisition(?:\s+)ID[:#\s-]*([A-Z0-9\-]{4,})",
        r"Req(?:\s+)ID[:#\s-]*([A-Z0-9\-]{4,})",
        r"\bREQ-?\d{4,}\b",
        r"\bJR-?\d{4,}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _clean(match.group(1) if match.lastindex else match.group(0))
    return None


def _extract_location_from_text(text: str) -> str | None:
    work_mode = re.search(r"\b(Remote|Hybrid|On-?site)\b", text, re.IGNORECASE)
    if work_mode:
        return work_mode.group(1).title()
    city_state = re.search(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?,\s?[A-Z]{2})\b", text)
    if city_state:
        return _clean(city_state.group(1))
    return None


def _extract_email_from_text(text: str) -> str | None:
    match = re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", text, flags=re.IGNORECASE)
    return _clean(match.group(0)) if match else None


def _classify_job_type(title: str | None, org: str | None, text_sample: str) -> str | None:
    combined = f"{title or ''} {org or ''} {text_sample[:2000]}".lower()

    if "intern" in combined:
        return "internship"
    if "fellow" in combined:
        return "fellowship"
    if "faculty" in combined or "professor" in combined or "lecturer" in combined:
        return "academic"
    if "contract" in combined or "temporary" in combined or "consultant" in combined:
        return "contract"
    if "research" in combined:
        return "research"

    return "industry"


def extract_job_application_defaults(url: str) -> dict[str, str | None]:
    cleaned_url = _clean(url)
    if not cleaned_url:
        raise ValueError("Job URL is required.")

    response = requests.get(
        cleaned_url,
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    job_data = _extract_json_ld(soup)

    site_name = _extract_site_name(soup, cleaned_url)
    visible_text = _extract_visible_text(soup)

    if job_data:
        raw_title = _clean(job_data.get("title")) or _extract_title_from_soup(soup)
        organization = _parse_json_ld_org(job_data) or _derive_organization_from_soup(raw_title, site_name, visible_text, cleaned_url)
        _work_mode = re.search(r"\b(Remote|Hybrid|On-?site)\b", visible_text, re.IGNORECASE)
        location = (_work_mode.group(1).title() if _work_mode else None) or _parse_json_ld_location(job_data) or _extract_location_from_text(visible_text)
        job_id = _parse_json_ld_job_id(job_data) or _extract_job_id_from_text(visible_text)
        department = _parse_json_ld_department(job_data)
        if not department:
            dept_match = re.search(r"Department[:\s]+([^\n|]{4,100})", visible_text, re.IGNORECASE)
            if dept_match:
                candidate = _clean(dept_match.group(1))
                if candidate and len(candidate) < 100 and not any(w in candidate.lower() for w in ("full time", "part time", "grade", "worker")):
                    department = candidate
        description_sample = _clean(str(job_data.get("description", "")))[:2000] if job_data.get("description") else visible_text[:2000]
    else:
        raw_title = _extract_title_from_soup(soup)
        organization = _derive_organization_from_soup(raw_title, site_name, visible_text, cleaned_url)
        location = _extract_location_from_text(visible_text)
        job_id = _extract_job_id_from_text(visible_text)
        department = None
        description_sample = visible_text[:2000]

    job_title = _derive_job_title(raw_title, site_name)

    if not job_title:
        raise ValueError("Could not extract a job title from this URL.")

    if not organization:
        host = urlparse(cleaned_url).netloc.lower()
        path = urlparse(cleaned_url).path.lower()
        for domain in JOB_BOARD_DOMAINS:
            if domain in host:
                subdomain = host.split("." + domain)[0].split(".")[0]
                subdomain = subdomain.replace("-", " ").replace("_", " ").strip()
                if subdomain and len(subdomain) > 2 and subdomain not in ("www", "jobs", "careers", "apply", "wd5", "wd1", "wd3"):
                    organization = subdomain.title()
                    break
        if not organization:
            path_match = re.search(r"(?:staff-careers|careers|jobs)-([a-z]+)", path)
            if path_match:
                organization = path_match.group(1).title()

    return {
        "organization": organization or "",
        "company": None,
        "department_lab": department or "",
        "job_title": job_title,
        "job_id": job_id,
        "location": location,
        "application_date": date.today().isoformat(),
        "status": "applied",
        "job_type": _classify_job_type(job_title, organization, description_sample),
        "interview_stage": None,
        "contact_name": None,
        "contact_email": _clean(str(job_data.get("applicationContact", {}).get("email", "") or "")) or _extract_email_from_text(visible_text) if job_data else _extract_email_from_text(visible_text),
        "follow_up_date": None,
        "notes": f"Imported from: {cleaned_url}",
    }
