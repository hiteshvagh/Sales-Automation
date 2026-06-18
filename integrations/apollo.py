from __future__ import annotations
import time
from typing import Optional
import httpx

from config.settings import APOLLO_API_KEY

BASE_URL = "https://api.apollo.io/v1"

SENIORITY_MAP = {
    "c_suite": 10, "founder": 10, "partner": 9, "vp": 8,
    "head": 7, "director": 7, "manager": 5, "senior": 4,
    "entry": 2, "intern": 1,
}


def _headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": APOLLO_API_KEY,
    }


def _post(path: str, payload: dict, retries: int = 3) -> dict:
    if not APOLLO_API_KEY:
        return {}
    url = f"{BASE_URL}{path}"
    for attempt in range(retries):
        try:
            resp = httpx.post(url, json=payload, headers=_headers(), timeout=30)
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if attempt == retries - 1:
                return {}
            time.sleep(1)
    return {}


def _get(path: str, params: dict = None, retries: int = 3) -> dict:
    if not APOLLO_API_KEY:
        return {}
    url = f"{BASE_URL}{path}"
    for attempt in range(retries):
        try:
            resp = httpx.get(url, params=params or {}, headers=_headers(), timeout=30)
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if attempt == retries - 1:
                return {}
            time.sleep(1)
    return {}


def search_people(
    titles: list[str],
    industries: list[str] = None,
    countries: list[str] = None,
    employee_ranges: list[str] = None,
    page: int = 1,
    per_page: int = 25,
) -> dict:
    payload = {
        "person_titles": titles,
        "page": page,
        "per_page": per_page,
    }
    if industries:
        payload["organization_industry_tag_ids"] = industries
    if countries:
        payload["person_locations"] = countries
    if employee_ranges:
        payload["organization_num_employees_ranges"] = employee_ranges
    return _post("/mixed_people/search", payload)


def search_organizations(
    industries: list[str] = None,
    countries: list[str] = None,
    employee_ranges: list[str] = None,
    keywords: list[str] = None,
    page: int = 1,
    per_page: int = 25,
) -> dict:
    payload = {"page": page, "per_page": per_page}
    if industries:
        payload["organization_industry_tag_ids"] = industries
    if countries:
        payload["organization_locations"] = countries
    if employee_ranges:
        payload["organization_num_employees_ranges"] = employee_ranges
    if keywords:
        payload["q_keywords"] = " ".join(keywords)
    return _post("/mixed_companies/search", payload)


def enrich_person(
    email: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    domain: Optional[str] = None,
) -> dict:
    payload = {}
    if email:
        payload["email"] = email
    if linkedin_url:
        payload["linkedin_url"] = linkedin_url
    if first_name:
        payload["first_name"] = first_name
    if last_name:
        payload["last_name"] = last_name
    if domain:
        payload["domain"] = domain
    return _post("/people/match", payload)


def enrich_organization(domain: str) -> dict:
    return _get("/organizations/enrich", {"domain": domain})


def get_job_postings(organization_id: str) -> dict:
    return _get(f"/organizations/{organization_id}/job_postings")


def authority_score_from_title(title: str) -> int:
    title_lower = title.lower()
    for keyword, score in SENIORITY_MAP.items():
        if keyword.replace("_", " ") in title_lower or keyword in title_lower:
            return score
    return 3
