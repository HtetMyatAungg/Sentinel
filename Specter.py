"""Specter API client."""
import os
from typing import Optional, Dict, Any
import httpx


SPECTER_BASE = "https://app.tryspecter.com/api/v1"


class SpecterError(Exception):
    """Raised when Specter API returns an error or no match."""


def _headers() -> Dict[str, str]:
    api_key = os.getenv("SPECTER_API_KEY")
    if not api_key:
        raise SpecterError("Missing SPECTER_API_KEY for Specter API calls.")
    return {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }


def search_company(name: str) -> Optional[str]:
    """Resolve a company name to a domain via Specter company search."""
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(
                f"{SPECTER_BASE}/companies/search",
                headers=_headers(),
                params={"query": name},
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.json()
            if not data:
                return None
            first = data[0] if isinstance(data, list) else data
            return first.get("domain")
    except httpx.HTTPError as e:
        raise SpecterError(f"company search failed: {e}") from e


def enrich_company(domain: str) -> Dict[str, Any]:
    """Enrich a domain into a full Specter profile, slimmed to the fields we use."""
    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.post(
                f"{SPECTER_BASE}/companies",
                headers=_headers(),
                json={"domain": domain},
            )
            r.raise_for_status()
            data = r.json()
            if not data:
                raise SpecterError(f"No Specter match for domain: {domain}")
            return _slim_profile(data[0])
    except httpx.HTTPError as e:
        raise SpecterError(f"enrichment failed: {e}") from e


def _slim_profile(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Trim Specter response to only the fields the agent reasons over.
    Keeps the prompt tight and reduces token usage."""
    funding = raw.get("funding") or {}
    traction = raw.get("traction_metrics") or {}
    headcount_12mo = (traction.get("employee_count") or {}).get("12mo") or {}
    web_12mo = (traction.get("web_visits") or {}).get("12mo") or {}

    return {
        "id": raw.get("id"),
        "organization_name": raw.get("organization_name"),
        "description": raw.get("description"),
        "operating_status": raw.get("operating_status"),
        "growth_stage": raw.get("growth_stage"),
        "founded_year": raw.get("founded_year"),
        "employee_count": raw.get("employee_count"),
        "employee_count_range": raw.get("employee_count_range"),
        "revenue_estimate_usd": raw.get("revenue_estimate_usd"),
        "investors": (raw.get("investors") or [])[:10],
        "investor_count": raw.get("investor_count"),
        "highlights": raw.get("highlights") or [],
        "funding": {
            "total_funding_usd": funding.get("total_funding_usd"),
            "last_funding_usd": funding.get("last_funding_usd"),
            "last_funding_date": funding.get("last_funding_date"),
            "last_funding_type": funding.get("last_funding_type"),
            "round_count": funding.get("round_count"),
        },
        "awards_count": len(raw.get("awards") or []),
        "certifications": raw.get("certifications") or [],
        "acquisition": raw.get("acquisition"),
        "news": (raw.get("news") or [])[:3],
        "headcount_12mo_change_pct": headcount_12mo.get("percentage"),
        "web_visits_12mo_change_pct": web_12mo.get("percentage"),
    }