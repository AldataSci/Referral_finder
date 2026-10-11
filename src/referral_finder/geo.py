"""ZIP-to-ZIP distances using the offline `zipcodes` dataset (ZIP centroids)."""
from math import asin, cos, radians, sin, sqrt

import zipcodes

EARTH_RADIUS_MILES = 3958.8


def _coords(zip5: str) -> tuple[float, float] | None:
    match = zipcodes.matching(zip5)
    if not match or not match[0].get("lat"):
        return None
    return float(match[0]["lat"]), float(match[0]["long"])


def distances_from(origin: str, candidates: list[str], radius_miles: float) -> dict[str, float] | None:
    """Miles from `origin` to each candidate ZIP within the radius.

    Returns None if the origin ZIP is unknown, so the caller can fall back to an exact match.
    """
    start = _coords(origin)
    if start is None:
        return None
    lat1, lon1 = map(radians, start)
    result: dict[str, float] = {}
    for z in candidates:
        end = _coords(z)
        if end is None:
            continue
        lat2, lon2 = map(radians, end)
        a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
        miles = 2 * EARTH_RADIUS_MILES * asin(sqrt(a))
        if miles <= radius_miles or z == origin:
            result[z] = round(miles, 1)
    return result
