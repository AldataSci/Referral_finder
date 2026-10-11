"""Database tables (M1 lite): Organization, Contact, CallAttempt."""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, Text
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _tz_column(**kwargs) -> Column:
    return Column(DateTime(timezone=True), **kwargs)


class Organization(SQLModel, table=True):
    __tablename__ = "organizations"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    category: str
    npi: str | None = Field(default=None, unique=True, index=True)
    source: str = "npi"  # npi / manual
    address_line: str | None = None
    zip5: str | None = Field(default=None, index=True)
    borough: str | None = None
    main_phone: str | None = None
    main_phone_normalized: str | None = None
    fit_score: int = 0
    # untried / contacted / active / already_called / not_a_fit / bad_number / unreachable
    status: str = "untried"
    created_at: datetime = Field(default_factory=utcnow, sa_column=_tz_column(nullable=False))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=_tz_column(nullable=False))
    fetched_at: datetime | None = Field(default=None, sa_column=_tz_column())


class Contact(SQLModel, table=True):
    __tablename__ = "contacts"

    id: int | None = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organizations.id", index=True)
    name: str | None = None
    title: str | None = None
    phone: str | None = None
    email: str | None = None
    # decision_maker / gatekeeper / registered_official / clinician / other
    role: str = "other"
    # npi_official / learned_on_call / web / manual
    source: str = "manual"
    source_url: str | None = None
    evidence: str | None = None  # quote from the page; required when source = web
    verified: bool = False


class CallAttempt(SQLModel, table=True):
    """One row per call or email. A hypertable on Tiger Cloud, partitioned by
    timestamp, so the primary key is (id, timestamp)."""

    __tablename__ = "call_attempts"

    id: int | None = Field(
        default=None,
        sa_column=Column(Integer, primary_key=True, autoincrement=True),
    )
    timestamp: datetime = Field(
        default_factory=utcnow,
        sa_column=_tz_column(primary_key=True, nullable=False),
    )
    organization_id: int = Field(foreign_key="organizations.id", index=True)
    contact_id: int | None = Field(default=None, foreign_key="contacts.id")
    # TEXT, not VARCHAR: Tiger warns against VARCHAR on hypertables
    channel: str = Field(default="call", sa_type=Text)  # call / email
    outcome: str = Field(sa_type=Text)
    note: str | None = Field(default=None, sa_type=Text)
    is_demo: bool = False
