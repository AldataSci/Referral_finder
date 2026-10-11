"""Rate how likely a job title is to handle home-care referrals. Pure functions.

Tiers (lower is better):
  0 referral : social work, discharge, case management, admissions, intake ...
  1 routing  : administrator / director / manager; can tell you who handles referrals
  2 unknown  : any other title, or no title
  3 unlikely : finance, billing, owner, CEO/president and similar
"""
import re

REFERRAL, ROUTING, UNKNOWN, UNLIKELY = 0, 1, 2, 3

# Title given to a department line (e.g. "Admissions" + its phone); the department name is the rank signal.
DEPARTMENT_TITLE = "Department phone line"

TIER_LABELS = {
    REFERRAL: "Likely handles referrals",
    ROUTING: "Can point you to the right person",
    UNKNOWN: "Role unclear",
    UNLIKELY: "Unlikely to handle referrals (finance / executive)",
}


def title_tier(title: str | None, titles_config: dict) -> int:
    """Classify a title using the `titles` block of config/contact_finder.yaml (regex lists)."""
    t = (title or "").lower().strip()
    if not t:
        return UNKNOWN
    for tier, key in ((REFERRAL, "referral"), (UNLIKELY, "unlikely"), (ROUTING, "routing")):
        if any(re.search(pattern, t) for pattern in titles_config[key]):
            return tier
    return UNKNOWN
