"""All database code. Tiger Cloud Postgres only, chosen by DATABASE_URL."""
import logging
import os
from functools import lru_cache

from dotenv import find_dotenv, load_dotenv
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine, select

from referral_finder.contact_finder import FoundContact
from referral_finder.models import CallAttempt, Contact, Organization, utcnow
from referral_finder.sources.npi import Lead

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    load_dotenv(find_dotenv(usecwd=True))
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set in .env")
    # SQLAlchemy needs the psycopg (v3) driver named in the URL scheme.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return create_engine(url, pool_pre_ping=True)


def _make_call_attempts_hypertable(engine: Engine) -> None:
    """Tiger-only SQL, kept in this one function."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "SELECT create_hypertable('call_attempts', by_range('timestamp'), "
                "if_not_exists => true)"
            )
        )


def init_db() -> None:
    """Create the tables if missing and make call_attempts a hypertable."""
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _make_call_attempts_hypertable(engine)
    logger.info("Database ready.")


def save_leads(leads: list[Lead]) -> int:
    """Upsert organizations by NPI, plus their registered official as a contact.

    Keeps each existing organization's status and fit score. Returns the number saved.
    """
    now = utcnow()
    with Session(get_engine()) as session:
        existing = {
            o.npi: o
            for o in session.exec(select(Organization).where(Organization.npi.in_([lead.npi for lead in leads])))
        }
        officials = {
            c.organization_id: c
            for c in session.exec(select(Contact).where(Contact.source == "npi_official"))
        }
        for lead in leads:
            org = existing.get(lead.npi) or Organization(npi=lead.npi, name=lead.name, category=lead.category)
            org.name, org.category, org.source = lead.name, lead.category, "npi"
            org.address_line, org.zip5, org.borough = lead.address_line, lead.zip5, lead.borough
            org.main_phone, org.main_phone_normalized = lead.main_phone, lead.main_phone_normalized
            org.updated_at, org.fetched_at = now, now
            session.add(org)
            if lead.official_name:
                session.flush()  # assigns org.id for new organizations
                contact = officials.get(org.id) or Contact(
                    organization_id=org.id, role="registered_official", source="npi_official"
                )
                contact.name, contact.title, contact.phone = (
                    lead.official_name,
                    lead.official_title,
                    lead.official_phone,
                )
                session.add(contact)
        session.commit()
    return len(leads)


def organizations_in(borough: str) -> list[Organization]:
    with Session(get_engine()) as session:
        return list(session.exec(select(Organization).where(Organization.borough == borough)))


def contacts_by_org(org_ids: list[int]) -> dict[int, list[Contact]]:
    result: dict[int, list[Contact]] = {}
    with Session(get_engine()) as session:
        for c in session.exec(select(Contact).where(Contact.organization_id.in_(org_ids))):
            result.setdefault(c.organization_id, []).append(c)
    return result


def set_fit_scores(scores: dict[int, int]) -> None:
    """Write fit scores (organization id -> score) in one transaction."""
    with Session(get_engine()) as session:
        for org in session.exec(select(Organization).where(Organization.id.in_(list(scores)))):
            if org.fit_score != scores[org.id]:
                org.fit_score, org.updated_at = scores[org.id], utcnow()
                session.add(org)
        session.commit()


def search_leads(
    borough: str,
    zip5s: list[str] | None = None,
    categories: list[str] | None = None,
    hidden_statuses: list[str] | None = None,
    limit: int | None = None,
) -> list[tuple[Organization, Contact | None]]:
    """Organizations by descending fit, each with its registered official.

    Organizations whose status is in `hidden_statuses` are left out.
    """
    stmt = (
        select(Organization, Contact)
        .join(
            Contact,
            (Contact.organization_id == Organization.id) & (Contact.source == "npi_official"),
            isouter=True,
        )
        .where(Organization.borough == borough)
        .order_by(Organization.fit_score.desc(), Organization.name)
    )
    if zip5s is not None:
        stmt = stmt.where(Organization.zip5.in_(zip5s))
    if categories is not None:
        stmt = stmt.where(Organization.category.in_(categories))
    if hidden_statuses:
        stmt = stmt.where(Organization.status.not_in(hidden_statuses))
    if limit:
        stmt = stmt.limit(limit)
    with Session(get_engine()) as session:
        return list(session.exec(stmt).all())


def org_zips(borough: str) -> list[str]:
    """Distinct ZIPs that have leads in a borough."""
    stmt = select(Organization.zip5).where(Organization.borough == borough, Organization.zip5.is_not(None)).distinct()
    with Session(get_engine()) as session:
        return list(session.exec(stmt))


def get_organization(org_id: int) -> Organization:
    with Session(get_engine()) as session:
        return session.get(Organization, org_id)


def contacts_for(org_id: int) -> list[Contact]:
    with Session(get_engine()) as session:
        return list(session.exec(select(Contact).where(Contact.organization_id == org_id)))


def attempts_by_org(org_ids: list[int]) -> dict[int, list[CallAttempt]]:
    """Call attempts per organization, newest first."""
    result: dict[int, list[CallAttempt]] = {}
    stmt = (
        select(CallAttempt)
        .where(CallAttempt.organization_id.in_(org_ids))
        .order_by(CallAttempt.timestamp.desc())
    )
    with Session(get_engine()) as session:
        for attempt in session.exec(stmt):
            result.setdefault(attempt.organization_id, []).append(attempt)
    return result


def save_web_contacts(org_id: int, found: list[FoundContact]) -> int:
    """Save verified web contacts, skipping names already on file.

    Returns the number of new contacts saved.
    """
    with Session(get_engine()) as session:
        known = {
            (c.name or "").lower()
            for c in session.exec(select(Contact).where(Contact.organization_id == org_id))
        }
        new = [f for f in found if f.name.lower() not in known]
        for f in new:
            session.add(
                Contact(
                    organization_id=org_id,
                    name=f.name,
                    title=f.title,
                    email=f.email,
                    phone=f.phone,
                    role=f.role,
                    source="web",
                    source_url=f.source_url,
                    evidence=f.evidence,
                    verified=False,
                )
            )
        session.commit()
    return len(new)


def record_call(org_id: int, outcome: str, new_status: str, contact_id: int | None = None) -> None:
    """Log one call attempt and update the organization's status together."""
    with Session(get_engine()) as session:
        session.add(CallAttempt(organization_id=org_id, contact_id=contact_id, outcome=outcome))
        _apply_status(session, org_id, new_status)
        session.commit()


def set_status(org_id: int, status: str) -> None:
    with Session(get_engine()) as session:
        _apply_status(session, org_id, status)
        session.commit()


def _apply_status(session: Session, org_id: int, status: str) -> None:
    org = session.get(Organization, org_id)
    org.status, org.updated_at = status, utcnow()
    session.add(org)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    with get_engine().connect() as conn:
        rows = conn.execute(
            text(
                "SELECT hypertable_name FROM timescaledb_information.hypertables"
            )
        ).all()
    print("Tables created. Hypertables:", [r[0] for r in rows])
