"""Nimble Search: one call that returns web pages about an organization."""
import logging
import time

import httpx
import sentry_sdk
from pydantic import BaseModel

from referral_finder import cache
from referral_finder.config import get_secret, load_config

logger = logging.getLogger(__name__)


class Page(BaseModel):
    url: str
    title: str = ""
    text: str  # title + description + page content: everything the evidence check may match


def search_pages(org_name: str, borough: str) -> list[Page]:
    """ONE Nimble Search call (cached for cache_ttl_days). Returns pages with text."""
    settings = load_config("contact_finder")["nimble"]
    body = {
        "query": settings["query_template"].format(name=org_name, borough=borough),
        "max_results": settings["max_results"],
        "search_depth": settings["search_depth"],
        "full_content": settings["full_content"],
        "exclude_domains": settings["exclude_domains"],
    }
    data = cache.get("nimble", body, settings["cache_ttl_days"])
    if data is None:
        with sentry_sdk.start_span(op="http.client", name="Nimble search"):
            data = _post(settings, body)
        cache.put("nimble", body, data)

    pages = []
    for r in data.get("results") or []:
        text = "\n".join(p for p in (r.get("title"), r.get("description"), r.get("content")) if p)
        if r.get("url") and text:
            pages.append(Page(url=r["url"], title=r.get("title") or "", text=text))
    logger.info("Nimble returned %d pages", len(pages))
    return pages


def _post(settings: dict, body: dict) -> dict:
    headers = {"Authorization": f"Bearer {get_secret('NIMBLE_API_KEY')}"}
    for attempt in range(settings["retries"]):
        try:
            r = httpx.post(settings["url"], headers=headers, json=body, timeout=settings["timeout_seconds"])
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as exc:
            logger.warning("Nimble request failed (attempt %d): %s", attempt + 1, type(exc).__name__)
            if attempt == settings["retries"] - 1:
                raise
            time.sleep(2**attempt)
