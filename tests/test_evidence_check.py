from referral_finder.contact_finder import verify_contacts
from referral_finder.llm import Candidate
from referral_finder.web import Page

TITLES = {
    "referral": ["social work", "discharge"],
    "unlikely": ["financ", "billing", "ceo"],
    "routing": ["administrat"],
}
URL = "https://example-snf.org/staff"
PAGE = Page(
    url=URL,
    text=(
        "Our Team\nMaria Lopez, Director of Social Work\n"
        "Contact: mlopez@example-snf.org, direct line (718) 555-0142\nJohn Smith - Administrator"
    ),
)


def candidate(**overrides) -> Candidate:
    base = dict(
        name="Maria Lopez",
        title="Director of Social Work",
        email="mlopez@example-snf.org",
        phone="718-555-0142",
        source_url=URL,
        quote="Maria Lopez, Director of Social Work",
    )
    return Candidate(**{**base, **overrides})


def check(c: Candidate):
    kept, rejected = verify_contacts([c], [PAGE], TITLES)
    return kept, rejected


def test_real_contact_is_kept_and_marked_decision_maker():
    kept, rejected = check(candidate())
    assert len(kept) == 1 and not rejected
    assert kept[0].role == "decision_maker"
    assert kept[0].evidence == "Maria Lopez, Director of Social Work"


def test_quote_not_in_page_is_rejected():
    kept, rejected = check(candidate(quote="Maria Lopez leads our discharge planning team"))
    assert not kept and "quote" in rejected[0][1]


def test_made_up_name_is_rejected():
    kept, rejected = check(candidate(name="Priya Raman", quote="John Smith - Administrator"))
    assert not kept and "name" in rejected[0][1]


def test_email_not_in_page_is_rejected():
    kept, rejected = check(candidate(email="maria.lopez@gmail.com"))
    assert not kept and "email" in rejected[0][1]


def test_phone_is_kept_when_on_page_and_rejected_when_not():
    kept, _ = check(candidate())
    assert kept[0].phone == "718-555-0142"
    kept, rejected = check(candidate(phone="212-555-9999"))
    assert not kept and "phone" in rejected[0][1]


def test_finance_or_executive_title_is_rejected_for_web_contacts():
    page = Page(url=URL, text="John Smith, VP of Finance")
    c = candidate(name="John Smith", title="VP of Finance", email=None, phone=None, quote="John Smith, VP of Finance")
    kept, rejected = verify_contacts([c], [page], TITLES)
    assert not kept and "not a referral role" in rejected[0][1]


def test_department_line_is_kept_and_ranked_as_a_referral_contact():
    page = Page(url=URL, text="Admissions: 718-555-0199 | Billing: 718-555-0100")
    c = candidate(name="Admissions", kind="department", title=None, email=None, phone="718-555-0199", quote="Admissions: 718-555-0199")
    kept, _ = verify_contacts([c], [page], TITLES | {"referral": ["admission"]})
    assert len(kept) == 1 and kept[0].role == "decision_maker" and kept[0].title == "Department phone line"


def test_people_in_other_roles_are_not_saved():
    page = Page(url=URL, text="Rabbi Ben Lesser, Chaplain, 718-555-0111")
    c = candidate(name="Rabbi Ben Lesser", title="Chaplain", email=None, phone="718-555-0111", quote="Rabbi Ben Lesser, Chaplain, 718-555-0111")
    kept, rejected = verify_contacts([c], [page], TITLES)
    assert not kept and "not a referral role" in rejected[0][1]


def test_unknown_source_page_is_rejected():
    kept, rejected = check(candidate(source_url="https://other-site.com/team"))
    assert not kept and "source page" in rejected[0][1]


def test_missing_email_is_allowed_and_unverified_title_is_dropped():
    kept, _ = check(candidate(email=None, title="Chief Medical Officer"))
    assert len(kept) == 1
    assert kept[0].email is None and kept[0].title is None
    assert kept[0].role == "decision_maker"  # the quoted line still shows a social work role


def test_whitespace_and_case_differences_still_match():
    kept, _ = check(candidate(quote="maria lopez,   DIRECTOR of social work"))
    assert len(kept) == 1
