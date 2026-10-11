"""Fetch Brooklyn leads from NPI, save them to Tiger Cloud, print the top 20.

Run from the project root:  python scripts/preview_leads.py
"""
import logging
import sys

from referral_finder.monitoring import init_sentry
from referral_finder.services import category_labels, list_leads, refresh_leads

BOROUGH = "Brooklyn"
LIMIT = 20

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
init_sentry()

saved = refresh_leads(BOROUGH)
labels = category_labels()
print(f"\nSaved {saved} {BOROUGH} leads. Top {LIMIT} by fit:\n")
for i, lead in enumerate(list_leads(BOROUGH, limit=LIMIT), 1):
    print(
        f"{i:>2}. [{lead.fit:>3} {lead.band}] {lead.name} | {labels[lead.category]} | "
        f"{lead.zip5} | {lead.phone or '-'} | {lead.best_contact or '-'}"
    )
