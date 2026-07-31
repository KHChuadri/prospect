# Event Crawler — Design

**Date:** 2026-07-31
**Status:** Approved for implementation planning

Prospect tracks job applications. This adds a crawler that finds upcoming
networking events, panel talks, and career events on the web, and surfaces them
in a review feed — highlighting any event where a company the user has applied
to will be present.

---

## 1. Scope

### v1 — this spec

1. **Crawl and extract.** Hybrid sources: a typed Eventbrite API client, plus a
   generic `fetch → clean → LLM extract` path for university and company pages.
2. **Store.** A global `events` table plus a per-user `user_events` decision table.
3. **Review feed.** An `/events` page: upcoming events, filterable, with
   *Register* / *Not interested* triage and a Saved tab.
4. **Company linking.** Events whose organizations intersect the user's tracked
   companies are highlighted, matched on normalized names.

### v2 — deferred

5. **Weekly digest email** — reuses `mailer.py` and APScheduler.
6. **Calendar export** — an `.ics` download endpoint.

Both are deferred because they are downstream of extraction quality. A digest of
poorly-extracted events just delivers noise faster. Ship v1, run it against real
sites for a week, then build these.

### v3 — site discovery

The v1 crawler reads a hand-configured list of sites. Note that it does already
discover *events* it was never told about: the Eventbrite source asks "what is
happening in Sydney?" rather than naming events. What it cannot do is find new
**sites**.

7. **Search-driven discovery.** A `type: search` source issues location and
   topic queries against a search API (Brave Search, Serper, or Google Custom
   Search — all have free tiers) and feeds each result URL through the existing
   generic path: fetch → clean → extract → four gates. One new `Source`
   implementation, no new pipeline.

   ```yaml
     - name: discover-sydney
       type: search
       queries:
         - "networking event Sydney {month} {year}"
         - "graduate careers panel Sydney {month}"
       max_results: 20
   ```

   Bounded by construction: 1 search call plus at most 20 fetches and 20 LLM
   calls per query per run. Run weekly rather than 12-hourly. Gates 1 and 4
   absorb the heavy overlap between runs.

8. **Human-approved site proposals.** A search result is a single page; a good
   site deserves recurring crawls of its whole listing. When a discovered page's
   domain is not already a configured source, it is written to a
   `discovered_sources` table rather than trusted. `/events` gains a small "New
   sources found" section: approve, and the domain joins the crawl list with a
   `link_pattern`; reject, and it is never proposed again.

   This follows the accept/reject idiom already used by `/recommendations` and
   the follow-up approval flow. It matters more here than elsewhere: an
   auto-added source means the crawler begins hitting a site nobody vetted,
   under the user's IP and User-Agent.

**Why v3 and not v1:** discovery multiplies whatever the extraction quality
happens to be. At 60% accuracy it yields more 60%-accurate results and a larger
mess to triage. Reach good extraction on three known sites first, then widen.

### Explicitly out of scope

- **LinkedIn Events.** Requires login, is aggressively anti-bot, and scraping it
  violates their Terms of Service with real account-ban risk. If LinkedIn events
  are wanted later, the legitimate path is subscribing to LinkedIn's event
  notification emails and parsing them through the **existing Gmail pipeline**.
- **True spidering** — following outbound links recursively to discover sites.
  Rejected, permanently, not deferred. Two reasons. **Cost without yield:** a
  page's nature cannot be known without reading it, and reading costs an LLM
  call; three hops from a university events page reaches tens of thousands of
  staff profiles, degree listings and news archives, and approximately zero
  additional events. **Crawler traps:** event calendars expose a "next month"
  link, which yields an infinite URL space that never errors and never
  terminates. Containing this requires frontier management, URL prioritisation
  and per-domain budgets — the problem Scrapy exists to solve, and far outside
  this feature's value. Search-driven discovery (v3) reaches the same goal by
  querying an index someone else already built.
- **Open-ended crawl depth.** The crawler follows links exactly one hop, from a
  configured listing page to event detail pages.

---

## 2. Approach

Extend the existing Python agent (`agent/`) rather than building a separate
crawler service.

**Rejected alternatives:**

| Option | Why not |
|---|---|
| Scrapy as its own service | A full crawling framework is overkill for ~10 known URLs, and adds a container and a set of concepts for capability we don't need. |
| TypeScript + Playwright service | Handles JS-rendered pages, but is the heaviest option to run and adds a third backend language to a repo already running .NET and Python. |
| Firecrawl (hosted scraping API) | Removes the fetch layer entirely, but costs money and removes the part most worth learning. Keep as an escape hatch. |

**Why extend the agent:** it already has APScheduler, an OpenAI-compatible LLM
client with structured output, JWT auth shared with the .NET backend, Postgres
access, and a Docker deployment. The recommendations pipeline
(`recommend_batch.py`) is the same shape as this feature — poll a source, dedup,
LLM-extract, dedup again, insert, user reviews in the UI.

**JS-rendered pages:** all fetching goes through one function, `fetch.get(url)`.
If a specific site turns out to require JavaScript, Playwright can be introduced
behind that function for that source alone, without touching the pipeline.
The primary source (UNSW) is server-rendered and does not need it.

---

## 3. Architecture

### 3.1 New code

```
agent/followup_agent/events/
  fetch.py      http_get(url) -> str            ← single swap point for Playwright
  clean.py      html_to_text(html) -> str       ← strip nav/script/footer
  extract.py    extract_event(text, url) -> EventExtract   ← LLM, structured output
  crawl.py      run_events_batch(...)           ← orchestration
  sources/
    eventbrite.py
    generic.py
agent/events_sources.yaml                       ← hand-edited site list
```

Modified: `models.py` (+`EventExtract`), `db.py` (+schema, CRUD), `api.py`
(+routes), `main.py` (+scheduled job), `config.py` (+settings),
`requirements.txt` (+`pyyaml`).

Client: `clients/prospect/src/app/(app)/events/`, following the existing
`/recommendations` page structure and shadcn Card idiom.

The `events/` subpackage is a deliberate departure from the flat module layout in
`followup_agent/`, which is already 13 files spanning three unrelated features.

### 3.2 The Source protocol

```python
Candidate = (uid: str, url: str, prefetched: EventExtract | None)

class Source(Protocol):
    name: str
    def discover(self) -> list[Candidate]: ...
```

| | `sources/eventbrite.py` | `sources/generic.py` |
|---|---|---|
| `discover()` returns | uid, url, **and the full event** | uid + url only |
| HTTP fetches | 1 API call for all events | 1 listing + 1 per new event |
| LLM calls | **zero** | 1 per new event |
| Fails when | the API contract changes | rarely — text extraction survives redesigns |

The `prefetched` field is the entire hybrid. One protocol, one loop.

### 3.3 Crawl depth: follow links

For generic sources the crawler reads the listing page, finds event links
matching `link_pattern`, and fetches each event's own detail page.

Listing-page-only extraction was considered and rejected: listing pages are built
to be scanned, so they carry title, date and venue but **not speakers**. Speaker
and host names are what populate `organizations[]`, which company linking depends
on. Listing-only extraction would silently disable the highest-value feature.

Cost is front-loaded, not recurring. The first crawl of a site with 15 events
costs 15 fetches and 15 LLM calls. Every crawl after that, Gate 1 recognises the
stored URLs and skips them before spending a fetch or a token, so a site posting
two new events a week costs two LLM calls a week.

### 3.4 Configuration

```yaml
sources:
  # Whole-university feed. Mostly concerts and exhibitions — the is_career_event
  # gate does the filtering. Verified server-rendered, robots.txt permits /event/*.
  - name: unsw-events
    type: generic
    url: https://www.events.unsw.edu.au/
    link_pattern: "/event/"
    timezone: Australia/Sydney

  - name: eventbrite
    type: eventbrite
    query: networking
    location: Sydney
```

Settings (`config.py`): `EVENTS_SOURCES_PATH`, `EVENTS_LOCATION` (`Sydney`),
`EVENTS_POLL_HOURS` (`12`), `EVENTS_USER_AGENT`, `EVENTBRITE_TOKEN`.

The crawler takes **no user id**. It writes only to the global `events` table
(§4); user identity enters solely through the JWT on the API side.

`EVENTBRITE_TOKEN` is the only new credential the feature requires. `LLM_API_KEY`,
`SMTP_*` and `GMAIL_*` are already configured and v1 does not touch the latter two.

### 3.5 Data flow

```
APScheduler (every EVENTS_POLL_HOURS, default 12)
  └→ crawl.run_events_batch(conn)
       for each source in events_sources.yaml:
         candidates = source.discover()
         for c in candidates:
           GATE 1  uid already stored?          → skip (before any fetch or token)
           ev = c.prefetched or extract(clean(fetch(c.url)), c.url)
           GATE 2  is_career_event?             → skip
           GATE 3  starts_at in the past?       → skip
           GATE 4  (title, date) seen this run? → skip
           db.create_event(...)
```

Gate 4's key is `(normalized_title, starts_at::date)`, where `normalized_title` is
lowercased with whitespace collapsed. Events with a null `starts_at` are exempt —
they cannot collide on a date and are left to the user to judge.

Gate 1 runs before any network or LLM cost, which is what makes re-crawling the
same listing every 12 hours nearly free. Gate 4 is cross-source: the same meetup
listed on both Eventbrite and a university page collapses to one row.

Gate 1 short-circuits the Eventbrite path and the generic detail-page path. The
generic listing page itself is fetched every crawl regardless, since its contents
cannot be known without reading it.

**There is no sync cursor.** Unlike `gmail_sync_state`, which exists because a
missed message window is gone forever, event listing pages show what is current.
The crawler re-reads the whole listing each run and lets Gate 1 absorb repeats.
An event that failed at 09:00 is retried at 21:00 with no bookkeeping.

---

## 4. Data model

```sql
-- The crawled fact. Global — one row per real-world event.
CREATE TABLE IF NOT EXISTS events (
    id            SERIAL PRIMARY KEY,
    source_name   TEXT NOT NULL,
    source_uid    TEXT NOT NULL,
    url           TEXT NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    starts_at     TIMESTAMPTZ,
    ends_at       TIMESTAMPTZ,
    location      TEXT,
    is_online     BOOLEAN NOT NULL DEFAULT false,
    organizations TEXT[] NOT NULL DEFAULT '{}',
    topics        TEXT[] NOT NULL DEFAULT '{}',
    event_type    TEXT,
    raw_snippet   TEXT NOT NULL DEFAULT '',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_name, source_uid)
);
CREATE INDEX IF NOT EXISTS events_starts_idx ON events (starts_at);

-- The user's opinion about it. Exists only once a decision is made.
CREATE TABLE IF NOT EXISTS user_events (
    user_id    INTEGER NOT NULL,
    event_id   INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    status     TEXT NOT NULL,            -- 'interested' | 'dismissed'
    decided_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, event_id)
);

CREATE TABLE IF NOT EXISTS events_crawl_state (
    source_name     TEXT PRIMARY KEY,
    last_crawled_at TIMESTAMPTZ NOT NULL,
    last_error      TEXT
);

-- Used by both the company match (§5) and its supporting index.
CREATE OR REPLACE FUNCTION normalize_company(name TEXT)
RETURNS TEXT LANGUAGE sql IMMUTABLE AS $$
    SELECT btrim(regexp_replace(
        regexp_replace(lower(name),
            '\s+(ltd|limited|inc|incorporated|plc|corp|corporation|pty|llc)\.?$', '', 'g'),
        '\s+', ' ', 'g'));
$$;
```

`event_type` is one of `networking`, `panel`, `career_fair`, `workshop`, `talk`,
`other`. Anything else the LLM returns is coerced to `other`.

`source_uid` is the source's own stable identifier: Eventbrite's event id for the
API source, and the canonical absolute detail-page URL for generic sources.

### 4.1 The LLM contract

`EventExtract` is the pydantic model the LLM must populate. It is the only
interface between model output and the pipeline:

```python
class EventExtract(BaseModel):
    is_career_event: bool          # Gate 2 — networking/panel/careers, not a concert
    title: str
    description: str = ""
    starts_at_local: str | None    # ISO-8601 *without* timezone, as printed on the page
    ends_at_local:   str | None
    location: str | None
    is_online: bool = False
    organizations: list[str] = []  # hosts and speakers' employers
    topics: list[str] = []
    event_type: str = "other"
```

The model returns **local** times as printed; the pipeline converts to UTC using
the source's declared `timezone` (§4, Timezone handling). `url` is deliberately
absent — it comes from the crawler, never the model (§7).

### Design decisions

**Events are global; opinions are per-user.** An event at UNSW is public — every
user would receive an identical copy. Putting `user_id` on `events` would mean
crawling the same page once per user and storing the same row once per user, and
would make the eventual move to multi-user a data migration. The split costs one
small table today, behaves identically for a single user, and makes multi-user a
non-event: new users start with an empty opinion set over the same event pool.

This differs deliberately from `recommendations`, which correctly carries
`user_id` on the row — Gmail messages are private, so a recommendation belongs to
exactly one person.

**No `'new'` status.** Absence of a `user_events` row means undecided. The
crawler writes to `events` only and never touches per-user data.

**`starts_at` is nullable.** Real pages say "early autumn" or give no date at
all. Forcing a timestamp means either dropping those events or inventing a date.
Null renders as a "Date TBC" pill and sorts last.

**`organizations[]` and `topics[]` are Postgres arrays, not lookup tables.** The
`&&` overlap operator serves both the company match and the keyword filter. A
join table is premature.

**Timezone handling.** Source pages print local times with no timezone
(`"Wednesday 13 August, 6:30pm"`). `starts_at` is `TIMESTAMPTZ`, an absolute
instant. Storing the naive time makes a 6:30pm Sydney event display as 4:30am the
next day, and AEDT/AEST shifts it again seasonally. Every source therefore
declares a `timezone` in the YAML, and extraction converts local → UTC using
`zoneinfo` (stdlib — no new dependency). **This is a required rule, not an
optimization:** it is silently wrong in production while appearing to work in
tests.

---

## 5. Filtering and company matching

**Filter at read time, never at crawl time.** The crawler captures every upcoming
career event it finds and records `location`, `is_online`, `topics[]` and
`starts_at`. `/events` does the filtering via query parameters. A bad filter can
therefore never silently lose an event, and changing keywords costs no re-crawl.

**Company matching is derived, never stored:**

```sql
SELECT e.*,
       ue.status,
       EXISTS (
         SELECT 1 FROM "JobApplications" ja
         WHERE ja."UserId" = :uid
           AND normalize_company(ja."Company") = ANY(
                 SELECT normalize_company(o) FROM unnest(e.organizations) o)
       ) AS company_match
  FROM events e
  LEFT JOIN user_events ue ON ue.event_id = e.id AND ue.user_id = :uid
 WHERE (ue.status IS DISTINCT FROM 'dismissed')
   AND (e.starts_at IS NULL OR e.starts_at >= now())
 ORDER BY e.starts_at NULLS LAST;
```

`normalize_company` is the immutable SQL function defined in §4 — it lowercases,
strips legal suffixes (`Ltd`, `Limited`, `Inc`, `plc`, `Corp`, `Pty`, `LLC`), and
collapses whitespace, so `Monzo Bank Ltd` matches `Monzo`. Without it the feature
silently under-fires. It lives in SQL rather than Python so the match runs inside
the query rather than pulling both lists into the API process.

`organizations` is a fact about the event — stored. `company_match` is a
relationship between two facts — derived. Computing it per request means an event
crawled last week lights up the moment the user adds an application to that
company, with nothing to backfill and no possibility of staleness.

**Expected hit rate is low and that is not a bug.** Many event pages name no
organizations at all. The feature is cheap (one SQL expression, one extra LLM
field) and high-value when it fires; empty highlights most weeks are the design
working correctly.

---

## 6. API and UI

### Endpoints (`api.py`, JWT-authenticated, same as existing routes)

| Method | Path | Description |
|---|---|---|
| GET | `/events` | Upcoming, undismissed events. Params: `online`, `location`, `topic`, `company_match`, `saved`. |
| POST | `/events/{id}/interested` | Upsert `user_events` status `interested`. |
| POST | `/events/{id}/dismiss` | Upsert `user_events` status `dismissed`. |
| DELETE | `/events/{id}/decision` | Undo — removes the `user_events` row. |

### `/events` page

Card per event, matching the `/recommendations` shadcn idiom. Each card shows
title, `event_type` badge, date line (or amber "Date TBC"), venue or Online pill,
organization and topic pills, description, and source attribution.

**Interaction model.** Prospect cannot take registrations — every event registers
on its own site. So:

- **Card body** → opens the source page in a new tab.
- **`Register ↗`** (primary) → marks `interested` **and** opens the source page.
  One click, both effects.
- **`Not interested`** → marks `dismissed`; the event stays out of the feed.
- **Undo** → deletes the decision row.

The primary button performs the primary action. An "Interested" button that only
flips a status column is a dead end — it leaves the user hunting for a small link
to do the thing they actually wanted.

Prospect records that the user *left to register*, never that they did. It cannot
observe what happens on Eventbrite, and claiming otherwise would make the data a
lie — hence "Interested", not "Registered".

`interested` events move to a **Saved tab**; the main feed stays an inbox that can
be emptied. Company-matched events are outlined and sorted to the top.

---

## 7. Failure handling

Two blast radii, following the rule already established in `batch.py`:

```
for source in sources:              ← one site down does not stop the others
    try: candidates = source.discover()
    except: write events_crawl_state.last_error; continue

    for c in candidates:            ← one bad event does not stop the rest
        try: fetch, extract, validate, insert
        except: log; continue
```

Source failures are recorded in `events_crawl_state` so they are visible rather
than silent. Individual event failures are logged and dropped, and retried
automatically on the next crawl by virtue of the stateless design (§3.5).

### LLM output is untrusted input

A crawled page is text written by a stranger, fed to a model.

**Malformed output** raises during pydantic validation, is logged, and the event
is skipped. **Well-formed nonsense** is caught by explicit validation:

- `title` must be non-empty
- `starts_at` must be within `[now, now + 18 months]`
- `event_type` must be in the allowed set, else coerced to `other`

**Prompt injection** — a page may contain instructions aimed at the model. Three
mitigations:

1. **Structured output.** The model can only populate a fixed pydantic schema.
   It cannot add fields, call tools, or execute anything. Worst case is a junk row.
2. **`url` never comes from the LLM.** It is the URL the crawler fetched. Otherwise
   a malicious page could inject a phishing link into the user's own feed, wearing
   the UI's trust.
3. **`raw_snippet` preserves the source text**, so anything suspicious is auditable.

---

## 8. Crawl politeness

| Rule | Implementation |
|---|---|
| Respect `robots.txt` | `urllib.robotparser` (stdlib), fetched once per host per crawl. Verified: UNSW permits `/event/*` and sets no `Crawl-delay`. |
| Identify honestly | `EVENTS_USER_AGENT`, defaulting to `Prospect-EventCrawler/1.0 (+https://github.com/KHChuadri/Prospect)`. Must name the project and carry a reachable contact URL. Never a spoofed browser string. |
| Serialize per host | One request at a time, ~2s apart. 15 detail pages ≈ 30s, irrelevant for a twice-daily job. |
| Timeouts | 10s connect, 10s read, so a hanging server cannot wedge the crawl. |
| Cap pages per source | Max 25 detail fetches per source per crawl, **and log when the cap is hit** so a truncated crawl never looks complete. |

Three sites twice a day is roughly 40 requests — negligible load. These rules cost
nothing and are the difference between a crawler that is welcome and one that gets
the user's IP range blocked.

Conditional requests (`If-Modified-Since` / `ETag`) were considered and deferred
as premature.

---

## 9. Testing

Live sites cannot be asserted against — they change, they go down, and hitting
them from CI contradicts §8. Three layers, mirroring `agent/tests/`:

**1. Pure logic, no I/O.** Highest value per line:

```python
normalize_company("Monzo Bank Ltd") == "monzo"
to_utc("13 Aug 6:30pm", "Australia/Sydney") == 2026-08-13T08:30Z
gate_past(starts_at=yesterday) is False
dedup_key("Fintech Panel", d) == dedup_key("  fintech  panel ", d)
```

**2. Fixture tests.** One real UNSW page saved to
`tests/fixtures/unsw-events.html`. Tests link discovery and HTML cleaning against
it — deterministic and offline. This mirrors `test_gmail_parse.py`, which already
tests saved Gmail payloads.

**3. Fake-injected pipeline tests.** `run_events_batch` takes `fetch_fn` and
`extract_fn` as parameters, exactly as `run_reco_batch` takes `gmail_fn` /
`extract_fn`. All four gates, cross-source dedup, and error isolation are tested
with no network and no LLM. Required case:

```python
def test_one_failing_source_does_not_stop_the_others(): ...
```

**Deliberately not automated:** whether the LLM extracts *well* from a real page.
That is evaluation, not unit testing, and automating it produces a green suite
that proves nothing. The tools are a `crawl_now.py` script (mirroring
`draft_now.py`) that runs one source live and prints what came back, plus a single
smoke test marked `@pytest.mark.live` and skipped by default.

---

## 10. Known limitations

- **UNSW's feed is university-wide**, not careers-specific. Of ~17 events on the
  front page roughly one is career-relevant; the rest are concerts, exhibitions
  and public lectures. Gate 2 does substantial real work here. Worth checking at
  implementation time whether UNSW publishes a careers-specific feed.
- **No JS rendering.** A source that renders events client-side returns nothing.
  Mitigated by the `fetch.get` swap point, not solved.
- **Company match hit rate will be low** (§5).
- **Single-worker constraint inherited** from the existing agent — the crawl job
  runs in-process on APScheduler, so the agent must continue to run with one
  uvicorn worker, as documented in `ARCHITECTURE.md`.
- **`link_pattern` is per-site and manual.** A site restructuring its URLs
  silently yields zero events until the pattern is updated; `events_crawl_state`
  makes this visible but nothing alerts on it.

---

## 11. Prerequisites

| Item | Status |
|---|---|
| `EVENTBRITE_TOKEN` | **Required** — free, from eventbrite.com/platform. The only new credential for v1. |
| Search API key | Not needed for v1. Required only if v3 site discovery (§1) is built. |
| `LLM_API_KEY` | Already configured (OpenRouter). |
| `pyyaml` | New dependency, one line in `requirements.txt`. |
| `.superpowers/` in `.gitignore` | Not yet present at repo root. |
