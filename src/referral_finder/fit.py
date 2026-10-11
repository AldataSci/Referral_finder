"""Referral potential ("fit") score: how worth a call is this lead? Pure functions.

Known before any calls. Points come from what kind of facility it is, how well the
best contact on file matches the job (see roles.py), and whether we can actually
phone or email someone. Weights live in config/scoring.yaml.
"""


def fit_breakdown(
    category: str,
    *,
    best_contact_tier: int | None,
    has_phone: bool,
    has_email: bool,
    config: dict,
) -> list[tuple[str, int]]:
    """(reason, points) pairs. `best_contact_tier` is None when no contact is on file."""
    fit = config["fit"]
    signals = fit["signals"]
    contact = 0 if best_contact_tier is None else signals["contact_by_tier"][best_contact_tier]
    return [
        ("category", fit["categories"][category]["weight"]),
        ("contact", contact),
        ("phone", signals["has_phone"] if has_phone else 0),
        ("email", signals["has_email"] if has_email else 0),
    ]


def fit_score(category: str, *, config: dict, **signals) -> int:
    total = sum(points for _, points in fit_breakdown(category, config=config, **signals))
    return min(total, config["fit"]["max_score"])


def fit_band(score: int, config: dict) -> dict:
    """The band (label + style) a score falls into."""
    return next(b for b in config["fit"]["bands"] if score >= b["min"])
