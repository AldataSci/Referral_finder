import math
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from referral_finder import services
from referral_finder.monitoring import init_sentry, report_error
from referral_finder.roles import TIER_LABELS

NY = ZoneInfo("America/New_York")
ROLE_LABELS = {
    "registered_official": "NPI registered contact",
    "decision_maker": "Likely decision maker",
    "other": "Staff member",
}
STATUS_LABELS = {
    "untried": "⚪ New",
    "contacted": "🟡 Contacted",
    "active": "🟢 Active",
    "already_called": "🟣 Already called",
    "not_a_fit": "⚫ Not a fit",
    "bad_number": "🔴 Bad number",
    "unreachable": "🔴 Unreachable",
}
CATEGORY_COLORS = {"skilled_nursing": "blue", "rehab": "green", "case_management": "orange"}

CSS = """
<style>
.block-container { padding-top: 1.2rem; max-width: 1450px; }
header[data-testid="stHeader"] { background: transparent; }

.hero {
    background: linear-gradient(120deg, #4F46E5 0%, #7C3AED 55%, #0EA5E9 100%);
    border-radius: 16px; padding: 18px 26px; color: white; margin-bottom: 14px;
    box-shadow: 0 8px 22px rgba(79, 70, 229, 0.22);
    display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap;
}
.hero h1 { color: white; margin: 0; font-size: 1.7rem; padding: 0; line-height: 1.2; }
.hero p { margin: 2px 0 0; font-size: 0.95rem; opacity: 0.92; }
.hero .tag { background: rgba(255,255,255,.18); border-radius: 999px; padding: 6px 14px; font-size: .85rem; font-weight: 600; }

/* lead cards */
[class*="st-key-card_"] { transition: box-shadow .15s, transform .15s; }
[class*="st-key-card_"]:hover { box-shadow: 0 6px 18px rgba(79,70,229,.15); transform: translateY(-1px); }
.fit {
    width: 46px; height: 46px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 1.15rem; color: white;
}
.fit-high { background: linear-gradient(135deg, #059669, #047857); }
.fit-good { background: linear-gradient(135deg, #10B981, #059669); }
.fit-fair { background: linear-gradient(135deg, #F59E0B, #D97706); }
.fit-low { background: linear-gradient(135deg, #94A3B8, #64748B); }
.lead-name { font-weight: 700; font-size: 1rem; line-height: 1.25; }
.lead-meta { color: #667085; font-size: .85rem; margin-top: 2px; }

/* detail panel stays in view while you scroll the list */
.st-key-panel { position: sticky; top: 3.2rem; max-height: calc(100vh - 4rem); overflow-y: auto; padding-right: 4px; }

.best {
    border-left: 5px solid #4F46E5; background: #EEF0FF; border-radius: 12px;
    padding: 14px 18px; margin: 4px 0 10px;
}
.best .label { font-size: 0.75rem; letter-spacing: .08em; color: #4F46E5; font-weight: 700; }
.best .name { font-size: 1.15rem; font-weight: 700; margin: 2px 0; }
.best .meta { color: #4B5163; font-size: 0.95rem; }
.stButton > button { border-radius: 10px; font-weight: 600; }
</style>
"""


@st.cache_resource
def _start_monitoring() -> bool:
    return init_sentry()


sentry_on = _start_monitoring()

st.set_page_config(page_title="Referral Finder", page_icon="🏥", layout="wide", initial_sidebar_state="collapsed")
st.markdown(CSS, unsafe_allow_html=True)
st.session_state.setdefault("selected_org", None)
st.session_state.setdefault("flash", None)
st.session_state.setdefault("page", 0)
st.session_state.setdefault("filter_sig", None)

categories = services.category_labels()
outcomes = services.outcome_labels()
ui = services.ui_settings()


# ---- actions (run as button callbacks, before the page reruns) ----

def _flash(message: str, error: bool = False) -> None:
    st.session_state.flash = (message, error)


def _open(org_id: int) -> None:
    st.session_state.selected_org = org_id
    st.session_state.flash = None


def _go_to_page(page: int) -> None:
    st.session_state.page = page


def _log_call(org_id: int, outcome: str) -> None:
    contact_id = st.session_state.get(f"who_{org_id}")
    services.log_call(org_id, outcome, contact_id)
    _flash(f"Logged: {outcomes[outcome]}")


def _find_contacts(org_id: int) -> None:
    result = services.find_contacts(org_id)
    if result.error:
        _flash(result.error, error=True)
    elif result.saved:
        _flash(f"Found {result.saved} new contact(s) from the web. {result.rejected} rejected by the evidence check.")
    else:
        _flash(
            "No new named contacts found."
            + (f" ({result.already_known} already on file.)" if result.already_known else "")
        )


def _already_called(org_id: int) -> None:
    services.mark_already_called(org_id)
    _flash("Marked as already called (hidden unless 'Show hidden' is on).")


def _phone_link(phone: str | None) -> str:
    """(718) 555-0142 as a tap-to-call link; falls back to the raw text."""
    if not phone:
        return "not published"
    digits = "".join(ch for ch in phone if ch.isdigit())
    shown = f"({digits[:3]}) {digits[3:6]}-{digits[6:10]}" if len(digits) == 10 else phone
    return f"[{shown}](tel:{digits})"


def _contact_line(c) -> str:
    phone = _phone_link(c.phone)
    email = f"[{c.email}](mailto:{c.email})" if c.email else "not published"
    return f"📞 {phone} &nbsp;&nbsp; ✉️ {email}"


def _contact_hint(r) -> str:
    """One line on the card: who we could ask for, or that we have no good contact yet."""
    title = (r.best_contact or "").title()
    if r.best_tier is None:
        return "⚠️ No contact on file"
    if r.best_tier == 0:
        return f"⭐ {title}"
    if r.best_tier == 1:
        return f"🚪 {title}"
    return f"⚠️ No referral contact yet (only {title or 'unnamed contact'})"


# ---- sidebar (data + monitoring; collapsed by default) ----

with st.sidebar:
    st.markdown("### 🏥 Referral Finder")
    st.caption("Find who sends home-care referrals, then call them.")
    st.divider()
    st.markdown("**Data**")
    refresh_borough = st.selectbox("Borough to refresh", services.boroughs(), key="refresh_borough")
    if st.button("🔄 Refresh from NPI Registry", width="stretch"):
        with st.spinner("Fetching from the NPI Registry..."):
            st.success(f"Saved {services.refresh_leads(refresh_borough)} leads.")
    with st.expander("Monitoring"):
        st.write(f"Sentry: {'on ✅' if sentry_on else 'off (no SENTRY_DSN)'}")
        if st.button("Send test error to Sentry"):
            try:
                raise RuntimeError("Referral Finder Sentry test error")
            except RuntimeError as exc:
                report_error(exc)
            st.success("Sent. Check your Sentry Issues page.")

# ---- header + filters ----

st.markdown(
    '<div class="hero"><div><h1>🏥 Referral Finder</h1>'
    "<p>The people who refer patients to long-term home care, ranked by referral potential and distance.</p></div>"
    '<div class="tag">Live data: CMS NPI Registry</div></div>',
    unsafe_allow_html=True,
)

radius_choices, radius_default = services.radius_options()
with st.container(border=True):
    f1, f2, f3, f4 = st.columns([1.1, 1, 1, 0.8], vertical_alignment="bottom")
    borough = f1.selectbox("Borough", services.boroughs())
    zip_code = f2.text_input("ZIP code", max_chars=5, placeholder="e.g. 11201")
    radius = f3.selectbox(
        "Search radius",
        radius_choices,
        index=radius_choices.index(radius_default),
        format_func=lambda m: "That ZIP only" if m == 0 else f"{m:g} miles",
        disabled=not zip_code,
    )
    show_hidden = f4.toggle("Show hidden", help="Include already called, not a fit and bad number leads")
    picked = st.pills(
        "Facility type",
        list(categories),
        selection_mode="multi",
        default=list(categories),
        format_func=categories.get,
    )
chosen = picked or list(categories)

if zip_code and not (zip_code.isdigit() and len(zip_code) == 5):
    st.warning("Enter a 5-digit ZIP, or leave it blank.")

leads = services.list_leads(borough, zip_code or None, chosen, show_hidden, radius_miles=radius if zip_code else 0)

# a new search starts back on page 1
signature = (borough, zip_code, radius, tuple(chosen), show_hidden)
if st.session_state.filter_sig != signature:
    st.session_state.filter_sig = signature
    st.session_state.page = 0

# ---- summary cards ----

k1, k2, k3, k4 = st.columns(4)
near = f" within {radius:g} mi of {zip_code}" if zip_code and radius else ""
k1.metric("Leads", len(leads), help=f"Matching your filters{near}", border=True)
k2.metric("Avg potential", round(sum(r.fit for r in leads) / len(leads)) if leads else "-", border=True)
k3.metric("Already worked", sum(r.status != "untried" for r in leads), help="Contacted, called or ruled out", border=True)
k4.metric("Calls logged", sum(r.attempts for r in leads), border=True)

list_col, panel_col = st.columns([5, 4], gap="large")

# ---- lead cards ----

with list_col:
    head, pager = st.columns([3, 2], vertical_alignment="center")
    head.markdown("#### Leads")
    pages = max(1, math.ceil(len(leads) / ui["page_size"]))
    page = min(st.session_state.page, pages - 1)
    if not leads:
        st.info("No leads match. Try a bigger radius, or use 'Refresh from NPI Registry' in the sidebar if the database is empty.")
    else:
        head.caption("Best referral potential first, nearest first when tied. Open a lead to see why it scored what it did.")
        prev_col, label_col, next_col = pager.columns([1, 2, 1], vertical_alignment="center")
        prev_col.button("◀", key="prev", on_click=_go_to_page, args=(page - 1,), disabled=page == 0, width="stretch")
        label_col.markdown(f"<div style='text-align:center'>Page {page + 1} of {pages}</div>", unsafe_allow_html=True)
        next_col.button("▶", key="next", on_click=_go_to_page, args=(page + 1,), disabled=page >= pages - 1, width="stretch")

        start = page * ui["page_size"]
        for r in leads[start : start + ui["page_size"]]:
            selected = r.id == st.session_state.selected_org
            if selected:
                st.markdown(
                    f"<style>.st-key-card_{r.id} {{ border: 2px solid #4F46E5 !important; background: #F4F5FF; }}</style>",
                    unsafe_allow_html=True,
                )
            with st.container(border=True, key=f"card_{r.id}"):
                c1, c2, c3 = st.columns([1, 6, 2], vertical_alignment="center")
                c1.markdown(f'<div class="fit fit-{r.band_style}">{r.fit}</div>', unsafe_allow_html=True)
                bits = [r.band, categories[r.category], r.zip5 or "", f"{r.miles:.1f} mi" if r.miles is not None else "", STATUS_LABELS.get(r.status, r.status)]
                if r.attempts:
                    bits.append(f"{r.attempts} call{'s' if r.attempts != 1 else ''}")
                c2.markdown(
                    f'<div class="lead-name">{r.name.title()}</div>'
                    f'<div class="lead-meta">{" · ".join(b for b in bits if b)}</div>'
                    f'<div class="lead-meta">{_contact_hint(r)}</div>',
                    unsafe_allow_html=True,
                )
                c3.button(
                    "Viewing" if selected else "Open ➜",
                    key=f"open_{r.id}",
                    on_click=_open,
                    args=(r.id,),
                    type="primary" if selected else "secondary",
                    width="stretch",
                )

# ---- lead panel ----

with panel_col:
    with st.container(key="panel"):
        org_id = st.session_state.selected_org
        if org_id is None:
            with st.container(border=True):
                st.markdown("#### 👈 Pick a lead")
                st.write("Open any lead to see its contacts, find decision makers on the web and log your calls.")
        else:
            detail = services.lead_detail(org_id)
            org, summary = detail.organization, detail.summary
            if st.session_state.flash:
                message, is_error = st.session_state.flash
                (st.error if is_error else st.success)(message, icon="⚠️" if is_error else "✅")
                st.session_state.flash = None

            with st.container(border=True):
                st.markdown(f"### {org.name.title()}")
                st.badge(categories.get(org.category, org.category), color=CATEGORY_COLORS.get(org.category, "gray"))
                st.badge(STATUS_LABELS.get(org.status, org.status))
                band = services.band_for(org.fit_score)
                st.progress(org.fit_score / 100, text=f"Referral potential {org.fit_score} / 100 · {band['label']}")
                with st.expander("Why this score?"):
                    for reason, points in detail.score_parts:
                        st.markdown(f"**+{points}** &nbsp; {reason}")
                    if detail.could_add:
                        st.caption("To raise it: " + " · ".join(detail.could_add))
                st.write(f"📍 {org.address_line.title() if org.address_line else ''}, {org.borough} {org.zip5}")
                st.markdown(f"☎️ Main line: {_phone_link(org.main_phone)}")
                m1, m2, m3 = st.columns(3)
                m1.metric("Calls", summary.attempts)
                m2.metric("Miss streak", summary.voicemail_streak, help="Voicemails or no-answers in a row")
                m3.metric("Contacts", len(detail.contacts))
                if summary.last_outcome:
                    st.caption(f"Last outcome: {outcomes.get(summary.last_outcome, summary.last_outcome)}")

            tab_contacts, tab_log, tab_history = st.tabs(["👤 Contacts", "📞 Log a call", "🕒 History"])

            with tab_contacts:
                tiers = [services.contact_tier(c) for c in detail.contacts]
                if tiers and tiers[0] <= 1:  # a referral contact, or someone who can route you
                    best = detail.contacts[0]
                    label = "⭐ LIKELY REFERRAL CONTACT" if tiers[0] == 0 else "🚪 BEST WAY IN: ASK WHO HANDLES REFERRALS"
                    st.markdown(
                        f'<div class="best"><div class="label">{label}</div>'
                        f'<div class="name">{(best.name or "Unnamed").title()}</div>'
                        f'<div class="meta">{best.title or ROLE_LABELS.get(best.role, best.role)}</div></div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(_contact_line(best))
                    if best.source == "web":
                        st.caption(f'Found on the web, not yet verified by a call. [Source]({best.source_url}): "{best.evidence}"')
                    others = list(zip(detail.contacts, tiers, strict=True))[1:]
                else:
                    st.warning(
                        "**No referral contact found yet.** The people on file are finance or executive roles, who rarely handle "
                        f"referrals. Call the main line ({_phone_link(org.main_phone)}) and ask for **Social Work, "
                        "Discharge Planning or Admissions**, or try 'Find contacts on the web'.",
                        icon="📞",
                    )
                    others = list(zip(detail.contacts, tiers, strict=True))
                for c, tier in others:
                    with st.container(border=True):
                        st.markdown(f"**{(c.name or 'Unnamed').title()}**" + (f" · {c.title}" if c.title else ""))
                        st.caption(f"{ROLE_LABELS.get(c.role, c.role)} · {TIER_LABELS[tier]}")
                        st.markdown(_contact_line(c))
                        if c.source == "web":
                            st.caption(f'Found on the web, not yet verified by a call. [Source]({c.source_url}): "{c.evidence}"')
                if not detail.contacts:
                    st.info("No contacts on file yet.")
                st.button(
                    "🔎 Find contacts on the web",
                    key=f"find_{org_id}",
                    on_click=_find_contacts,
                    args=(org_id,),
                    type="primary",
                    width="stretch",
                    help="One web search + Gemini. Uses trial credits, so use it on leads you care about.",
                )
                st.caption(
                    "**Why this button?** The federal registry usually lists only an owner or finance contact. "
                    "This searches the web (Nimble) for staff at this facility, such as social work, discharge or admissions, "
                    "and an AI (Gemini) reads the pages. Code then checks every name, phone and email really appears on the "
                    "page, so nothing is made up. Each person is saved with a source link."
                )

            with tab_log:
                who = {None: "Front desk / main line"} | {c.id: f"{c.name} ({c.title or c.role})" for c in detail.contacts}
                st.selectbox("Who did you reach out to?", list(who), format_func=who.get, key=f"who_{org_id}")
                grid = st.columns(2)
                for i, (code, label) in enumerate(outcomes.items()):
                    grid[i % 2].button(label, key=f"out_{org_id}_{code}", on_click=_log_call, args=(org_id, code), width="stretch")
                st.button(
                    "🟣 Already called (hide this lead)",
                    key=f"ac_{org_id}",
                    on_click=_already_called,
                    args=(org_id,),
                    disabled=org.status == "already_called",
                    width="stretch",
                )

            with tab_history:
                if detail.history:
                    st.caption("New York time")
                    st.dataframe(
                        pd.DataFrame(
                            {
                                "When": [a.timestamp.astimezone(NY).strftime("%b %d, %I:%M %p") for a in detail.history],
                                "Outcome": [outcomes.get(a.outcome, a.outcome) for a in detail.history],
                            }
                        ),
                        hide_index=True,
                        width="stretch",
                    )
                else:
                    st.info("No calls logged yet.")
