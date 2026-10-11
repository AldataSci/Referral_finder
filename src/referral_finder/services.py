"""Functions the UI and scripts call. Errors are reported to Sentry."""
import functools

import httpx
from pydantic import BaseModel, ConfigDict

from referral_finder import calls, contact_finder, db, geo
from referral_finder.config import load_config
from referral_finder.fit import fit_band, fit_breakdown, fit_score
from referral_finder.llm import ExtractionUnavailable, QuotaExceeded
from referral_finder.models import CallAttempt, Contact, Organization
from referral_finder.monitoring import report_error
from referral_finder.normalize import zip5 as normalize_zip
from referral_finder.roles import DEPARTMENT_TITLE, TIER_LABELS, title_tier
from referral_finder.sources import npi


def _reported(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            report_error(exc)
            raise

    return wrapper


class LeadRow(BaseModel):
    id: int
    fit: int
    name: str
    category: str
    zip5: str | None
    phone: str | None
    best_contact: str | None  # title (or name) of the best contact on file
    best_tier: int | None
    band: str
    band_style: str
    miles: float | None = None  # distance from the ZIP searched
    status: str
    attempts: int
    last_outcome: str | None


def contact_tier(c: Contact) -> int:
    """0 = likely handles referrals ... 3 = unlikely (finance / executive). See roles.py."""
    return title_tier(_role_text(c), load_config("contact_finder")["titles"])


def _signals(org: Organization, contacts: list[Contact]) -> dict:
    tiers = [contact_tier(c) for c in contacts]
    return {
        "best_contact_tier": min(tiers) if tiers else None,
        "has_phone": bool(org.main_phone_normalized),
        "has_email": any(c.email for c in contacts),
    }


def band_for(score: int) -> dict:
    return fit_band(score, load_config("scoring"))


def _role_text(c: Contact) -> str | None:
    """What to show as a contact's role: the title, or the department name for a department line."""
    return c.name if c.title == DEPARTMENT_TITLE else c.title


def _contact_rank(c: Contact) -> tuple:
    """Best contact first: by how likely the title handles referrals, then email, then phone."""
    return (contact_tier(c), not c.email, not c.phone, c.name or "")


class LeadDetail(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    organization: Organization
    contacts: list[Contact]
    history: list[CallAttempt]  # newest first
    summary: calls.CallSummary
    score_parts: list[tuple[str, int]]  # (explanation, points) behind the score
    could_add: list[str]  # what would raise it


def category_labels() -> dict[str, str]:
    return {k: v["label"] for k, v in load_config("scoring")["fit"]["categories"].items()}


def outcome_labels() -> dict[str, str]:
    return load_config("scoring")["calls"]["outcomes"]


def radius_options() -> tuple[list[float], float]:
    search = load_config("service_area")["search"]
    return search["radius_options_miles"], search["default_radius_miles"]


def ui_settings() -> dict:
    return load_config("scoring")["ui"]


def boroughs() -> list[str]:
    return list(load_config("service_area")["boroughs"])


@_reported
def refresh_leads(borough: str) -> int:
    """Fetch NPI organizations for a borough, score them, and save them."""
    saved = db.save_leads(npi.fetch_leads(borough))
    recompute_fits(borough)
    return saved


def recompute_fits(borough: str) -> None:
    """Recalculate every lead's score from the contacts on file."""
    config = load_config("scoring")
    orgs = db.organizations_in(borough)
    contacts = db.contacts_by_org([o.id for o in orgs])
    db.set_fit_scores(
        {o.id: fit_score(o.category, config=config, **_signals(o, contacts.get(o.id, []))) for o in orgs}
    )


@_reported
def list_leads(
    borough: str,
    zip_code: str | None = None,
    categories: list[str] | None = None,
    show_hidden: bool = False,
    limit: int | None = None,
    radius_miles: float = 0,
) -> list[LeadRow]:
    """Leads sorted by fit (nearest first among equal fit), with call attempts and last outcome.

    With a ZIP and a radius, includes leads in every ZIP within that many miles.
    """
    zip5 = normalize_zip(zip_code) if zip_code else None
    if zip_code and not zip5:
        return []
    miles: dict[str, float] = {}
    zip5s = None
    if zip5:
        near = geo.distances_from(zip5, db.org_zips(borough), radius_miles) if radius_miles > 0 else None
        miles = near if near is not None else {zip5: 0.0}
        zip5s = list(miles)
    scoring = load_config("scoring")
    rows = db.search_leads(
        borough,
        zip5s=zip5s,
        categories=categories,
        hidden_statuses=None if show_hidden else scoring["calls"]["hidden_statuses"],
        limit=limit,
    )
    attempts = db.attempts_by_org([org.id for org, _ in rows])
    contacts = db.contacts_by_org([org.id for org, _ in rows])
    miss = scoring["calls"]["miss_outcomes"]
    out = []
    for org, _ in rows:
        best = sorted(contacts.get(org.id, []), key=_contact_rank)[:1]
        band = band_for(org.fit_score)
        summary = calls.summarize([a.outcome for a in attempts.get(org.id, [])], miss)
        out.append(
            LeadRow(
                id=org.id,
                fit=org.fit_score,
                name=org.name,
                category=org.category,
                zip5=org.zip5,
                miles=miles.get(org.zip5) if zip5 else None,
                phone=org.main_phone,
                best_contact=(_role_text(best[0]) or best[0].name) if best else None,
                best_tier=contact_tier(best[0]) if best else None,
                band=band["label"],
                band_style=band["style"],
                status=org.status,
                attempts=summary.attempts,
                last_outcome=summary.last_outcome,
            )
        )
    out.sort(key=lambda r: (-r.fit, r.miles or 0.0, r.name))
    return out


@_reported
def lead_detail(org_id: int) -> LeadDetail:
    history = db.attempts_by_org([org_id]).get(org_id, [])
    miss = load_config("scoring")["calls"]["miss_outcomes"]
    org = db.get_organization(org_id)
    contacts = sorted(db.contacts_for(org_id), key=_contact_rank)
    parts, could_add = _explain_score(org, contacts)
    return LeadDetail(
        organization=org,
        contacts=contacts,
        history=history,
        summary=calls.summarize([a.outcome for a in history], miss),
        score_parts=parts,
        could_add=could_add,
    )


def _explain_score(org: Organization, contacts: list[Contact]) -> tuple[list[tuple[str, int]], list[str]]:
    """Plain-English reasons behind a lead's score, and what would raise it."""
    config = load_config("scoring")
    signals = _signals(org, contacts)
    points = dict(fit_breakdown(org.category, config=config, **signals))
    by_tier = config["fit"]["signals"]["contact_by_tier"]
    tier = signals["best_contact_tier"]
    best = sorted(contacts, key=_contact_rank)[:1]
    category = config["fit"]["categories"][org.category]["label"]
    contact_text = "No contact on file"
    if best:
        who = _role_text(best[0]) or "role not listed"
        contact_text = f"Best contact on file: {who}. {TIER_LABELS[tier]}"
    parts = [
        (f"{category} facility", points["category"]),
        (contact_text, points["contact"]),
        ("Main phone number to call" if signals["has_phone"] else "No phone number", points["phone"]),
        ("Email address on file" if signals["has_email"] else "No email address on file", points["email"]),
    ]
    could_add = []
    gain = by_tier[0] - points["contact"]
    if tier != 0 and gain > 0:
        could_add.append(f"+{gain}: find a social work, discharge, case management or admissions contact")
    if not signals["has_email"]:
        could_add.append(f"+{config['fit']['signals']['has_email']}: find a contact's email address")
    return parts, could_add


@_reported
def log_call(org_id: int, outcome: str, contact_id: int | None = None) -> str:
    """Log a call and update the lead's status. Returns the new status."""
    rules = load_config("scoring")["calls"]
    if outcome not in rules["outcomes"]:
        raise ValueError(f"Unknown outcome: {outcome}")
    status = calls.status_after(outcome, rules["status_after_outcome"])
    db.record_call(org_id, outcome, status, contact_id)
    return status


class FindResult(BaseModel):
    saved: int = 0
    already_known: int = 0
    rejected: int = 0
    error: str | None = None  # set when the search could not run; show it instead of a traceback


@_reported
def find_contacts(org_id: int) -> FindResult:
    """Search the web for named staff at one organization and save the verified ones."""
    org = db.get_organization(org_id)
    try:
        found, rejected = contact_finder.find_contacts(org.name, org.borough)
    except QuotaExceeded as exc:
        report_error(exc)
        return FindResult(error="The Gemini API quota is used up. Wait for it to reset, or use a different key in .env.")
    except ExtractionUnavailable as exc:
        report_error(exc)
        return FindResult(error="Gemini is busy right now (Google's servers are overloaded). Wait a minute and try again.")
    except httpx.HTTPError as exc:
        report_error(exc)
        return FindResult(error="The web search (Nimble) failed. Try again in a moment.")
    saved = db.save_web_contacts(org_id, found)
    recompute_fits(org.borough)
    return FindResult(saved=saved, already_known=len(found) - saved, rejected=rejected)


@_reported
def mark_already_called(org_id: int) -> None:
    db.set_status(org_id, "already_called")
