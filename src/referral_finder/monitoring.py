"""Sentry setup. Personal data is never sent (send_default_pii is off)."""
import logging
import os

import sentry_sdk
from dotenv import find_dotenv, load_dotenv

logger = logging.getLogger(__name__)

_initialized = False


def init_sentry() -> bool:
    """Initialize Sentry once per process. Returns True if Sentry is active."""
    global _initialized
    if _initialized:
        return True
    load_dotenv(find_dotenv(usecwd=True))
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        logger.warning("SENTRY_DSN is not set; Sentry is disabled.")
        return False
    sentry_sdk.init(
        dsn=dsn,
        send_default_pii=False,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0")),
    )
    _initialized = True
    return True


def report_error(exc: BaseException) -> None:
    """Send an error to Sentry explicitly (Streamlit can swallow errors)."""
    sentry_sdk.capture_exception(exc)
