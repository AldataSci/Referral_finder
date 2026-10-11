"""Call logging rules (lite): status after a call, and a per-lead call summary.

Pure functions; the database work lives in db.py.
"""
from pydantic import BaseModel


class CallSummary(BaseModel):
    attempts: int = 0
    last_outcome: str | None = None
    voicemail_streak: int = 0


def status_after(outcome: str, status_rules: dict[str, str]) -> str:
    """New organization status after logging a call with this outcome."""
    return status_rules.get(outcome, "contacted")


def summarize(outcomes_newest_first: list[str], miss_outcomes: list[str]) -> CallSummary:
    """Attempts, last outcome, and the current run of voicemail/no-answer misses."""
    streak = 0
    for outcome in outcomes_newest_first:
        if outcome not in miss_outcomes:
            break
        streak += 1
    return CallSummary(
        attempts=len(outcomes_newest_first),
        last_outcome=outcomes_newest_first[0] if outcomes_newest_first else None,
        voicemail_streak=streak,
    )
