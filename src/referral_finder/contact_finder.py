"""Web contact finder: Nimble pages -> Gemini candidates -> evidence check in code.

The evidence check is plain Python, not AI. A contact survives only if what Gemini
claims really appears in the page text.
"""
import logging
import re

import sentry_sdk
from pydantic import BaseModel

from referral_finder.config import load_config
from referral_finder.llm import Candidate, extract_candidates
from referral_finder.roles import DEPARTMENT_TITLE, REFERRAL, title_tier
from referral_finder.web import Page, search_pages

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class FoundContact(BaseModel):
    name: str
    title: str | None
    email: str | None
    phone: str | None
    role: str  # decision_maker / other
    source_url: str
    evidence: str  # the verified quote


def _norm(text: str) -> str:
    """Lowercase and collapse whitespace, quotes and dashes so formatting can't cause misses."""
    text = (
        text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
        .replace("–", "-").replace("—", "-").replace("\xa0", " ")
    )
    return re.sub(r"\s+", " ", text).strip().lower()


def _phone_on_page(phone: str, page_digits: str) -> bool:
    """A phone is real only if its 10 digits (country code dropped) appear on the page."""
    d = re.sub(r"\D", "", phone)
    d = d[1:] if len(d) == 11 and d.startswith("1") else d
    return len(d) == 10 and d in page_digits


def verify_contacts(
    candidates: list[Candidate], pages: list[Page], titles_config: dict
) -> tuple[list[FoundContact], list[tuple[Candidate, str]]]:
    """Keep a candidate only if its quote, name and email appear in its source page.

    A title that is not on the page is dropped (the contact is kept, as role 'other').
    Only referral roles are kept (social work, discharge, case management, admissions, intake);
    anyone else found on a page (chaplains, patient reps, finance, executives) is rejected.
    Returns (kept, rejected-with-reason).
    """
    by_url = {p.url.rstrip("/"): _norm(p.text) for p in pages}
    digits = {p.url.rstrip("/"): re.sub(r"\D", "", p.text) for p in pages}
    kept: list[FoundContact] = []
    rejected: list[tuple[Candidate, str]] = []
    for c in candidates:
        page = by_url.get(c.source_url.rstrip("/"))
        if page is None:
            rejected.append((c, "source page was not in the search results"))
        elif not c.name.strip() or _norm(c.name) not in page:
            rejected.append((c, "name not found on the page"))
        elif not c.quote.strip() or _norm(c.quote) not in page:
            rejected.append((c, "quote not found on the page"))
        elif c.email and (not EMAIL_RE.match(c.email) or c.email.strip().lower() not in page):
            rejected.append((c, "email not found on the page"))
        elif c.phone and not _phone_on_page(c.phone, digits[c.source_url.rstrip("/")]):
            rejected.append((c, "phone not found on the page"))
        else:
            title = c.title if c.title and _norm(c.title) in page else None
            is_department = c.kind == "department"
            # the verified title decides; if it is missing, the quoted line itself does
            tier = title_tier(c.name if is_department else (title or c.quote), titles_config)
            if tier != REFERRAL:
                rejected.append((c, "not a referral role (social work, discharge, case management, admissions)"))
                continue
            kept.append(
                FoundContact(
                    name=c.name.strip(),
                    title=DEPARTMENT_TITLE if is_department else title,
                    email=c.email.strip().lower() if c.email else None,
                    phone=c.phone.strip() if c.phone else None,
                    role="decision_maker" if tier == REFERRAL else "other",
                    source_url=c.source_url,
                    evidence=c.quote.strip(),
                )
            )
    return kept, rejected


def find_contacts(org_name: str, borough: str) -> tuple[list[FoundContact], int]:
    """Run the finder for one organization. Returns (verified contacts, rejected count)."""
    settings = load_config("contact_finder")
    with sentry_sdk.start_transaction(op="task", name="find_contacts"):
        pages = search_pages(org_name, borough)
        if not pages:
            return [], 0
        candidates = extract_candidates(org_name, pages)
        with sentry_sdk.start_span(op="function", name="Evidence check"):
            kept, rejected = verify_contacts(candidates, pages, settings["titles"])
    for candidate, reason in rejected:
        logger.info("Rejected %r: %s", candidate.name, reason)
    return kept, len(rejected)
