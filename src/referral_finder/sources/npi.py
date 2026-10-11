"""NPI Registry (CMS) organization search."""
import logging
import time

import httpx
from pydantic import BaseModel

from referral_finder import cache
from referral_finder.config import load_config
from referral_finder.normalize import phone10, zip5

logger = logging.getLogger(__name__)


class Lead(BaseModel):
    npi: str
    name: str
    category: str
    address_line: str | None = None
    zip5: str | None = None
    borough: str
    main_phone: str | None = None
    main_phone_normalized: str | None = None
    official_name: str | None = None
    official_title: str | None = None
    official_phone: str | None = None


def _get(settings: dict, params: dict) -> dict:
    """One API call with timeout, retry with backoff, and disk cache."""
    cached = cache.get("npi", params, settings["cache_ttl_days"])
    if cached is not None:
        return cached
    for attempt in range(settings["retries"]):
        try:
            r = httpx.get(settings["base_url"], params=params, timeout=settings["timeout_seconds"])
            r.raise_for_status()
            data = r.json()
            cache.put("npi", params, data)
            time.sleep(settings["request_delay_seconds"])
            return data
        except httpx.HTTPError as exc:
            logger.warning("NPI request failed (attempt %d): %s", attempt + 1, exc)
            if attempt == settings["retries"] - 1:
                raise
            time.sleep(2**attempt)


def _search(settings: dict, taxonomy: str, state: str, prefix: str) -> list[dict]:
    """All pages for one taxonomy term + ZIP prefix."""
    size = settings["page_size"]
    results: list[dict] = []
    skip = 0
    while True:
        params = {
            "version": settings["version"],
            "enumeration_type": "NPI-2",
            "taxonomy_description": taxonomy,
            "postal_code": f"{prefix}*",
            "state": state,
            "address_purpose": "LOCATION",
            "limit": size,
            "skip": skip,
        }
        page = _get(settings, params).get("results") or []
        results += page
        if len(page) < size:
            break
        skip += size
        if skip > settings["max_skip"]:
            logger.warning("NPI query hit the result cap: %s %s*", taxonomy, prefix)
            break
    return results


def _to_lead(record: dict, category: str, borough: str, prefixes: list[str]) -> Lead | None:
    location = next((a for a in record["addresses"] if a["address_purpose"] == "LOCATION"), None)
    if not location:
        return None
    zip_ = zip5(location.get("postal_code"))
    if not zip_ or not zip_.startswith(tuple(prefixes)):
        return None
    basic = record["basic"]
    official = " ".join(
        p
        for p in (basic.get("authorized_official_first_name"), basic.get("authorized_official_last_name"))
        if p
    )
    phone = location.get("telephone_number")
    return Lead(
        npi=str(record["number"]),
        name=basic["organization_name"],
        category=category,
        address_line=location.get("address_1"),
        zip5=zip_,
        borough=borough,
        main_phone=phone,
        main_phone_normalized=phone10(phone),
        official_name=official or None,
        official_title=basic.get("authorized_official_title_or_position") or None,
        official_phone=basic.get("authorized_official_telephone_number") or None,
    )


def fetch_leads(borough: str) -> list[Lead]:
    """Organizations in the borough for every configured category (deduped by NPI)."""
    area = load_config("service_area")["boroughs"][borough]
    settings = load_config("service_area")["npi"]
    categories = load_config("scoring")["fit"]["categories"]
    leads: dict[str, Lead] = {}
    for category, spec in categories.items():
        for taxonomy in spec["taxonomies"]:
            for prefix in area["zip_prefixes"]:
                for record in _search(settings, taxonomy, area["state"], prefix):
                    primary = next((t["desc"] for t in record["taxonomies"] if t.get("primary")), "")
                    if not any(primary.startswith(t) for t in spec["taxonomies"]):
                        continue
                    lead = _to_lead(record, category, borough, area["zip_prefixes"])
                    if lead and lead.npi not in leads:
                        leads[lead.npi] = lead
    logger.info("Fetched %d leads for %s", len(leads), borough)
    return list(leads.values())
