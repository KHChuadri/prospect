# What the job crawler changed

**PR:** [#11](https://github.com/KHChuadri/prospect/pull/11) · `feat/job-crawler`
**Baseline:** `main` at `23bb0de` · **26 commits** · 31 files, +2733 / −68

A delta document: what the system did before, what it does now, and which
existing behaviour moved. For *why* it is built this way, read
[`ARCHITECTURE.md`](../ARCHITECTURE.md) §5 and
[`AGENTS-ONBOARDING.md`](../AGENTS-ONBOARDING.md) §7.

> **On the PR's commit count.** GitHub shows 27 commits, one more than the 26
> here, because `origin/main` is a commit behind local `main` and `23bb0de`
> rides along in the diff. That commit is the AGENTS-ONBOARDING guide and is not
> part of this change. Push `main` before reviewing for a clean diff.

---

## 1. At a glance

| | Before | After |
|---|---|---|
| Background agents | 3 | 4 |
| Sources of a recommendation | Gmail alert emails | Gmail alert emails **+ job boards** |
| Scheduled jobs | nightly 09:00, 15 min, 12 h | + a second 12 h job |
| Database tables | — | **unchanged** |
| EF migrations | — | **none added** |
| Agent env vars | — | **+5** (`JOBS_*`) |
| Config files in `agent/` | `events_sources.yaml` | + `job_sources.yaml` |
| Agent tests | 188 passed / 34 skipped, 29 files | 294 passed / 37 skipped, 38 files |
| LLM calls per crawl | 1 per page | **0** |

---

## 2. The new capability

Every 12 hours the agent searches configured job boards and writes what it finds
into the existing `recommendations` table. Postings appear on the existing
Recommendations page as the same accept/dismiss cards, and accepting one creates
a `JobApplication` exactly as before.

Three source types ship: **LinkedIn** (public `jobs-guest` endpoints),
**Greenhouse** and **Lever** (documented JSON board APIs).

No LLM is involved. All three sources return structured data, so there is
nothing to extract and no prompt to inject into.

---

## 3. What was added

```
agent/
├── crawl_jobs_now.py                    NEW  run one crawl by hand
├── job_sources.yaml                     NEW  which searches and boards to visit
└── followup_agent/jobs/                 NEW  the whole package
    ├── crawl.py                              four-gate driver (96 lines)
    └── sources/
        ├── __init__.py                       JobPosting, YAML loader, factory
        ├── linkedin.py                       the robots.txt exception (361 lines)
        ├── greenhouse.py                     JSON board API, via Fetcher
        └── lever.py                          JSON board API, via Fetcher
```

Plus nine test files (`agent/tests/test_jobs_*.py`).

---

## 4. What changed in code that already existed

This is the part worth reviewing closely — everything above is additive and
cannot regress anything.

### 4.1 `db.existing_message_ids` was renamed

The crawler needed a "which recommendation keys are already stored" lookup for
Gate 1. It initially shipped its own, byte-identical to the existing function.
Rather than keep two, the **existing** one was renamed and the duplicate deleted:

```diff
-def existing_message_ids(conn) -> set[str]:
+def existing_source_message_ids(conn) -> set[str]:
+    """Gate 1's lookup — every recommendation key already stored.
+
+    Deliberately unfiltered by status: a dismissed posting must stay dismissed,
+    and filtering to 'pending' here would re-insert everything the user has
+    already rejected on the next crawl.
+    """
```

**Behaviour is identical** — same query, same return value. Only the name and a
docstring changed.

Call sites updated: `recommend_batch.py:19`, `tests/test_reco_db.py`,
`tests/test_recommend_batch.py`.

> If you have a branch that calls `db.existing_message_ids`, this is the one
> rename you need to apply. Nothing else in the public surface of `db.py` moved.

### 4.2 The Recommendations page shows its source as a badge

`clients/prospect/src/app/(app)/recommendations/page.tsx`:

```diff
-  Jobs parsed from your email alerts. Accept to add to your board, or dismiss.
+  Jobs from your email alerts and the job crawler. Accept to add to your
+  board, or dismiss.

-  <div className="text-sm text-muted-foreground">
-    {rec.location && <span>{rec.location} · </span>}
-    <span>from {rec.source_sender}</span>
+  <div className="flex items-center gap-2 text-sm text-muted-foreground">
+    {rec.location && <span>{rec.location}</span>}
+    <Badge variant="secondary">{rec.source_sender}</Badge>
```

Why: with two very different provenances feeding one list, "where did this come
from" stopped being incidental. The `·` separator gave way to a flex gap.

**This changes how Gmail-sourced recommendations render too.** Their
`source_sender` is the alert sender's address, which now sits in a badge rather
than after the words "from". No data changed, only presentation.

`source_sender` for crawler rows carries a **display name**
(`Greenhouse · Databricks`, `LinkedIn`), never the YAML identifier — the
frontend copies that field into the created `JobApplication.source`
permanently, so a config identifier there would be recorded on the board
forever and renaming a search would orphan its history.

### 4.3 `main.py` — a fourth job, and two subtleties

```diff
+_jobs_fetcher = Fetcher(settings.jobs_user_agent)
+_linkedin_client = LinkedInClient(max_requests=settings.jobs_max_requests_per_run)
+
+def _jobs_job():
+    ...
+
 scheduler.start_hours(_sched, _events_job, settings.events_poll_hours)
+scheduler.start_hours(_sched, _jobs_job, settings.jobs_poll_hours)
```

Two decisions that look redundant and are not:

- **A second `Fetcher`, not a reused one.** `_fetcher` announces
  `Prospect-EventCrawler`. A user-agent that misdescribes what it is doing is
  not an honest user-agent, so the job crawler announces its own.
- **`_linkedin_client` is module-level.** Its request budget resets per run via
  `begin_run()`, but the circuit breaker's cooldown counter must *survive*
  between runs — that is the entire point of a breaker that skips the next N
  runs. Construct it inside `_jobs_job` and the breaker silently never trips.

`_jobs_job` follows `_reco_job` and `_events_job`: broad `except`, rollback,
close. It does **not** follow `_nightly_job`, which still has no `except`
(main.py:67) — a pre-existing asymmetry this PR did not touch.

### 4.4 `config.py` — five settings

Documented in full in §5 below.

### 4.5 `scheduler.py` — unchanged

`start_hours` already existed for the event crawler and is reused as-is. The PR
adds a test for it (`tests/test_scheduler.py`) that was missing before.

---

## 5. New configuration surface

Five environment variables, all optional with working defaults. See
[`agent/.env.example`](../../agent/.env.example).

| Variable | Default | Reaches |
|---|---|---|
| `JOBS_POLL_HOURS` | `12` | scheduler |
| `JOBS_SOURCES_PATH` | `agent/job_sources.yaml` | loader |
| `JOBS_USER_AGENT` | `Prospect-JobCrawler/1.0 (+…)` | **Greenhouse and Lever only** |
| `JOBS_MAX_PER_SOURCE` | `25` | **Greenhouse and Lever only** |
| `JOBS_MAX_REQUESTS_PER_RUN` | `10` | **LinkedIn only** |

Two of these mislead if read at face value, so both are commented in
`config.py`:

- `JOBS_MAX_PER_SOURCE` does **not** get you more LinkedIn results. Each
  LinkedIn source deliberately fetches one page — 10 results — per run, so a cap
  of 25 is unreachable there. It governs the two board APIs.
- `JOBS_MAX_REQUESTS_PER_RUN` is a **soft** cap: checked once on entry to
  `get()`, incremented per network *attempt*. A call that starts under budget
  can still spend its full retry ladder, so the worst case at 10 is roughly 16
  attempts, not 10.

**New file: `agent/job_sources.yaml`.** A `sources:` list; each entry needs
`name` and `type`, then `query` + `location` (LinkedIn) or `slug` (Greenhouse,
Lever). `enabled: false` sits a source out. Unknown types and missing keys raise
at load with the key named, rather than as an `AttributeError` mid-crawl.

Ships with two LinkedIn searches and two real boards (`databricks`,
`palantir`) enabled, so a fresh checkout does not exercise the ToS-violating
source alone.

---

## 6. Database: nothing changed

Worth stating explicitly, because a feature this size normally implies a
migration:

```
$ git diff --stat 23bb0de..HEAD -- prospect-backend/
$
```

No new table, no new column, no EF migration. A posting is a `recommendations`
row keyed by a namespaced `source_message_id` (`linkedin:4426311357`) — a column
that already carried the UNIQUE constraint an idempotent write needs.

The cost of that reuse, and it is a real one: **location and posting date are
folded into `raw_snippet`** because no column exists for them. Fine for display,
useless for sorting or filtering. Adding the column is the right move the moment
either is needed — not before.

---

## 7. Tests

| | Before | After |
|---|---|---|
| Passed | 188 | 294 |
| Skipped | 34 | 37 |
| Files | 29 | 38 |

The three new skips are `test_jobs_db.py`, which needs a live Postgres.

**A skipped test is not a passing test.** Those three are the only check that
`ON CONFLICT (source_message_id)` matches a real unique index on that column
alone — otherwise confirmed only by reading `AgentTablesConfiguration.cs`. If
the assumption is wrong, every crawl insert raises and the run logs one line
with zero rows written. They have never executed.

```
docker compose up -d postgres
cd prospect-backend/src/JobApplicationTracker && dotnet ef database update
cd ../../../agent && python3 -m pytest tests/ -q
```

Frontend: three tests added to `RecommendationsPage.test.tsx` asserting the
badge renders as real markup. Not run on this branch.

---

## 8. Documentation

| File | Change |
|---|---|
| `docs/AGENTS-ONBOARDING.md` | New §7 on agent 4. §7–13 renumbered to §8–14. Counts and line references corrected throughout. |
| `docs/ARCHITECTURE.md` | New §5. Old §5–6 renumbered to §6–7. Robots.txt exception row, two known limits, job boards in the system diagram. |
| `agent/ARCHITECTURE.md` | New job crawler module table and design notes. |
| `README.md` | New "Running the job crawler" section with the ToS warning. Agent count corrected. |

Both architecture docs previously undercounted the agents by omitting the Gmail
poller ("two autonomous agents"). Since those sentences were being edited
anyway, they now say four and the README matches.

---

## 9. The risk this PR takes on

**The LinkedIn source violates robots.txt and LinkedIn's Terms of Service.**
LinkedIn's `robots.txt` is `Disallow: /` for every user-agent. This is the only
code in the repo that fetches a disallowed path, confined to
`jobs/sources/linkedin.py` — one file to audit, one file to delete. Greenhouse
and Lever carry no such exception and go through `Fetcher` unchanged.

Compensating rails, none of which make it permitted:

| Rail | Behaviour |
|---|---|
| Request budget | `JOBS_MAX_REQUESTS_PER_RUN`, default 10, soft (see §5) |
| Spacing | 2s between requests |
| Backoff | 0.5s → 8s jittered, 6 retries, on 429/5xx incl. LinkedIn's 999 |
| Circuit breaker | Skip 1 run, then 2, 4, 8, capped at 16 — on an exhausted ladder *or* a non-retryable 4xx such as 403. A transport error is not a refusal. |

**To disable it:** set `enabled: false` on the LinkedIn entries in
`job_sources.yaml`. The rest of the crawler keeps working.

---

## 10. Known gaps

- **Single user.** Searches are deployment-wide YAML feeding one `RECO_USER_ID`,
  reusing agent 2's setting. The multi-user path — a global `job_postings` table
  with per-user opinions in `user_job_postings`, mirroring `events`/`user_events`
  — is written up in the design spec.
- **LinkedIn markup rot is detectable, not preventable.** The source parses HTML
  with regex. A 200 with a real body yielding zero cards is logged as a *parse
  failure* rather than as zero results, so breakage is visible — but only if
  someone reads the log.
- **No source has hit a live endpoint.** `crawl_jobs_now.py` has never run.
- **Open decision, deliberately not taken:** an empty `enabled:` value parses as
  `None` and leaves the source **enabled**. Given that toggle is the documented
  way to switch off the LinkedIn source, failing closed may be the better
  default. One line in `_is_disabled` plus a test.
