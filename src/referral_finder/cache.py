"""Simple JSON disk cache with a time-to-live."""
import hashlib
import json
import time
from pathlib import Path

from referral_finder.config import ROOT

CACHE_DIR = ROOT / "data" / "cache"


def _path(namespace: str, key: dict) -> Path:
    digest = hashlib.sha1(json.dumps(key, sort_keys=True).encode()).hexdigest()[:16]
    return CACHE_DIR / f"{namespace}_{digest}.json"


def get(namespace: str, key: dict, ttl_days: float):
    path = _path(namespace, key)
    if path.exists() and time.time() - path.stat().st_mtime < ttl_days * 86400:
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def put(namespace: str, key: dict, value) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _path(namespace, key).write_text(json.dumps(value), encoding="utf-8")
