"""Smoke test: one tiny call to each service. Prints PASS/FAIL per service.

Run from the project root:  python scripts/smoke_test.py
Never prints keys or the database URL (error text is scrubbed of secret values).
"""
import os
import sys
import time
import uuid

import requests
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True))

SECRET_VARS = ["NIMBLE_API_KEY", "GEMINI_API_KEY", "SENTRY_DSN", "DATABASE_URL"]
TIMEOUT = 30


def redact(text: str) -> str:
    """Remove any secret value (and the password inside the DB URL) from text."""
    text = str(text)
    secrets = [os.getenv(v) for v in SECRET_VARS]
    url = os.getenv("DATABASE_URL")
    if url:
        try:
            from urllib.parse import urlparse

            p = urlparse(url)
            secrets += [p.password, p.hostname, p.username]
        except Exception:
            pass
    for s in secrets:
        if s and len(s) > 3:
            text = text.replace(s, "***")
    return text


def need(var: str) -> str:
    val = os.getenv(var)
    if not val:
        raise RuntimeError(f"{var} is not set in .env")
    return val


# ---- checks: each returns a short detail string, or raises on failure ----

def check_npi() -> str:
    r = requests.get(
        "https://npiregistry.cms.hhs.gov/api/",
        params={
            "version": "2.1",
            "enumeration_type": "NPI-2",
            "taxonomy_description": "Skilled Nursing Facility",
            "postal_code": "112*",
            "state": "NY",
            "address_purpose": "LOCATION",
            "limit": 1,
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    results = data.get("results") or []
    if not results:
        raise RuntimeError(f"no results returned (keys: {list(data)})")
    name = results[0]["basic"].get("organization_name", "?")
    return f"1 facility returned: {name}"


def check_tiger() -> str:
    import psycopg

    table = f"smoke_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(need("DATABASE_URL"), connect_timeout=TIMEOUT, autocommit=True) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        if cur.fetchone() != (1,):
            raise RuntimeError("SELECT 1 returned something unexpected")
        try:
            cur.execute(
                f"CREATE TABLE {table} (ts timestamptz NOT NULL, val int)"
            )
            cur.execute(f"SELECT create_hypertable('{table}', by_range('ts'))")
            cur.execute(
                "SELECT count(*) FROM timescaledb_information.hypertables "
                "WHERE hypertable_name = %s",
                (table,),
            )
            if cur.fetchone()[0] != 1:
                raise RuntimeError("table was not registered as a hypertable")
        finally:
            cur.execute(f"DROP TABLE IF EXISTS {table}")
    return "SELECT 1 ok; hypertable created and dropped"


def check_gemini() -> str:
    from google import genai

    client = genai.Client(api_key=need("GEMINI_API_KEY"))
    # Override with GEMINI_MODEL in .env if your key doesn't have the first one.
    candidates = [os.getenv("GEMINI_MODEL")] if os.getenv("GEMINI_MODEL") else [
        "gemini-3.8-flash",  # Google's 404 message recommends this one
        "gemini-3.5-flash",
    ]
    last_err = None
    for model in candidates:
        try:
            resp = client.models.generate_content(
                model=model, contents="Reply with one short sentence saying hello."
            )
            text = (resp.text or "").strip()
            if not text:
                raise RuntimeError("empty response")
            return f"model {model} replied ({len(text)} chars)"
        except Exception as e:  # try the next model name
            last_err = e
    raise RuntimeError(f"all models failed; last error: {last_err}")


def check_nimble() -> str:
    r = requests.post(
        "https://sdk.nimbleway.com/v2/search",
        headers={"Authorization": f"Bearer {need('NIMBLE_API_KEY')}"},
        json={
            "query": "skilled nursing facility Brooklyn director of social work",
            "max_results": 3,
            "search_depth": "lite",
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    n = len(data.get("results") or [])
    if n == 0:
        raise RuntimeError(f"no results returned (keys: {list(data)})")
    return f"{n} results returned"


def check_sentry() -> str:
    import sentry_sdk

    sentry_sdk.init(dsn=need("SENTRY_DSN"), send_default_pii=False)
    try:
        raise RuntimeError("Referral Finder smoke test: intentional test error")
    except RuntimeError as e:
        event_id = sentry_sdk.capture_exception(e)
    sentry_sdk.flush(timeout=10)
    if not event_id:
        raise RuntimeError("Sentry did not accept the event (check the DSN)")
    return "test error sent; confirm it appears in your Sentry project"


CHECKS = [
    ("NPI Registry", check_npi),
    ("Tiger Cloud", check_tiger),
    ("Gemini", check_gemini),
    ("Nimble", check_nimble),
    ("Sentry", check_sentry),
]


def main() -> int:
    failed = 0
    for name, fn in CHECKS:
        start = time.time()
        try:
            detail = fn()
            print(f"PASS  {name:<13} {detail} ({time.time() - start:.1f}s)")
        except Exception as e:
            failed += 1
            print(f"FAIL  {name:<13} {type(e).__name__}: {redact(e)}")
    print(f"\n{len(CHECKS) - failed}/{len(CHECKS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
