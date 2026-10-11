# Referral Finder

Read PROJECT_PLAN.md before any work. It is the source of truth.

**Hackathon mode (October 11): Section 0 of PROJECT_PLAN.md overrides everything below.** Build the "lite" version in Section 0.4b. Tiger Cloud only (no SQLite support today). Write tests only for fit scoring and the contact finder's evidence check. When the hackathon is over, the owner will delete this paragraph.

- The ideal lead: a decision maker who handles referrals to long-term home care. Keep that in mind in every design choice.
- Work on one milestone at a time (Section 14). Propose a plan first; do not start the next milestone unless asked.
- Never ask the owner to paste API keys into the chat; they go in .env.
- Business logic goes in src/referral_finder/ with no Streamlit imports.
- No hard-coded ZIPs, weights, thresholds, or model names; use config/.
- All database code lives in db.py and uses SQLModel. After the hackathon it must also work on SQLite via DATABASE_URL. Tiger-only SQL (hypertables, continuous aggregates) lives in one isolated setup function.
- Read Streamlit's, Tiger Data's, Nimble's, Sentry's, and google-genai's current docs before writing code that uses them.
- Store timestamps in UTC; show and group times in America/New_York.
- Initialize Sentry once (monitoring.py), with send_default_pii off.
