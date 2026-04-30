"""Specter API client. Real calls when SPECTER_API_KEY is set, mocks otherwise."""
import os
from typing import Optional, Dict, Any
import httpx

SPECTER_BASE = "https://app.tryspecter.com/api/v1"
MOCK_MODE = os.getenv("MOCK_MODE", "0") == "1" or not os.getenv("SPECTER_API_KEY")

MOCK_FIXTURES = {
    "stripe.com": {
        "id": "spec_stripe_001",
        "organization_name": "Stripe",
        "description": "Online payment processing for internet businesses.",
        "operating_status": "active",
        "growth_stage": "late_stage",
        "founded_year": 2010,
        "employee_count": 8000,
        "employee_count_range": "5001-10000",
        "revenue_estimate_usd": 14000000000,
        "investors": ["Sequoia Capital", "Andreessen Horowitz", "GV", "Founders Fund"],
        "investor_count": 30,
        "highlights": ["top_tier_investors", "strong_headcount_growth", "strong_web_traffic_growth", "strong_social_growth"],
        "funding": {"total_funding_usd": 9000000000, "last_funding_usd": 6500000000, "last_funding_date": "2023-03-15", "last_funding_type": "series_i", "round_count": 9},
        "awards": [{"award_name": "Forbes Cloud 100", "award_year": 2024}],
        "certifications": [["SOC 2", "PCI DSS", "ISO 27001"]],
        "acquisition": None,
        "news": [{"date": "2025-08-01", "title": "Stripe expands UK operations", "publisher": "FT"}],
        "traction_metrics": {"employee_count": {"12mo": {"change": 800, "percentage": 11}}, "web_visits": {"12mo": {"change": 2500000, "percentage": 18}}},
    },
    "ravelin.com": {
        "id": "spec_ravelin_002",
        "organization_name": "Ravelin",
        "description": "Fraud detection and prevention for online merchants.",
        "operating_status": "active",
        "growth_stage": "growth_stage",
        "founded_year": 2015,
        "employee_count": 110,
        "employee_count_range": "51-200",
        "revenue_estimate_usd": 18000000,
        "investors": ["Amadeus Capital Partners", "Passion Capital"],
        "investor_count": 4,
        "highlights": ["no_recent_funding", "strong_web_traffic_growth"],
        "funding": {"total_funding_usd": 28000000, "last_funding_usd": 20000000, "last_funding_date": "2021-06-01", "last_funding_type": "series_b", "round_count": 3},
        "awards": [],
        "certifications": [["ISO 27001", "GDPR"]],
        "acquisition": None,
        "news": [],
        "traction_metrics": {"employee_count": {"12mo": {"change": -8, "percentage": -7}}, "web_visits": {"12mo": {"change": 12000, "percentage": 8}}},
    },
    "monzo.com": {
        "id": "spec_monzo_003",
        "organization_name": "Monzo",
        "description": "UK digital challenger bank.",
        "operating_status": "active",
        "growth_stage": "late_stage",
        "founded_year": 2015,
        "employee_count": 3500,
        "employee_count_range": "1001-5000",
        "revenue_estimate_usd": 880000000,
        "investors": ["Accel", "General Catalyst", "GV", "Y Combinator"],
        "investor_count": 18,
        "highlights": ["top_tier_investors", "strong_headcount_growth", "strong_social_growth"],
        "funding": {"total_funding_usd": 1500000000, "last_funding_usd": 610000000, "last_funding_date": "2025-03-01", "last_funding_type": "series_i", "round_count": 12},
        "awards": [{"award_name": "Best UK Challenger Bank", "award_year": 2024}],
        "certifications": [["SOC 2", "ISO 27001", "FCA Regulated"]],
        "acquisition": None,
        "news": [{"date": "2025-09-15", "title": "Monzo IPO filing reported", "publisher": "Bloomberg"}],
        "traction_metrics": {"employee_count": {"12mo": {"change": 700, "percentage": 25}}, "web_visits": {"12mo": {"change": 800000, "percentage": 22}}},
    },
}

NAME_TO_DOMAIN = {"stripe": "stripe.com", "ravelin": "ravelin.com", "monzo": "monzo.com", "monzo bank": "monzo.com"}

class SpecterError(Exception):
    """Raised when Specter API returns an error or no match."""

def _headers() -> Dict[str, str]:
    return {"X-API-Key": os.environ["SPECTER_API_KEY"], "Content-Type": "application/json"}

def search_company(name: str) -> Optional[str]:
    if MOCK_MODE:
        key = name.lower().strip()
        for k, v in NAME_TO_DOMAIN.items():
            if k in key or key in k:
                return v
        return None
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(f"{SPECTER_BASE}/entities", headers=_headers(), json={"query": name, "limit": 1})
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.json()
            if not data:
                return None
            first = data[0] if isinstance(data, list) else data
            return first.get("website", {}).get("domain") or first.get("domain")
    except httpx.HTTPError as e:
        raise SpecterError(f"text-search failed: {e}") from e

def enrich_company(domain: str) -> Dict[str, Any]:
    if MOCK_MODE:
        if domain not in MOCK_FIXTURES:
            raise SpecterError(f"No Specter match for domain: {domain}")
        return _slim_profile(MOCK_FIXTURES[domain])
    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.post(f"{SPECTER_BASE}/companies", headers=_headers(), json={"domain": domain})
            r.raise_for_status()
            data = r.json()
            if not data:
                raise SpecterError(f"No Specter match for domain: {domain}")
            return _slim_profile(data[0])
    except httpx.HTTPError as e:
        raise SpecterError(f"enrichment failed: {e}") from e

def _slim_profile(raw: Dict[str, Any]) -> Dict[str, Any]:
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
"""Specter API client. Real calls when SPECTER_API_KEY is set, mocks otherwise."""
import os
from typing import Optional, Dict, Any
import httpx


SPECTER_BASE = "https://app.tryspecter.com/api/v1"
MOCK_MODE = os.getenv("MOCK_MODE", "0") == "1" or not os.getenv("SPECTER_API_KEY")


MOCK_FIXTURES = {
    "stripe.com": {
        "id": "spec_stripe_001",
        "organization_name": "Stripe",
        "description": "Online payment processing for internet businesses.",
        "operating_status": "active",
        "growth_stage": "late_stage",
        "founded_year": 2010,
        "employee_count": 8000,
        "employee_count_range": "5001-10000",
        "revenue_estimate_usd": 14000000000,
        "investors": ["Sequoia Capital", "Andreessen Horowitz", "GV", "Founders Fund"],
        "investor_count": 30,
        "highlights": [
            "top_tier_investors",
            "strong_headcount_growth",
            "strong_web_traffic_growth",
            "strong_social_growth",
        ],
        "funding": {
            "total_funding_usd": 9000000000,
            "last_funding_usd": 6500000000,
            "last_funding_date": "2023-03-15",
            "last_funding_type": "series_i",
            "round_count": 9,
        },
        "awards": [{"award_name": "Forbes Cloud 100", "award_year": 2024}],
        "certifications": [["SOC 2", "PCI DSS", "ISO 27001"]],
        "acquisition": None,
        "news": [
            {"date": "2025-08-01", "title": "Stripe expands UK operations", "publisher": "FT"},
        ],
        "traction_metrics": {
            "employee_count": {"12mo": {"change": 800, "percentage": 11}},
            "web_visits": {"12mo": {"change": 2500000, "percentage": 18}},
        },
    },
    "ravelin.com": {
        "id": "spec_ravelin_002",
        "organization_name": "Ravelin",
        "description": "Fraud detection and prevention for online merchants.",
        "operating_status": "active",
        "growth_stage": "growth_stage",
        "founded_year": 2015,
        "employee_count": 110,
        "employee_count_range": "51-200",
        "revenue_estimate_usd": 18000000,
        "investors": ["Amadeus Capital Partners", "Passion Capital"],
        "investor_count": 4,
        "highlights": [
            "no_recent_funding",
            "strong_web_traffic_growth",
        ],
        "funding": {
            "total_funding_usd": 28000000,
            "last_funding_usd": 20000000,
            "last_funding_date": "2021-06-01",
            "last_funding_type": "series_b",
            "round_count": 3,
        },
        "awards": [],
        "certifications": [["ISO 27001", "GDPR"]],
        "acquisition": None,
        "news": [],
        "traction_metrics": {
            "employee_count": {"12mo": {"change": -8, "percentage": -7}},
            "web_visits": {"12mo": {"change": 12000, "percentage": 8}},
        },
    },
    "monzo.com": {
        "id": "spec_monzo_003",
        "organization_name": "Monzo",
        "description": "UK digital challenger bank.",
        "operating_status": "active",
        "growth_stage": "late_stage",
        "founded_year": 2015,
        "employee_count": 3500,
        "employee_count_range": "1001-5000",
        "revenue_estimate_usd": 880000000,
        "investors": ["Accel", "General Catalyst", "GV", "Y Combinator"],
        "investor_count": 18,
        "highlights": [
            "top_tier_investors",
            "strong_headcount_growth",
            "strong_social_growth",
        ],
        "funding": {
            "total_funding_usd": 1500000000,
            "last_funding_usd": 610000000,
            "last_funding_date": "2025-03-01",
            "last_funding_type": "series_i",
            "round_count": 12,
        },
        "awards": [{"award_name": "Best UK Challenger Bank", "award_year": 2024}],
        "certifications": [["SOC 2", "ISO 27001", "FCA Regulated"]],
        "acquisition": None,
        "news": [
            {"date": "2025-09-15", "title": "Monzo IPO filing reported", "publisher": "Bloomberg"},
        ],
        "traction_metrics": {
            "employee_count": {"12mo": {"change": 700, "percentage": 25}},
            "web_visits": {"12mo": {"change": 800000, "percentage": 22}},
        },
    },
    "afterpay.com": {
        "id": "spec_afterpay_004",
        "organization_name": "Afterpay",
        "description": "Buy-now-pay-later provider acquired by Block.",
        "operating_status": "acquired",
        "growth_stage": "late_stage",
        "founded_year": 2014,
        "employee_count": 1600,
        "employee_count_range": "1001-5000",
        "revenue_estimate_usd": 950000000,
        "investors": ["Tiger Global", "Bond", "Coatue"],
        "investor_count": 9,
        "highlights": ["top_tier_investors", "strong_web_traffic_growth"],
        "funding": {
            "total_funding_usd": 600000000,
            "last_funding_usd": 40000000,
            "last_funding_date": "2020-09-10",
            "last_funding_type": "venture",
            "round_count": 6,
        },
        "awards": [],
        "certifications": [["SOC 2"]],
        "acquisition": {"acquirer_name": "Block", "acquisition_date": "2022-01-31"},
        "news": [
            {"date": "2022-01-31", "title": "Block completes Afterpay acquisition", "publisher": "Reuters"},
        ],
        "traction_metrics": {
            "employee_count": {"12mo": {"change": 40, "percentage": 3}},
            "web_visits": {"12mo": {"change": 350000, "percentage": 12}},
        },
    },
}

NAME_TO_DOMAIN = {
    "stripe": "stripe.com",
    "ravelin": "ravelin.com",
    "monzo": "monzo.com",
    "monzo bank": "monzo.com",
    "afterpay": "afterpay.com",
}


class SpecterError(Exception):
    """Raised when Specter API returns an error or no match."""


def _headers() -> Dict[str, str]:
    return {
        "X-API-Key": os.environ["SPECTER_API_KEY"],
        "Content-Type": "application/json",
    }


def search_company(name: str) -> Optional[str]:
    """Resolve a company name to a domain. Returns None if no match."""
    if MOCK_MODE:
        key = name.lower().strip()
        for k, v in NAME_TO_DOMAIN.items():
            if k in key or key in k:
                return v
        return None

    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(
                f"{SPECTER_BASE}/entities",
                headers=_headers(),
                json={"query": name, "limit": 1},
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.json()
            if not data:
                return None
            first = data[0] if isinstance(data, list) else data
            return first.get("website", {}).get("domain") or first.get("domain")
    except httpx.HTTPError as e:
        raise SpecterError(f"text-search failed: {e}") from e


def enrich_company(domain: str) -> Dict[str, Any]:
    """Enrich a domain into a full Specter profile, slimmed to the fields we use."""
    if MOCK_MODE:
        if domain not in MOCK_FIXTURES:
            raise SpecterError(f"No Specter match for domain: {domain}")
        return _slim_profile(MOCK_FIXTURES[domain])

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
    """Trim Specter response to only the fields the agent reasons over."""
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
"""Specter API client. Real calls when SPECTER_API_KEY is set, mocks otherwise."""
import os
from typing import Optional, Dict, Any
import httpx


SPECTER_BASE = "https://app.tryspecter.com/api/v1"
MOCK_MODE = os.getenv("MOCK_MODE", "0") == "1" or not os.getenv("SPECTER_API_KEY")


# Mock fixtures — match the real Specter response shape so the swap is transparent
MOCK_FIXTURES = {
    "stripe.com": {
        "id": "spec_stripe_001",
        "organization_name": "Stripe",
        "description": "Online payment processing for internet businesses.",
        "operating_status": "active",
        "growth_stage": "late_stage",
        "founded_year": 2010,
        "employee_count": 8000,
        "employee_count_range": "5001-10000",
        "revenue_estimate_usd": 14000000000,
        "investors": ["Sequoia Capital", "Andreessen Horowitz", "GV", "Founders Fund"],
        "investor_count": 30,
        "highlights": [
            "top_tier_investors",
            "strong_headcount_growth",
            "strong_web_traffic_growth",
            "strong_social_growth",
        ],
        "funding": {
            "total_funding_usd": 9000000000,
            "last_funding_usd": 6500000000,
            "last_funding_date": "2023-03-15",
            "last_funding_type": "series_i",
            "round_count": 9,
        },
        "awards": [{"award_name": "Forbes Cloud 100", "award_year": 2024}],
        "certifications": [["SOC 2", "PCI DSS", "ISO 27001"]],
        "acquisition": None,
        "news": [
            {"date": "2025-08-01", "title": "Stripe expands UK operations", "publisher": "FT"},
        ],
        "traction_metrics": {
            "employee_count": {"12mo": {"change": 800, "percentage": 11}},
            "web_visits": {"12mo": {"change": 2500000, "percentage": 18}},
        },
    },
    "ravelin.com": {
        "id": "spec_ravelin_002",
        "organization_name": "Ravelin",
        "description": "Fraud detection and prevention for online merchants.",
        "operating_status": "active",
        "growth_stage": "growth_stage",
        "founded_year": 2015,
        "employee_count": 110,
        "employee_count_range": "51-200",
        "revenue_estimate_usd": 18000000,
        "investors": ["Amadeus Capital Partners", "Passion Capital"],
        "investor_count": 4,
        "highlights": [
            "no_recent_funding",
            "strong_web_traffic_growth",
        ],
        "funding": {
            "total_funding_usd": 28000000,
            "last_funding_usd": 20000000,
            "last_funding_date": "2021-06-01",
            "last_funding_type": "series_b",
            "round_count": 3,
        },
        "awards": [],
        "certifications": [["ISO 27001", "GDPR"]],
        "acquisition": None,
        "news": [],
        "traction_metrics": {
            "employee_count": {"12mo": {"change": -8, "percentage": -7}},
            "web_visits": {"12mo": {"change": 12000, "percentage": 8}},
        },
    },
    "monzo.com": {
        "id": "spec_monzo_003",
        "organization_name": "Monzo",
        "description": "UK digital challenger bank.",
        "operating_status": "active",
        "growth_stage": "late_stage",
        "founded_year": 2015,
        "employee_count": 3500,
        "employee_count_range": "1001-5000",
        "revenue_estimate_usd": 880000000,
        "investors": ["Accel", "General Catalyst", "GV", "Y Combinator"],
        "investor_count": 18,
        "highlights": [
            "top_tier_investors",
            "strong_headcount_growth",
            "strong_social_growth",
        ],
        "funding": {
            "total_funding_usd": 1500000000,
            "last_funding_usd": 610000000,
            "last_funding_date": "2025-03-01",
            "last_funding_type": "series_i",
            "round_count": 12,
        },
        "awards": [{"award_name": "Best UK Challenger Bank", "award_year": 2024}],
        "certifications": [["SOC 2", "ISO 27001", "FCA Regulated"]],
        "acquisition": None,
        "news": [
            {"date": "2025-09-15", "title": "Monzo IPO filing reported", "publisher": "Bloomberg"},
        ],
        "traction_metrics": {
            "employee_count": {"12mo": {"change": 700, "percentage": 25}},
            "web_visits": {"12mo": {"change": 800000, "percentage": 22}},
        },
    },
    "afterpay.com": {
        "id": "spec_afterpay_004",
        "organization_name": "Afterpay",
        "description": "Buy-now-pay-later provider acquired by Block.",
        "operating_status": "acquired",
        "growth_stage": "late_stage",
        "founded_year": 2014,
        "employee_count": 1600,
        "employee_count_range": "1001-5000",
        "revenue_estimate_usd": 950000000,
        "investors": ["Tiger Global", "Bond", "Coatue"],
        "investor_count": 9,
        "highlights": ["top_tier_investors", "strong_web_traffic_growth"],
        "funding": {
            "total_funding_usd": 600000000,
            "last_funding_usd": 40000000,
            "last_funding_date": "2020-09-10",
            "last_funding_type": "venture",
            "round_count": 6,
        },
        "awards": [],
        "certifications": [["SOC 2"]],
        "acquisition": {"acquirer_name": "Block", "acquisition_date": "2022-01-31"},
        "news": [
            {"date": "2022-01-31", "title": "Block completes Afterpay acquisition", "publisher": "Reuters"},
        ],
        "traction_metrics": {
            "employee_count": {"12mo": {"change": 40, "percentage": 3}},
            "web_visits": {"12mo": {"change": 350000, "percentage": 12}},
        },
    },
}


# Name → domain resolution table (mock for the text search step)
NAME_TO_DOMAIN = {
    "stripe": "stripe.com",
    "ravelin": "ravelin.com",
    "monzo": "monzo.com",
    "monzo bank": "monzo.com",
    "afterpay": "afterpay.com",
}


class SpecterError(Exception):
    """Raised when Specter API returns an error or no match."""


def _headers() -> Dict[str, str]:
    return {
        "X-API-Key": os.environ["SPECTER_API_KEY"],
        "Content-Type": "application/json",
    }


def search_company(name: str) -> Optional[str]:
    """Resolve a company name to a domain. Returns None if no match."""
    if MOCK_MODE:
        key = name.lower().strip()
        for k, v in NAME_TO_DOMAIN.items():
            if k in key or key in k:
                return v
        return None

    # Real call: text search to find the company
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(
                f"{SPECTER_BASE}/entities",
                headers=_headers(),
                json={"query": name, "limit": 1},
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.json()
            if not data:
                return None
            # Response shape: list of entity matches; pull domain from first
            first = data[0] if isinstance(data, list) else data
            return first.get("website", {}).get("domain") or first.get("domain")
    except httpx.HTTPError as e:
        raise SpecterError(f"text-search failed: {e}") from e


def enrich_company(domain: str) -> Dict[str, Any]:
    """Enrich a domain into a full Specter profile, slimmed to the fields we use."""
    if MOCK_MODE:
        if domain not in MOCK_FIXTURES:
            raise SpecterError(f"No Specter match for domain: {domain}")
        return _slim_profile(MOCK_FIXTURES[domain])

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
"""Specter API client. Real calls when SPECTER_API_KEY is set, mocks otherwise."""
import os
from typing import Optional, Dict, Any
import httpx


SPECTER_BASE = "https://app.tryspecter.com/api/v1"
MOCK_MODE = os.getenv("MOCK_MODE", "0") == "1" or not os.getenv("SPECTER_API_KEY")


# Mock fixtures — match the real Specter response shape so the swap is transparent
MOCK_FIXTURES = {
    "stripe.com": {
        "id": "spec_stripe_001",
        "organization_name": "Stripe",
        "description": "Online payment processing for internet businesses.",
        "operating_status": "active",
        "growth_stage": "late_stage",
        "founded_year": 2010,
        "employee_count": 8000,
        "employee_count_range": "5001-10000",
        "revenue_estimate_usd": 14000000000,
        "investors": ["Sequoia Capital", "Andreessen Horowitz", "GV", "Founders Fund"],
        "investor_count": 30,
        "highlights": [
            "top_tier_investors",
            "strong_headcount_growth",
            "strong_web_traffic_growth",
            "strong_social_growth",
        ],
        "funding": {
            "total_funding_usd": 9000000000,
            "last_funding_usd": 6500000000,
            "last_funding_date": "2023-03-15",
            "last_funding_type": "series_i",
            "round_count": 9,
        },
        "awards": [{"award_name": "Forbes Cloud 100", "award_year": 2024}],
        "certifications": [["SOC 2", "PCI DSS", "ISO 27001"]],
        "acquisition": None,
        "news": [
            {"date": "2025-08-01", "title": "Stripe expands UK operations", "publisher": "FT"},
        ],
        "traction_metrics": {
            "employee_count": {"12mo": {"change": 800, "percentage": 11}},
            "web_visits": {"12mo": {"change": 2500000, "percentage": 18}},
        },
    },
    "ravelin.com": {
        "id": "spec_ravelin_002",
        "organization_name": "Ravelin",
        "description": "Fraud detection and prevention for online merchants.",
        "operating_status": "active",
        "growth_stage": "growth_stage",
        "founded_year": 2015,
        "employee_count": 110,
        "employee_count_range": "51-200",
        "revenue_estimate_usd": 18000000,
        "investors": ["Amadeus Capital Partners", "Passion Capital"],
        "investor_count": 4,
        "highlights": [
            "no_recent_funding",
            "strong_web_traffic_growth",
        ],
        "funding": {
            "total_funding_usd": 28000000,
            "last_funding_usd": 20000000,
            "last_funding_date": "2021-06-01",
            "last_funding_type": "series_b",
            "round_count": 3,
        },
        "awards": [],
        "certifications": [["ISO 27001", "GDPR"]],
        "acquisition": None,
        "news": [],
        "traction_metrics": {
            "employee_count": {"12mo": {"change": -8, "percentage": -7}},
            "web_visits": {"12mo": {"change": 12000, "percentage": 8}},
        },
    },
    "monzo.com": {
        "id": "spec_monzo_003",
        "organization_name": "Monzo",
        "description": "UK digital challenger bank.",
        "operating_status": "active",
        "growth_stage": "late_stage",
        "founded_year": 2015,
        "employee_count": 3500,
        "employee_count_range": "1001-5000",
        "revenue_estimate_usd": 880000000,
        "investors": ["Accel", "General Catalyst", "GV", "Y Combinator"],
        "investor_count": 18,
        "highlights": [
            "top_tier_investors",
            "strong_headcount_growth",
            "strong_social_growth",
        ],
        "funding": {
            "total_funding_usd": 1500000000,
            "last_funding_usd": 610000000,
            "last_funding_date": "2025-03-01",
            "last_funding_type": "series_i",
            "round_count": 12,
        },
        "awards": [{"award_name": "Best UK Challenger Bank", "award_year": 2024}],
        "certifications": [["SOC 2", "ISO 27001", "FCA Regulated"]],
        "acquisition": None,
        "news": [
            {"date": "2025-09-15", "title": "Monzo IPO filing reported", "publisher": "Bloomberg"},
        ],
        "traction_metrics": {
            "employee_count": {"12mo": {"change": 700, "percentage": 25}},
            "web_visits": {"12mo": {"change": 800000, "percentage": 22}},
        },
    },
    "afterpay.com": {
        "id": "spec_afterpay_004",
        "organization_name": "Afterpay",
        "description": "Buy-now-pay-later provider acquired by Block.",
        "operating_status": "acquired",
        "growth_stage": "late_stage",
        "founded_year": 2014,
        "employee_count": 1600,
        "employee_count_range": "1001-5000",
        "revenue_estimate_usd": 950000000,
        "investors": ["Tiger Global", "Bond", "Coatue"],
        "investor_count": 9,
        "highlights": ["top_tier_investors", "strong_web_traffic_growth"],
        "funding": {
            "total_funding_usd": 600000000,
            "last_funding_usd": 40000000,
            "last_funding_date": "2020-09-10",
            "last_funding_type": "venture",
            "round_count": 6,
        },
        "awards": [],
        "certifications": [["SOC 2"]],
        "acquisition": {"acquirer_name": "Block", "acquisition_date": "2022-01-31"},
        "news": [
            {"date": "2022-01-31", "title": "Block completes Afterpay acquisition", "publisher": "Reuters"},
        ],
        "traction_metrics": {
            "employee_count": {"12mo": {"change": 40, "percentage": 3}},
            "web_visits": {"12mo": {"change": 350000, "percentage": 12}},
        },
    },
}


# Name → domain resolution table (mock for the text search step)
NAME_TO_DOMAIN = {
    "stripe": "stripe.com",
    "ravelin": "ravelin.com",
    "monzo": "monzo.com",
    "monzo bank": "monzo.com",
    "afterpay": "afterpay.com",
}


class SpecterError(Exception):
    """Raised when Specter API returns an error or no match."""


def _headers() -> Dict[str, str]:
    return {
        "X-API-Key": os.environ["SPECTER_API_KEY"],
        "Content-Type": "application/json",
    }


def search_company(name: str) -> Optional[str]:
    """Resolve a company name to a domain. Returns None if no match."""
    if MOCK_MODE:
        key = name.lower().strip()
        for k, v in NAME_TO_DOMAIN.items():
            if k in key or key in k:
                return v
        return None

    # Real call: text search to find the company
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(
                f"{SPECTER_BASE}/entities",
                headers=_headers(),
                json={"query": name, "limit": 1},
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.json()
            if not data:
                return None
            # Response shape: list of entity matches; pull domain from first
            first = data[0] if isinstance(data, list) else data
            return first.get("website", {}).get("domain") or first.get("domain")
    except httpx.HTTPError as e:
        raise SpecterError(f"text-search failed: {e}") from e


def enrich_company(domain: str) -> Dict[str, Any]:
    """Enrich a domain into a full Specter profile, slimmed to the fields we use."""
    if MOCK_MODE:
        if domain not in MOCK_FIXTURES:
            raise SpecterError(f"No Specter match for domain: {domain}")
        return _slim_profile(MOCK_FIXTURES[domain])

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