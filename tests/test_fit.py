from referral_finder.config import load_config
from referral_finder.fit import fit_band, fit_breakdown, fit_score

CONFIG = {
    "fit": {
        "categories": {"snf": {"weight": 50}, "cm": {"weight": 35}},
        "signals": {"contact_by_tier": [30, 18, 6, 0], "has_phone": 10, "has_email": 10},
        "max_score": 100,
        "bands": [
            {"min": 85, "label": "Excellent", "style": "high"},
            {"min": 55, "label": "Fair", "style": "fair"},
            {"min": 0, "label": "Low", "style": "low"},
        ],
    }
}


def score(category, tier=None, phone=False, email=False, config=CONFIG):
    return fit_score(category, best_contact_tier=tier, has_phone=phone, has_email=email, config=config)


def test_category_weight_only():
    assert score("snf") == 50
    assert score("cm") == 35


def test_a_referral_contact_beats_a_finance_contact():
    assert score("snf", tier=0, phone=True) == 90
    assert score("snf", tier=3, phone=True) == 60  # finance / executive adds nothing


def test_contact_points_follow_the_tier():
    assert [score("snf", tier=t) for t in (0, 1, 2, 3)] == [80, 68, 56, 50]


def test_everything_is_capped_at_the_maximum():
    assert score("snf", tier=0, phone=True, email=True) == 100
    config = {"fit": {**CONFIG["fit"], "max_score": 70}}
    assert score("snf", tier=0, phone=True, email=True, config=config) == 70


def test_breakdown_lists_each_reason():
    parts = dict(fit_breakdown("snf", best_contact_tier=1, has_phone=True, has_email=False, config=CONFIG))
    assert parts == {"category": 50, "contact": 18, "phone": 10, "email": 0}


def test_bands_pick_the_highest_matching_label():
    assert fit_band(90, CONFIG)["label"] == "Excellent"
    assert fit_band(60, CONFIG)["label"] == "Fair"
    assert fit_band(10, CONFIG)["label"] == "Low"


def test_real_config_loads_and_caps():
    config = load_config("scoring")
    assert score("skilled_nursing", tier=0, phone=True, email=True, config=config) == 100
