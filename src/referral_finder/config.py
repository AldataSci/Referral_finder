"""Loads the YAML files in config/ and secrets from .env."""
import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import find_dotenv, load_dotenv

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"


@lru_cache(maxsize=None)
def load_config(name: str) -> dict:
    """Load config/<name>.yaml (e.g. 'scoring', 'service_area')."""
    with open(CONFIG_DIR / f"{name}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_secret(name: str) -> str:
    """Read a key from the environment / .env. Never logged or printed."""
    load_dotenv(find_dotenv(usecwd=True))
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set in .env")
    return value
