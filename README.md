# Referral Finder

A single-user web app for a home care agency's lead generation. It answers one question: **who at nearby
facilities actually handles home-care referrals, and how do I reach them?**

Search by borough, ZIP and radius. The app returns facilities ranked by *referral potential*, shows the best
person (or department line) to ask for, and lets you log every call.

Built for the AI Engineer NYC 2026 hackathon (MLH), October 11.

## What it does

- **Finds leads.** Pulls skilled nursing, rehab and case management organizations in Brooklyn from the federal
  CMS NPI Registry (289 leads), with address, phone and registered contact.
- **Ranks them.** A 0-100 *referral potential* score = facility type + how well the best contact on file matches
  referral work (social work, discharge, case management, admissions) + a phone number + an email. Open any lead
  and expand "Why this score?" to see the points. Finance and executive titles score nothing, because they rarely
  handle referrals.
- **Searches by distance.** Enter a ZIP and a radius (that ZIP only, 1, 2, 3 or 5 miles). Ties in score are broken
  by distance.
- **Finds the right person on the web.** "Find contacts on the web" runs one web search, has an AI read the pages,
  and keeps only people or department lines whose name, phone, email and quote actually appear on the page (checked
  in code, not by the AI). Everything is saved with a source link and is marked *not yet verified by a call*.
- **Logs calls.** One-click outcomes, attempts, voicemail streak, call history in New York time, and an
  "Already called" button that hides a lead.

## Run it

Requires Python 3.11+.

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt -e .
cp .env.example .env        # then fill in the four values (never commit .env)
.venv/Scripts/python.exe -m referral_finder.db            # creates the tables on Tiger Cloud (once)
.venv/Scripts/python.exe scripts/preview_leads.py         # loads the Brooklyn leads from NPI (once)
.venv/Scripts/python.exe -m streamlit run app.py
```

On macOS/Linux use `.venv/bin/python` instead of `.venv/Scripts/python.exe`. Restart Streamlit after changing
code under `src/`.

`.env` needs: `DATABASE_URL` (Tiger Cloud Postgres), `GEMINI_API_KEY`, `NIMBLE_API_KEY`, `SENTRY_DSN`.
`scripts/smoke_test.py` checks that every key works.

Run the tests with `.venv/Scripts/python.exe -m pytest`.

## Sponsor tools and why

| Tool | What it does here | Why |
|---|---|---|
| **Tiger Data (Tiger Cloud)** | The database. `call_attempts` is a time-series **hypertable** keyed by `(id, timestamp)`. | Every call is a timestamped event. It is the foundation for learning when each facility picks up. |
| **Nimble** | One web search per lead, returning the text of the pages. | The registry gives an owner or finance contact. Live web context is how we reach admissions and social work. |
| **Gemini API** | Reads those pages and returns structured contacts (person or department, title, phone, email, exact quote). If one model's free quota or capacity runs out, the app tries the next. | A real extraction job, with a code-level guardrail against made-up names. |
| **Sentry** | Initialized once with personal data off. The contact finder is traced in separate spans for the Nimble search, the Gemini call and the evidence check, and service errors are reported explicitly. | The app depends on four outside services, so we need to see which one failed. |

Not used: Snowflake (a deliberate choice, to stay on one database platform).

## Known limits

- Brooklyn only today. Other boroughs are a config change plus a data refresh.
- Registry data is imperfect: some listings are closed facilities, non-facilities or duplicates.
- Many small nursing homes publish no staff online, so "Find contacts" works best on hospitals and larger systems.
  It says "No new named contacts found" instead of guessing, and it never builds an email address.
- Not built yet: best-time-to-call (continuous aggregate on the hypertable), export, dedupe.
- Needs internet (Tiger Cloud). There is no offline fallback.

## Project layout

```
app.py                  Streamlit page
src/referral_finder/    all logic, no Streamlit imports (db, services, scoring, contact finder, ...)
config/                 weights, title rules, service area, finder settings (YAML)
scripts/                smoke_test.py, preview_leads.py
tests/                  fit scoring and the contact finder's evidence check
```

Full specification: `PROJECT_PLAN.md`.
