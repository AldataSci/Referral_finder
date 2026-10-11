# Referral Finder: Product Spec (v1)

A single-user web app: **I search by ZIP code, borough, or neighborhood, and it returns a ranked list of referral leads, prioritized by how likely I am to actually reach the decision maker, with the organization, contact name, phone, and email (when known), so I can call or email them and log what happened.** Built on free tiers and sponsor trials.

**Owner:** Al, Lead Generation Associate, non-profit home care agency
**Build tool:** Claude Code, one milestone at a time (see Section 14)
**Status:** Spec ready and reviewed for Claude Code feasibility (Section 6.5); not yet built
**Hackathon:** AI Engineer NYC 2026 (MLH), **Sunday, October 11**. Submissions close **11:59 PM EDT** the same day.

---

## 0. Hackathon plan (today)

> **For Claude Code: today (October 11), Section 0 overrides the rest of this document.** Wherever Sections 1–18 or Appendix A describe something more complete (SQLite dual mode, full tests, dedupe, neighborhoods, the three-step contact finder, heat maps), build the simpler version in Sections 0.3 and 0.4b instead. The rest of the document is the target for after the hackathon.

### 0.1 Prize tracks and where each tool fits

| Track | Use in this product | Why it's a genuine fit (what I tell judges) |
|---|---|---|
| **Best Overall** | The whole product | A real user (me), a real problem (I've exhausted Google Maps), a tool I'll keep using at work |
| **Tiger Data** | The app's database. Call attempts are a **hypertable**; a **continuous aggregate** powers **"Best time to call"** (Section 11.6) | Call logs are time-series data. Tiger turns them into "this discharge planner picks up Tue–Thu before 10 AM," which directly attacks my voicemail problem |
| **Nimble** | **Web contact finder** (Section 11.7): find each organization's website and staff pages, extract the text | Live web context turns a front-desk phone number into a named decision maker with an email, the weakest part of my data |
| **Gemini API** | Reads the pages Nimble returns and extracts **structured contacts** (name, title, email, quote); code verifies every quote is really on the page | AI used for a real extraction job, with a guardrail against made-up names |
| **Sentry** (+ raffle) | Error monitoring and tracing around every NPI, Nimble, Gemini, and database call, plus AI call monitoring if Sentry supports the Gemini SDK | A tool that depends on 4 outside services needs to show which one failed. **Must opt in to the Sentry category when submitting.** |
| **Snowflake** | **Not used** | It would mean building on a second data platform (Streamlit in Snowflake, Cortex) alongside Tiger Cloud. Solo, in one day, that splits focus, and Gemini already covers the AI. Skipping it is a deliberate choice. |

### 0.2 Tool priority (reviewed for realism)
Ranked by value to the product ÷ effort today. Sponsor tracks reward **depth** ("best use"), so two tools used well beat five used shallowly.

| Priority | Tool | Effort today | Verdict |
|---|---|---|---|
| 1 | **NPI + Streamlit + Tiger Cloud (as plain Postgres)** | Medium | **Must have.** Without it there's no product and no demo |
| 2 | **Nimble + Gemini contact finder** | Medium–high | **Must have.** It's the product's purpose (names + emails), the demo's best moment, and two prize tracks |
| 3 | **Sentry** | Low (~15–30 min) | **Do it early (in M0).** Cheap, raffle entry, and useful for debugging all day |
| 4 | **Tiger time-series features** (hypertable + continuous aggregate) | Medium | **Only after #2 works.** Needed to compete in the Tiger track; plain Postgres alone is unlikely to win "best use" |
| 5 | Snowflake | High | **Skip** |

### 0.3 Simplifications for today (vs. the full spec)
- **Tiger Cloud only. No SQLite dual mode today.** Keep `DATABASE_URL` so it can be added later, but skip the SQLite fallback and most tests. The offline backup is screenshots and a recorded demo.
- **Contact finder uses one Nimble Search call instead of search → site map → extract.** Nimble Search returns the content of top results, so one query like `"<org name>" Brooklyn director of social work` can feed Gemini directly. Add the site map + extract steps after the hackathon.
- **Simple reachability:** attempt count, last outcome, voicemail streak. The full formula comes later.
- **No dedupe, doctor grouping, or neighborhoods.** Search by borough or ZIP, three organization categories.
- **"Best time to call" shown as a simple table or bar chart**, not a heat map, unless time allows.

### 0.4 Today's build, with checkpoints
Time estimates are guesses. The checkpoints and the feature freeze are what matter.

| Time | Work | Milestones |
|---|---|---|
| Now–12:30 | Accounts and keys (Tiger Cloud, Gemini, Nimble, Sentry). Python env, Claude Code. Then a **smoke test**: one tiny call to each service to prove every key works | setup |
| 12:30–1:30 | Skeleton + Sentry; database on Tiger Cloud (tables + hypertable) | M0, M1 (lite) |
| 1:30–3:00 | NPI search: **Brooklyn only; SNFs, rehab, case management**; save to DB; simple fit score | M2a (narrow), M4 (lite) |
| 3:00–4:30 | Streamlit: search by borough/ZIP → ranked table → select a lead → panel with info + log call buttons | M6a, M6b (lite), M5 (lite) |
| **4:30** | **Checkpoint 1: a working, demoable MVP.** Commit. If it's not working, spend the rest of the day making it work, not adding features | |
| 4:30–6:30 | **Contact finder** (one Nimble Search + Gemini + evidence check) | M7a (lite) |
| **6:30** | **Checkpoint 2.** Commit | |
| 6:30–8:00 | **Best time to call:** continuous aggregate + labeled demo call history + simple chart | M7b (lite) |
| 8:00–9:00 | Buffer. Something will break; this hour is for that | |
| **9:00** | **Feature freeze.** Only bug fixes after this | |
| 9:00–10:30 | Rehearse the demo, record a video if required, write the submission | |
| 10:30–11:30 | Submit: list every track, **opt in to Sentry**. Leave buffer before 11:59 | |

### 0.4b What each "lite" milestone means today
| Milestone today | Build exactly this | Skip until after the hackathon |
|---|---|---|
| **Setup** | First, a `.gitignore` that includes `.env`. Then `scripts/smoke_test.py`: one tiny call each to NPI (1 SNF in `112*`), Tiger Cloud (`SELECT 1`, then create a test table, make it a hypertable, drop it), Gemini (one-sentence prompt), Nimble (one search), and Sentry (one test error). Prints PASS/FAIL per service; never prints keys or the database URL | — |
| **M0** | Folder skeleton, `pyproject.toml`, `requirements.txt`, `.env.example`, `.gitignore`, CLAUDE.md, empty Streamlit app, Sentry initialized once | README beyond run instructions |
| **M1 (lite)** | SQLModel tables for Organization, Contact, CallAttempt on **Tiger Cloud only**; `call_attempts` as a hypertable | SQLite support, repository tests |
| **M2a (narrow)** | NPI organization search for **Brooklyn (`112*`)**, 3 categories (verify taxonomy names in the live API first), LOCATION address, ZIP/phone normalization, save registered official as a contact, simple disk cache | Other boroughs, fixtures, cap splitting |
| **M4 (lite)** | Fit = category weight + has registered contact + has phone + has email, from `scoring.yaml` | Practice size, large-institution rule |
| **M5 (lite)** | Log a call with an outcome; show attempts, last outcome, voicemail streak; status → contacted / bad_number / not_a_fit | Full reachability formula, recency, labels |
| **M6a + M6b (lite)** | One page: borough/ZIP + category inputs → table sorted by fit → select a row → panel with org info, contacts, log-call buttons, "Already called" | Data Refresh page (use a sidebar button instead), Export page, editable status column |
| **M7a (lite)** | "Find contacts" button: **one** Nimble Search call → Gemini structured extraction → evidence check in code → save as web contacts with source URL + quote | Site map + extract steps |
| **M7b (lite)** | Continuous aggregate (Section 11.6, corrected design) + script that inserts clearly flagged demo calls (`is_demo = true`) + bar chart of answer rate by hour in the panel | Heat map, category-wide summary |

**Tests today:** only two small test files: fit scoring, and the contact finder's evidence check (it must reject a contact whose quote isn't in the page). Everything else is checked by using the app.

**Fallback rules (decide fast, don't sink hours):**
- **Tiger Cloud won't connect after 30 minutes:** use a local SQLite file, keep building, and drop the Tiger track.
- **Nimble isn't working by 5:30:** skip the contact finder, polish the core app, and drop the Nimble track. (Gemini can still do the optional fit reasons.)
- **Behind at 6:30:** skip "Best time to call" entirely. The contact finder is the stronger demo.

### 0.5 Unverified, check in the first 30 minutes
I couldn't confirm these from the docs I could reach. Check each before relying on it:
- **Nimble trial:** how fast the key is issued, how many credits it includes, and the exact Search response format (the smoke test will show)
- **Tiger Cloud trial:** whether a credit card is needed, and how to enable the time-series extension on a new service
- **Gemini free tier:** rate limits (the contact finder makes one call per lead, so this should be fine)
- **Sentry:** whether it has an integration for Google's Gemini SDK; if not, wrap Gemini calls in manual Sentry spans
- **Sentry + Streamlit:** Streamlit reruns the whole script on every click, so initialize Sentry only once (e.g., cached). Streamlit also shows errors on the page itself, which may stop Sentry from catching them automatically, so the service layer should report errors to Sentry explicitly
- **Submission format:** whether MLH asks for a video, a GitHub link, or a Devpost-style page
- **Claude Code usage limits:** a full day of heavy use can hit your plan's limits. Keep each request focused on one milestone.

**Skipped today, built after:** M2b (doctor grouping), M3 (neighborhoods), full M5 scoring, full M7a (site map + extract), M7c, M8, M9, SQLite fallback.

### 0.6 Demo script (about 3 minutes)
1. **Problem (30 sec):** "I generate referral leads for a dementia home care agency. I've called every lead I can find on Google Maps. The front desk transfers me, but the person I reach often doesn't pick up or isn't the one who handles referrals."
2. **Search (30 sec):** search Brooklyn → ranked list of real nursing and rehab facilities from the federal NPI Registry.
3. **Find contacts (60 sec, live):** open a lead → "Find contacts" → Nimble searches the web → Gemini extracts named staff (e.g., a Director of Social Work) with a source link and quote. *Pick a demo lead beforehand whose website actually lists staff.*
4. **Best time to call (30 sec):** log a call → reachability updates → show the best-time chart from Tiger's continuous aggregate. *Say out loud that the call history is demo data.*
5. **Under the hood (30 sec):** architecture diagram (Section 13) and the Sentry trace for that contact search.

**Have a backup:** run the demo searches once beforehand so results are cached, and take screenshots in case the Wi-Fi fails.

### 0.7 After the hackathon
Trials end, so every sponsor feature is built to be optional and swappable:
- **Database:** `DATABASE_URL` can point to any Postgres or a local SQLite file if the Tiger trial ends.
- **Nimble:** if the trial ends, the contact finder turns off (or switches to Clay/Apollo) and everything else keeps working.
- **Sentry and Gemini:** check whether their free plans cover my usage after the trial.
- **Wipe demo data:** demo call history is flagged (`is_demo`) and deleted before real use.
- Then continue with the skipped milestones.

---

## 1. The ideal lead

> **A decision maker at an organization who handles referrals for seniors (or anyone) needing long-term home care services.**

Typical titles: Discharge Planner, Case Manager, Social Worker, Director of Social Work, Director of Case Management, Care Manager (MLTC plans), Admissions/Discharge Coordinator, Practice Manager (physician practices).

The product serves one purpose: **find these people and return their contact information** (name, title, phone number, and email) so I can reach them.

> **Data coverage note:** The NPI Registry covers organization details and main phone numbers well (though some numbers are outdated), but **decision-maker names and especially email addresses are the weakest part of the data**. v1 addresses this with the **web contact finder** (Nimble + Gemini, Section 11.7), which pulls named contacts from organizations' own websites. It won't find everyone, since many small practices list no staff online, so **Clay or Apollo enrichment remains the #1 upgrade after v1.**

## 2. Problem

- I find leads manually on Google Maps and call them (rehab centers, skilled nursing facilities, discharge planners, private doctors' offices).
- I've called almost every lead I can find that way.
- The front desk can't reliably get me to the decision maker. It usually transfers me, but the person I reach often doesn't pick up, is sometimes the wrong person, and the front desk itself is often unsure who handles home care referrals.
- Many calls go to voicemail; some people never call back even after many voicemails.

## 3. Product goal

```
search (ZIP / borough / neighborhood) + optional category filter
   → list of in-area organizations, ranked by Priority
   → each lead: organization, category, address, phone, contact name/title, email if known
   → I call → I log the outcome in one click
   → the app learns who is reachable and re-ranks
```

The app does **not** write scripts or emails. It finds leads, tracks reachability, and tells me who to call next.

## 4. Agency profile

| Item | Value |
|---|---|
| Services | In-home care by home health aides specialized in Alzheimer's and dementia support |
| Payers accepted | Medicaid / MLTC plans, private pay |
| Key existing partners | MLTC plans |
| Service area (v1) | Brooklyn, Queens, Manhattan (not Bronx or Staten Island) |

**Targeting implications**
- Dementia focus: neurology, geriatric medicine, and geriatric psychiatry practices are high-value, especially for private-pay families.
- Medicaid / MLTC: patients leaving SNFs, rehab, and hospitals often need ongoing personal care at home; discharge and case management staff make those referrals.

## 5. Scope

### v1 (this spec)
1. Search by **ZIP code**, **borough**, or **neighborhood**, with optional category filter
2. Discover healthcare organizations and practices via the NPI Registry (free, no key)
3. Results table ranked by **Priority** (Fit + Reachability, Section 11)
4. One-click **"Already called"** to mark leads I've contacted before this app existed (my old Google Maps calls)
5. Add or edit the **decision maker** for an organization (names are often learned on a call: "talk to Maria in social work")
6. **Log every call attempt** with its outcome in one click
7. **Reachability score** computed from my call history (Section 11)
8. Export results to CSV
9. **Web contact finder** (Nimble + Gemini): find named decision makers and emails on an organization's website, with evidence (Section 11.7)
10. **Best time to call** from call history (Tiger Data, Section 11.6)
11. **Error monitoring and tracing** (Sentry)
12. *(Optional)* One-line AI explanation of why a lead fits

### Later (not in v1), in priority order
1. **Clay or Apollo enrichment** to find decision-maker names and **email addresses** (top priority; see the data coverage note in Section 1)
2. Google Places for non-medical sources (elder law, senior centers, senior housing, adult day) and website lookups
3. Importing existing lead lists from CSV
4. Follow-up reminders; in-person visit planner

(Hosting moved into v1: the database is Tiger Cloud Postgres from the start, and deploying a private online version is optional milestone M9.)

### Out of scope
Outreach scripts or email drafts, auto-sending email, auto-dialing, LinkedIn, scraping sites against their terms, multiple users, any patient information.

### Known v1 limitations (be upfront in the UI)
- **Reachability is unknown until I call.** New leads start as "Untried" and are ranked by Fit. The app gets smarter as I log calls.
- **Decision-maker names:** the free data source rarely names the person who handles referrals. It gives the NPI "authorized official" (whoever registered the organization, often an owner or executive), shown as "Registered contact." The real decision maker comes from the web contact finder (when the organization lists staff online) or is learned on a call and added by me.
- **Email addresses:** the NPI Registry doesn't provide them. The web contact finder finds them only when an organization lists them on its website; otherwise I add them manually until Clay/Apollo is added.
- **Phone numbers:** NPI data is self-reported and can be outdated; I can flag bad numbers.
- **Old Google Maps calls:** the app doesn't know about them; I mark them "Already called" as I see them.

## 6. Ground rules

1. **Free tiers and sponsor trials only.** No paid services; cache every external call; run paid-per-use calls (Nimble, Gemini) on demand, never in bulk. (The build tool, Claude Code, is separate and requires a Claude account.)
2. **Public business information only.** Organizations and professionals. No patient data anywhere.
3. **Never send call notes or call history to an AI model.** Only public organization data and public web page text.
4. **Secrets in `.env` only**, never committed. This includes the database password (`DATABASE_URL`) and the Gemini, Nimble, and Sentry keys. In a deployed app, secrets go in the host's secrets settings, never in code.
5. **Web data from organizations' own public websites only.** Use Nimble for web search and organization websites; never to scrape LinkedIn, Google Maps, or any site whose terms forbid it.
6. **No personal data in monitoring.** Sentry gets errors and timings only: no call notes, call history, or contact details (`send_default_pii` off).
7. **Private access only.** If the app is deployed online, only I can open it. My leads and call notes must never sit behind a public link.

## 6.5 Feasibility with Claude Code (reviewed)

**Verdict: all of v1 is buildable with Claude Code.** The code itself (API client, database, scoring, Streamlit screens, tests) is standard Python work well within what Claude Code does. What Claude Code *can't* do is set up my accounts, make judgment calls about my job, or know how real decision makers behave; those are on me.

### What Claude Code can do
- Write all the code and tests, run them, and fix failures
- Call the live NPI Registry during development to verify taxonomy terms, ZIP behavior, and the 1,200-result cap, and save real responses as test fixtures
- Look up current documentation (Streamlit, google-genai) instead of guessing
- Draft `neighborhoods.yaml` (starting from the United Hospital Fund neighborhood ZIP groupings used by NYC's health department), for me to review
- Launch the app locally, commit to Git, and explain every file in plain language

### What I must do myself
- **Have a Claude subscription or Anthropic Console account to run Claude Code.** This is the one paid piece; the product itself runs on free tiers.
- Create accounts and keys (Tiger Cloud, Gemini, Nimble, Sentry) and paste them into `.env` myself
- Install Python and Git
- Click through the app and judge whether results make sense (Claude Code can start the app, but I test the experience)
- Decide category weights and review the neighborhood map
- Use the app for several weeks before tuning the reachability rules
- Clay enrichment stays manual on the free plan (no API access); check Apollo's free-plan API limits before planning around it

### Risks found in review, and the revisions made
| Risk | Revision in this plan |
|---|---|
| The NPI milestone was too big for one session | Split into M2a (organizations) and M2b (doctor grouping + cap splitting) |
| Streamlit tables don't support a button on every row | Screens now use row selection to open a lead panel, plus an editable status column (Section 12) |
| Clickable `tel:` / `mailto:` links may not render inside a Streamlit table | Verify in M6a; fallback is plain text plus clickable links in the lead panel |
| Doctors at hospitals share the hospital's address, so "grouping by address" can create one giant fake practice | Groups above a size threshold are labeled "Large institution" and get no size bonus (Section 7) |
| The NPI contact's phone is often a corporate or billing line, not a direct line | Signal renamed to "separate contact phone" with a smaller weight (Section 11.1) |
| Tests that call the live API are slow and flaky | Fixtures are recorded once by a script; tests never call the API |
| A local SQLite file only works on one laptop, and free hosts like Streamlit Community Cloud don't keep local files | The app's database is **Tiger Cloud Postgres** (Tiger Data prize track). The same code runs on SQLite for tests and as an offline fallback (Section 13). |
| Tiger-specific features (hypertables, continuous aggregates) don't exist in SQLite | They're created in one isolated setup function that only runs on Tiger Cloud; on SQLite the app computes the same stats with plain queries |
| Venue Wi-Fi could fail during the demo | Switch `DATABASE_URL` to a local SQLite file, with a pre-loaded demo dataset |
| Sponsor trials (Tiger Cloud, Nimble, Sentry) may expire or cost money after the hackathon | Every sponsor feature is optional and swappable (Section 0.7); export to CSV regularly as a backup |
| Claude Code may over-build or skip ahead | `CLAUDE.md` rules, one milestone per session, and plan mode before each milestone |

## 7. Target categories (v1)

Search terms must be verified against the NPI Registry's taxonomy descriptions in M2a. Many specialties are registered on **individual** doctors (NPI-1), not their practices, so those are searched as individuals and grouped into practices by shared location address and phone.

**Contacts for grouped practices:** individual doctor records (NPI-1) have **no registered official**, so the high-value dementia categories won't come with a "Registered contact." Instead, save each grouped doctor as a contact with role `clinician` (name + specialty). That gives me a real name to reference when calling ("I'm calling about Dr. Lee's patients; who handles home care referrals?").

**Large institutions:** doctors employed by hospitals often list the hospital's address and main line, so grouping can create one huge "practice." Any group above a configurable size (default 25 clinicians) is labeled **"Large institution,"** gets no practice-size bonus, and shows a hint to ask for the department's social worker or care coordinator.

| Category | Search as | Who handles referrals there | Fit |
|---|---|---|---|
| Skilled nursing facilities | Organizations (NPI-2) | Discharge planner, social worker | **High** |
| Rehab facilities / clinics | Organizations | Discharge planner, case manager | **High** |
| Case management agencies | Organizations | Case manager | **High** |
| Neurology | Individuals → grouped | Practice manager, social worker | **High** (dementia) |
| Geriatric medicine | Individuals → grouped | Practice manager, care coordinator | **High** (dementia) |
| Geriatric psychiatry | Individuals → grouped | Practice manager, social worker | **High** (dementia) |
| Hospices | Organizations | Social worker, intake coordinator | Medium |
| Dialysis centers | Organizations | Social worker | Medium |
| Cardiology, pulmonology, oncology | Individuals → grouped | Practice manager, nurse navigator | Low–Medium |
| Outpatient physical therapy | Organizations | Clinic manager | Low–Medium |

## 8. Location search

All three search types resolve to a set of 5-digit ZIP codes, then filter leads by their **practice LOCATION** ZIP.

| Search type | How it resolves | Config file |
|---|---|---|
| ZIP code | Used directly (must be in service area) | — |
| Borough | All ZIPs for that borough | `config/service_area.yaml` |
| Neighborhood | ZIPs mapped to that neighborhood | `config/neighborhoods.yaml` |

- NYC neighborhoods don't line up exactly with ZIP codes; the mapping is approximate and editable. Neighborhood search supports partial names (e.g., "bay" → Bay Ridge, Bayside).
- Results show the neighborhood and borough derived from the lead's ZIP.

**Service area ZIP prefixes (verify in M2a):**
- Brooklyn: `112`
- Queens: `111`, `113`, `114`, `116`, plus border ZIPs `11004`, `11005`
- Manhattan: `100`, plus `101` and `102` (101xx are mostly single-building ZIPs such as office towers; 102xx includes Battery Park City's residential ZIPs `10280`–`10282`)

**Manhattan volume note:** a borough-wide query (e.g., neurology in `100*`) is likely to hit the 1,200-result cap. Split Manhattan queries into narrower prefixes (`1000*`, `1001*`, ...) or individual ZIPs, and log any query that hits the cap.

`config/neighborhoods.yaml` format (fill in and verify during build):
```yaml
Queens:
  Flushing: ["11354", "11355", "11358"]   # verify
Brooklyn:
  # Bay Ridge: [...]
Manhattan:
  # Upper East Side: [...]
```

## 9. NPI Registry API (CMS)

- Endpoint: `GET https://npiregistry.cms.hhs.gov/api/?version=2.1`
- No API key. JSON response.
- Key params: `enumeration_type` (NPI-1 individual / NPI-2 organization), `taxonomy_description`, `postal_code`, `state`, `organization_name`, `address_purpose`, `limit`, `skip`
- **Limits:** `limit` max 200 per request; `skip` max 1000 → **at most 1,200 results per query**. If a query hits 1,200, split it into narrower ZIP prefixes.
- `postal_code` accepts a trailing `*` wildcard after at least two characters (e.g., `112*`). Always include `state=NY` as well.
- `taxonomy_description` matches **any** taxonomy on a record; check the primary taxonomy in code.
- `result_count` is the count on the current page, not the total. Paginate until a short page returns.
- ZIPs are often stored as 9 digits without a hyphen; normalize to 5.
- Use the **LOCATION** address for area filtering and the location phone as the main phone.
- Registered contact fields (organization records only; individual records don't have them): `basic.authorized_official_first_name`, `_last_name`, `_title_or_position`, `_telephone_number`.
- Be polite: short delay between requests; cache responses on disk (refresh after 30 days).

**Fetching strategy:** NPI can't search by neighborhood. Fetch by borough ZIP prefix + category, store in the database, and run all searches against it. Searches stay fast and API usage stays low.

## 10. Data model

**Organization**
- `id`, `name`, `category`, `npi` (nullable), `source` (npi / manual)
- `address_line`, `zip5`, `neighborhood`, `borough`
- `main_phone`, `main_phone_normalized`
- `primary_taxonomy`, `clinician_count` (for grouped practices)
- `fit_score` (0–100), `ai_reason` (nullable)
- `status`: untried / contacted / active / already_called / not_a_fit / bad_number / unreachable (transitions in Section 11.5)
- `created_at`, `updated_at`, `fetched_at`

**Contact**
- `id`, `organization_id`, `name`, `title`, `phone`, `email`
- `role`: decision_maker / gatekeeper / registered_official / clinician / other
- `source`: npi_official / learned_on_call / web / manual (later: clay / apollo)
- `source_url`, `evidence` (quote from the page; required when source = web), `verified` (bool; I confirm on a call)
- `reachability_score` (0–100, nullable until first call), `reachability_label`

**CallAttempt** (one row per call or email; a **hypertable** on Tiger Cloud, partitioned by `timestamp`)
- `id`, `organization_id`, `contact_id` (nullable: "front desk" if unknown), `timestamp`
- Primary key is (`id`, `timestamp`), because Tiger hypertables require the time column in any unique key
- `channel`: call / email
- `outcome` (see Section 11)
- `note` (short, optional)
- `is_demo` (bool; true for sample data used in the hackathon demo, deleted before real use)

## 11. Ranking: Fit, Reachability, Priority

### 11.1 Fit score (who they are) — 0 to 100
Known before any calls. Answers: *"Is this the kind of organization whose staff refer people to long-term home care?"*
- Category weight (Section 7; weights in `config/scoring.yaml`)
- Has a named decision maker (big boost) or at least a registered contact
- Contact has a **separate phone** from the main line (small boost: possibly a direct line, though NPI contact numbers are often corporate or billing lines)
- Has an email
- Practice size (clinician count, capped)
- The total is capped at 100. Fit is **recalculated whenever contacts change** (e.g., adding a decision maker raises it).

### 11.2 Reachability score (can I reach them?) — 0 to 100
Learned from my logged calls. Tracked **per contact** (the decision maker), with an organization-level fallback ("front desk") when no contact is known.

**Call outcomes I can log (one click each):**

| Outcome | Meaning | Reachability effect |
|---|---|---|
| `reached_decision_maker` | Spoke with the person who handles referrals | Strong positive |
| `callback_received` | They called me back after a voicemail | Strong positive |
| `email_replied` | They replied to my email | Strong positive |
| `meeting_set` / `referral_received` | Best outcomes | Strongest positive; status → active |
| `transferred` | Front desk put me through | Positive |
| `got_name_from_gatekeeper` | Learned who the decision maker is | Neutral; prompts me to add the contact |
| `voicemail_left` | Left a voicemail | Negative (small) |
| `no_answer` | Nobody picked up, no voicemail | Negative (small) |
| `gatekeeper_blocked` | Front desk wouldn't connect me | Negative |
| `wrong_number` | Number is bad | Status → bad_number |
| `not_interested` | Clear no | Status → not_a_fit |

**Which outcomes count:**
- **Attempts** = positive outcomes + `voicemail_left` + `no_answer` + `gatekeeper_blocked`.
- `got_name_from_gatekeeper` is neutral and **not** counted as an attempt.
- `wrong_number` and `not_interested` change the status instead of the score.

**How the score is calculated (simple and explainable):**
- **Response rate with a neutral starting point:**
  `reachability = 100 × (positive_responses + 1) / (attempts + 2)`
  The +1/+2 makes the formula start at a neutral 50, which is never shown: untried leads display "Untried" and rank by Fit only.
- **First-call bonus:** reached on the very first attempt → +10, kept permanently (capped at 100).
- **Worked examples:** picks up on the first call → 67 + 10 bonus = **77 (Hot)**. Reached once, then a voicemail → 50 + 10 = 60 (Warm). Nine voicemails in a row → 9 (Cold).
- **Voicemail streak rule:** **10 consecutive voicemails / no-answers with no callback → label "Unreachable,"** score set to 0. Any positive outcome (e.g., a callback) resets the streak. (Threshold configurable in `config/scoring.yaml`.)
- **Recency:** outcomes older than 90 days count half (people change roles).

**Labels shown in the table:**

| Label | Rule |
|---|---|
| Untried | No attempts yet |
| Hot | Score ≥ 70 |
| Warm | 40–69 |
| Cold | 1–39 |
| Unreachable | Voicemail streak rule triggered |

### 11.3 Priority (what I see sorted)
Reachability is tracked per contact, but the table shows one row per organization, so:
**organization reachability = the best reachability among its contacts and its front-desk record.** (If Maria is unreachable but the front desk always transfers me, the organization is still worth calling.)

```
untried leads:   priority = fit_score
tried leads:     priority = 0.4 × fit_score + 0.6 × organization_reachability
```
Weights live in `config/scoring.yaml`. Unreachable, not_a_fit, bad_number, and already_called are hidden by default (toggle to show).

Each row shows **Fit**, **Reachability label**, and **attempts / last outcome / days since last attempt**, so the ranking is never a mystery.

### 11.4 Dedupe
1. Same NPI → same organization
2. Same normalized phone (10 digits) **and** (same street address **or** name similarity ≥ 60) → match. Phone alone isn't enough: departments in one hospital or building often share a switchboard.
3. Same ZIP + same street address + name similarity ≥ 90 → match
- **Name similarity:** normalize names first (lowercase; expand abbreviations such as Ctr → Center, Rehab → Rehabilitation; drop Inc/LLC/PC), then compare with rapidfuzz `token_sort_ratio`. Don't use `token_set_ratio`: it scores "NYU Langone" vs "NYU Langone Rehabilitation Center" as a perfect 100 and would merge different organizations.
- Individual doctors at the same location address + phone are grouped into one practice. If an organization record (NPI-2) exists at the same address + phone, the doctors are attached to it instead of creating a second practice.

### 11.5 Status transitions
| Event | New status |
|---|---|
| Lead first appears | untried |
| I mark it "Already called" | already_called (hidden by default) |
| First call logged | contacted |
| `meeting_set` or `referral_received` | active |
| `wrong_number` | bad_number |
| `not_interested` | not_a_fit |
| Every known contact and the front desk are Unreachable | unreachable |
| I log a new call on an already_called or unreachable lead | contacted |

The editable status dropdown (Section 12) only offers the manual statuses: untried, already_called, not_a_fit, bad_number.

### 11.6 Best time to call (Tiger Data)
Because every call attempt is timestamped, the app can learn **when** each organization actually picks up.
- A **continuous aggregate** rolls up call attempts into **1-hour buckets per organization** (`time_bucket('1 hour', timestamp)`): attempts and positive outcomes. Tiger keeps it up to date in the background.
- The "best time" query then groups that aggregate by **day of week and hour in New York time** (`America/New_York`) to get answer rates. Two reasons for this design: Tiger's continuous aggregates must group by a time bucket, not by "hour of day" directly; and timestamps are stored in UTC, so without converting, a 9 AM call would show up as 1 PM.
- Make sure a newly logged call shows up right away (real-time aggregation or a refresh after logging). Check Tiger's current docs for the default.
- The lead panel shows **"Best time to call"** (e.g., "Tue–Thu, 9–10 AM: 3 of 4 calls answered") and a small heat map of answer rate by day and hour.
- Across all leads, a summary shows answer rate by category and hour (e.g., "SNF discharge planners pick up most before 10 AM").
- Needs at least 3 attempts at an organization before showing a recommendation; otherwise shows "Not enough calls yet."
- On SQLite (tests/offline), the same numbers come from a plain query, so results match.

### 11.7 Web contact finder (Nimble + Gemini)
Fills the weakest part of the data: **decision-maker names, titles, and emails.** Runs **on demand** for one lead (a "Find contacts" button), never in bulk, to save trial credits.
1. **Find the website:** Nimble web search for the organization's name + address (NPI has no website field).
2. **Find the right pages:** Nimble site map lists the site's pages; keep likely ones (staff, team, leadership, about, contact, social work, admissions, case management).
3. **Get the text:** Nimble extract pulls clean text from up to 5 of those pages.
4. **Pull out contacts:** Gemini returns structured JSON: name, title, email, phone, source URL, and an **exact quote** from the page showing that contact.
5. **Evidence check (in code, not AI):** keep a contact only if its quote, name, and email actually appear in the page text. This blocks made-up names.
6. **Rank by role:** titles matching Section 1's decision-maker list (social work, discharge, case management, admissions, care management) are marked role `decision_maker`; others `other`.
7. **Save** as contacts with source `web`, the source URL, the quote, and `verified = false` until I confirm on a call. Cache results for 30 days.

Limits to be upfront about: many small practices list no staff online, and generic emails (info@) are common. The finder shows "No named contacts found" rather than guessing.

## 12. Screens (Streamlit)

**Search (main page)**
- Location input (ZIP / borough / neighborhood) + category filter
- Results table: Priority, Fit, Reachability label, organization, category, neighborhood, phone, primary contact name + title + role, email, attempts, last outcome
- **Primary contact** shown in the row: decision maker if known, otherwise registered official, otherwise the first clinician
- Phone and email as clickable `tel:` / `mailto:` links if Streamlit's link column supports them (verify in M6a); otherwise plain text in the table and clickable links in the lead panel
- **Editable Status column** (dropdown with manual statuses only: untried / already_called / not_a_fit / bad_number) for quick marking without opening the lead
- **Selecting a row opens the lead panel** beside or below the table (Streamlit tables don't support a separate button on every row)
- Toggles: show hidden statuses; "has decision maker only"

**Lead panel (opens on row selection)**
- Organization info, all contacts (with roles), call history
- **Add / edit contact** (name, title, role, phone, email)
- **Log call** form: contact (or front desk), channel, outcome buttons, optional short note — under 10 seconds to log
- **Find contacts** button (Section 11.7): shows found contacts with title, email, and a link to the source page, each with an "Add" button
- **Best time to call** (Section 11.6): recommendation + small heat map

**Data Refresh**
- Fetch/refresh NPI data by borough + category; shows counts and any capped queries

**Export**
- Download current results as CSV

## 13. Architecture

### Decision: Streamlit for the v1 UI
Right for a single-user internal tool built by one person. **Robustness comes from the architecture:** all logic lives in a plain Python package (`src/referral_finder/`) with no Streamlit imports; the UI only calls service functions. A different frontend can be added later without rewriting the core.

### Decision: Tiger Cloud Postgres as the database, no separate backend API
```
                    ┌──────────── Sentry (errors + tracing for everything below)
                    │
Streamlit UI  →  Python service layer (src/referral_finder/)  →  Tiger Cloud Postgres
                    │                                              (call_attempts = hypertable,
                    ├─→ NPI Registry API (organizations, phones)   continuous aggregate for
                    ├─→ Nimble (find org website + staff pages)    best time to call)
                    └─→ Gemini (extract named contacts from pages)
```
- **Tiger Cloud Postgres** stores all leads, contacts, and call history, so the data lives online and works from any device. Call attempts are time-series data, so they use Tiger's time-series features (Section 11.6).
- **The Python service layer is the backend.** It talks to Tiger Cloud directly as a Postgres database. No separate API server (e.g., FastAPI) in v1: for a single user it would double the work with no benefit. If other people or apps need access later, an API can be added on top of the same service layer.
- **One setting chooses the database:** `DATABASE_URL` in `.env`.
  - Tiger Cloud Postgres for real use
  - In-memory SQLite for tests (fast, no internet)
  - A local SQLite file as an offline fallback (e.g., if venue Wi-Fi fails during a demo)
- To make this work, all database code uses **SQLModel** (built on SQLAlchemy) and lives in `db.py`. The only Tiger-specific SQL (creating the hypertable and continuous aggregate) lives in one setup function that runs only on Tiger Cloud.

### Stack
| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Database | Tiger Cloud Postgres (Tiger Data trial); SQLite for tests and offline fallback |
| Database access | SQLModel (SQLAlchemy) + psycopg (Postgres driver) |
| Models / validation | Pydantic v2 (SQLModel models are Pydantic models) |
| HTTP | httpx |
| Fuzzy matching | rapidfuzz |
| Config | YAML (pyyaml) + `.env` (python-dotenv) |
| AI | google-genai (Gemini API): contact extraction, optional fit reasons |
| Web data | Nimble API (search, site map, extract) via httpx |
| Monitoring | sentry-sdk (errors, tracing, AI call monitoring) |
| UI | Streamlit |
| Tests / lint | pytest, ruff |

### Folder structure
```
referral-finder/
├── PROJECT_PLAN.md
├── CLAUDE.md
├── README.md
├── .env.example              # DATABASE_URL, GEMINI_API_KEY, NIMBLE_API_KEY, SENTRY_DSN (names only)
├── .gitignore                # .env, data/*.db, data/cache/, .streamlit/secrets.toml
├── pyproject.toml            # makes src/referral_finder installable (pip install -e .)
├── requirements.txt
├── config/
│   ├── service_area.yaml     # boroughs → ZIPs
│   ├── neighborhoods.yaml    # neighborhoods → ZIPs
│   └── scoring.yaml          # categories, fit weights, reachability rules, priority weights
├── data/
│   ├── referral_finder.db    # offline fallback only (not used with Tiger Cloud)
│   ├── demo_seed.json        # small demo dataset for the offline fallback
│   └── cache/
├── src/referral_finder/
│   ├── config.py
│   ├── models.py
│   ├── db.py                 # SQLModel engine from DATABASE_URL; all database code here
│   ├── cache.py
│   ├── normalize.py          # phone, ZIP, name, address
│   ├── locations.py          # ZIP / borough / neighborhood → ZIP set
│   ├── sources/
│   │   ├── base.py           # Source interface → list[Organization]
│   │   └── npi.py
│   ├── dedupe.py
│   ├── fit.py                # fit score
│   ├── reachability.py       # reachability score + labels from CallAttempts
│   ├── priority.py           # combines fit + reachability
│   ├── calls.py              # log attempts, status transitions
│   ├── llm.py                # Gemini wrapper (swappable)
│   ├── web.py                # Nimble wrapper: find website, list pages, extract text
│   ├── contact_finder.py     # Nimble + Gemini pipeline with evidence check (Section 11.7)
│   ├── monitoring.py         # Sentry setup (no personal data)
│   ├── export.py
│   └── services.py           # functions the UI calls
├── app.py                    # Search page + lead panel
├── pages/
│   ├── 1_Data_Refresh.py
│   └── 2_Export.py
├── scripts/
│   ├── smoke_test.py         # proves every service key works (run first)
│   ├── seed_demo_calls.py    # inserts flagged demo call history (is_demo = true)
│   ├── explore_npi.py        # live API exploration (dev only)
│   ├── record_fixtures.py    # saves real responses for tests
│   └── preview_leads.py      # prints top leads before the UI exists
└── tests/
    └── fixtures/             # saved NPI JSON for offline tests
```

## 14. Build milestones (for Claude Code)

Build **one milestone per session**. Start each session in **plan mode**: Claude Code proposes its plan, I approve it, then it builds. Each milestone must pass its check before moving on. Who checks what: 🤖 = Claude Code verifies with tests; 👤 = I verify by using the app.

| # | Milestone | Done when |
|---|---|---|
| M0 | Skeleton: folders, `pyproject.toml`, requirements, `.env.example`, `.gitignore`, README, CLAUDE.md, empty Streamlit app; package installed with `pip install -e .`; **Sentry initialized** (`monitoring.py`, PII off) | 🤖 `pytest` runs and can import `referral_finder` · 👤 `streamlit run app.py` opens in my browser, and a test error shows up in my Sentry dashboard |
| M1 | Config loading, SQLModel models, database setup from `DATABASE_URL` (Tiger Cloud or SQLite), repository functions; on Tiger Cloud, make `call_attempts` a hypertable. Read Tiger Data's current docs first. | 🤖 Tests create/read/update Organizations, Contacts, CallAttempts on in-memory SQLite · 👤 The app connects to Tiger Cloud and the tables (including the hypertable) appear in the Tiger console |
| M2a | NPI organizations: explore the live API and verify taxonomy terms + ZIP lists; category + ZIP-prefix queries, pagination, LOCATION address, normalization, service-area filter, disk cache; record fixtures | 🤖 Tests pass on fixtures · 👤 `scripts/preview_leads.py` lists Brooklyn SNFs and they look right |
| M2b | NPI individuals: doctor search, grouping into practices (attached to an existing NPI-2 record when one matches), clinicians saved as contacts, "Large institution" label, cap detection + automatic query splitting | 🤖 A Manhattan neurology query splits automatically; grouping tests pass |
| M3 | Location resolution (ZIP / borough / neighborhood), draft `neighborhoods.yaml`, dedupe | 🤖 Each search type returns the right ZIP set; partial names work; dedupe catches NPI, phone + address, and fuzzy-name matches, and does **not** merge "NYU Langone" with "NYU Langone Rehabilitation Center" · 👤 I review the neighborhood map |
| M4 | Fit score from `scoring.yaml` | 🤖 Changing weights changes ranking without code edits · 👤 `scripts/preview_leads.py` shows a top 20 for a test neighborhood that looks like real referral sources |
| M5 | Call logging + reachability score + labels + status transitions (Section 11.5) + priority | 🤖 New contact = Untried; first-call reach → 77 (Hot); 10 straight voicemails → Unreachable; a callback resets the streak; org reachability = best contact; wrong number → bad_number; recency weighting works |
| M6a | Search page: location + category inputs, results table, editable status column, filters, Data Refresh page | 👤 Refresh data → search a neighborhood → mark old calls "Already called" → they disappear |
| M6b | Lead panel: contacts, add/edit decision maker, log call, call history; Export page | 👤 Log a call → add the decision maker learned on it → ranking updates → export CSV |
| M7a | **Web contact finder** (Section 11.7): Nimble search → site map → extract; Gemini structured extraction; evidence check in code; save as web contacts; Sentry spans around each step | 🤖 Evidence check rejects a contact whose quote isn't in the page (fixture test); no call notes sent anywhere · 👤 "Find contacts" on a real SNF returns named staff with source links, or says none were found |
| M7b | **Best time to call** (Section 11.6): continuous aggregate on Tiger Cloud, equivalent query on SQLite, recommendation + heat map in the lead panel | 🤖 Tiger and SQLite give the same numbers on a test dataset · 👤 The lead panel shows a sensible best time for a lead with logged calls |
| M7c | *(Optional)* Gemini one-line fit reason for top results; batched, cached | 🤖 No notes or call history sent to the model · 👤 Reasons make sense |
| M8 | Hardening: error messages (NPI, Nimble, Gemini, or database unreachable), logging, offline fallback with `demo_seed.json`, README walkthrough (including CSV backups), tests for core logic | 🤖 NPI and database outages show a clear message · 👤 I can run it from the README alone, and switch to the offline fallback in under a minute |
| M9 | *(Optional)* Deploy to Streamlit Community Cloud as a **private app** shared only with my email; secrets in Streamlit's secrets settings | 👤 I open it from my phone and work computer; it's not viewable without signing in |

## 15. Engineering conventions

- Business logic in `src/referral_finder/`; no Streamlit imports there.
- Type hints everywhere; Pydantic models at every boundary.
- One responsibility per module; small, clearly named functions.
- No hard-coded ZIPs, weights, thresholds, or model names; use `config/`.
- Scoring functions are pure (data in, score out) so they're easy to test.
- Network calls: timeout, retry with backoff, disk cache.
- `logging`, not print. Tests use fixtures; no live API calls. (Live API calls are allowed only in an explicit exploration or fixture-recording script.)
- Check current documentation before using Streamlit, google-genai, Nimble, Tiger Data, or Sentry features; don't rely on memory for APIs that change.
- Small commits after each milestone.

## 16. Configuration example

`config/scoring.yaml` (shape only; values to tune)
```yaml
fit:
  categories:
    skilled_nursing:      { search_as: organization, weight: 35 }
    rehab:                { search_as: organization, weight: 35 }
    case_management:      { search_as: organization, weight: 35 }
    neurology:            { search_as: individual,   weight: 35 }
    geriatric_medicine:   { search_as: individual,   weight: 35 }
    geriatric_psychiatry: { search_as: individual,   weight: 35 }
    # ... remaining categories from Section 7
  signals:
    has_decision_maker: 25
    has_registered_contact: 10
    has_separate_contact_phone: 5
    has_email: 10
    per_clinician: 2
    clinician_cap: 10
    large_institution_threshold: 25   # groups this big get no size bonus

reachability:
  positive_outcomes: [reached_decision_maker, callback_received, email_replied, transferred, meeting_set, referral_received]
  first_call_bonus: 10
  unreachable_after_consecutive_misses: 10
  miss_outcomes: [voicemail_left, no_answer]
  recency_half_weight_days: 90
  labels: { hot: 70, warm: 40 }

priority:
  tried: { fit_weight: 0.4, reachability_weight: 0.6 }
```

## 17. Questions for the engineer review

- Is "Streamlit + Python service layer + Tiger Cloud Postgres" the right foundation, or will I need a separate API later?
- How should I handle schema changes once real data is in the database (migrations, e.g., Alembic)?
- Is the web contact finder's evidence check strong enough to trust the names it returns?
- Is the Source interface right for adding Google Places, Clay, Apollo later?
- Is the reachability formula sensible, or is there a better simple model?
- How should retries, rate limits, and caching be structured?
- Anything in the data model that will hurt later (e.g., organizations with multiple locations, contacts who change jobs)?

## 18. Open items

- [x] Service area: Brooklyn, Queens, Manhattan
- [ ] Claude subscription or Anthropic Console account for Claude Code
- [ ] Install Python 3.11+ and Git
- [ ] Create accounts and keys: Tiger Cloud service (`DATABASE_URL`), Gemini API key, Nimble trial key, Sentry trial project (DSN)
- [ ] When submitting: opt in to the Sentry category and list every prize track used
- [ ] Confirm with an organizer that solo submissions are allowed (the event page doesn't say explicitly)
- [ ] List the neighborhoods I search most, to seed `neighborhoods.yaml`
- [ ] Confirm the voicemail threshold (default: 10 in a row = Unreachable)
- [ ] Manager sign-off on using the tool at work

---

## Appendix A: Suggested `CLAUDE.md` (create in M0)

```markdown
# Referral Finder

Read PROJECT_PLAN.md before any work. It is the source of truth.

**Hackathon mode (October 11): Section 0 of PROJECT_PLAN.md overrides everything below.** Build the "lite" version in Section 0.4b. Tiger Cloud only (no SQLite support today). Write tests only for fit scoring and the contact finder's evidence check. When the hackathon is over, the owner will delete this paragraph.

- The ideal lead: a decision maker who handles referrals to long-term home care. Keep that in mind in every design choice.
- Work on one milestone at a time (Section 14). Propose a plan first; do not start the next milestone unless asked.
- Never ask the owner to paste API keys into the chat; they go in .env.
- Business logic goes in src/referral_finder/ with no Streamlit imports.
- No hard-coded ZIPs, weights, thresholds, or model names; use config/.
- All database code lives in db.py and uses SQLModel; no database-specific SQL. The app must work on both Tiger Cloud Postgres and SQLite via DATABASE_URL. Tiger-only SQL (hypertables, continuous aggregates) lives in one isolated setup function.
- Read Streamlit's, Tiger Data's, Nimble's, Sentry's, and google-genai's current docs before writing code that uses them.
- Store timestamps in UTC; show and group times in America/New_York.
- Contacts from the web finder must include the source URL and an evidence quote found in the page text; discard anything without it.
- Never send call notes, call history, or personal data to Sentry (send_default_pii off).
- Never send call notes or call history to an AI model.
- Tests use fixtures; no live API calls in tests.
- Explain what you changed and why in plain language; the owner is learning.
- Run tests and ruff before saying a milestone is done.
```
