# Follow-Up Agent — Architecture

The follow-up agent watches job applications that have sat in an early status
(Applied / Screening) past a threshold, uses an LLM to draft a polite
follow-up email, parks it for **human approval** in the web UI, and sends it
over SMTP once approved. It shares the Postgres database and JWT identity with
the ASP.NET backend.

## System diagram

```
                          ┌──────────────────────────────────────┐
                          │      Postgres (shared)               │
                          │  "JobApplications" (owned by .NET)   │
                          │  follow_ups        (owned by agent)  │
                          │  langgraph checkpoints (threads)     │
                          └──────────────────────────────────────┘
                             ▲ read apps      ▲ read/write       ▲ state
                             │                │                  │
   ┌─────────────┐   JWT     │     ┌──────────┴───────────────────────────┐
   │ ASP.NET API │──issues──▶ │     │            Follow-Up Agent (main.py)  │
   │ (JobAppTrkr)│  (HS256)   │     │                                       │
   └─────────────┘            │     │  ┌─────────────┐   ┌───────────────┐  │
         ▲                    │     │  │ APScheduler │   │  FastAPI (api)│  │
         │                    │     │  │ cron 09:00  │   │ /follow-ups   │  │
   ┌─────┴────────┐           │     │  └──────┬──────┘   │ /approve      │  │
   │ Next.js client│──Bearer──┼─────┼────────┼──────────│ /reject       │  │
   │ (job-tracker) │   JWT     │     │       │  batch.py └──────┬────────┘  │
   │  /follow-ups  │◀──────────┘     │       ▼                  │ resume    │
   └──────────────┘                 │  rules.eligible_apps      │           │
                                    │       │                   ▼           │
                                    │       ▼     ┌─────────────────────┐   │
                                    │  ┌──────────┤  LangGraph (graph)  │   │
                                    │  │  assess  │  START→assess       │   │
                                    │  │  (LLM)   │   ↓ warranted?      │   │
                                    │  └────┬─────┤  human_review       │   │
                                    │       │     │  (interrupt) ──────┐│   │
                                    │       ▼     │   ↓ approve?       ││   │
                                    │  llm.py     │  send ─────────────┘│   │
                                    │  ChatOpenAI │  (mailer SMTP)      │   │
                                    │  (OpenAI-   └─────────────────────┘   │
                                    │   compat)                            │
                                    └──────────────────────────────────────┘
```

## Components

| Module        | Responsibility |
|---------------|----------------|
| `main.py`     | Process entrypoint. Wires Postgres checkpointer, builds the graph, mounts FastAPI, starts the nightly scheduler. |
| `config.py`   | Loads `Settings` from `agent/.env` (auto-loaded at import). Provider-agnostic LLM config. |
| `scheduler.py`| Registers the nightly cron job (09:00). |
| `batch.py`    | Per-run: fetch candidate apps, filter via `rules`, invoke the graph per eligible app, persist drafts. Resilient — one flaky LLM call is logged and skipped, batch continues. |
| `rules.py`    | Pure eligibility logic: status in {Applied, Screening}, age ≥ N days, no existing follow-up. |
| `graph.py`    | LangGraph state machine: `assess → human_review (interrupt) → send`. Side effects injected via `assess_fn` / `send_fn`. |
| `llm.py`      | `assess_and_draft` — OpenAI-compatible chat with structured output (`Draft`). |
| `models.py`   | `AppRow`, `Draft` (pydantic), `FollowUpState` (LangGraph TypedDict). |
| `db.py`       | Schema + all SQL. Every query scoped by `user_id`. |
| `api.py`      | FastAPI: `GET /follow-ups`, `POST /approve`, `POST /reject`. JWT-authenticated. |
| `auth.py`     | Verifies the .NET-issued JWT (HS256, shared key, `nameidentifier` claim → user id). |
| `mailer.py`   | SMTP send. |

## Flow

1. **Nightly (09:00)** — `batch.run_batch` reads `"JobApplications"`, filters with
   `rules.eligible_apps`, and for each eligible app calls `graph.invoke`.
2. **assess** node calls the LLM. If `warranted` is false, the graph ends and
   nothing is persisted.
3. If warranted, a `follow_ups` row is written as `pending` and the graph parks
   at the `human_review` **interrupt** (state checkpointed in Postgres).
4. **User** lists pending items (`GET /follow-ups`) and approves
   (`POST /approve`). The endpoint resumes the parked graph with
   `Command(resume=...)`; the **send** node emails via SMTP; row → `sent`.
   Reject resumes with a reject decision; row → `rejected`.

Each app gets a stable LangGraph `thread_id` (`followup-{app_id}-{YYYYMMDD}`),
so its drafting + approval is one durable, resumable conversation.

## Cross-cutting design notes

- **Identity is shared, not duplicated.** The agent verifies the same JWT the
  .NET backend issues; there is no second user store. All DB access is scoped
  by the `user_id` extracted from the token.
- **Human-in-the-loop is durable.** State lives in the Postgres checkpointer, so
  a pending follow-up survives a process restart and can be approved later.
- **LLM provider is swappable.** `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`
  point the OpenAI-compatible client at OpenRouter, Groq, Gemini, etc. with no
  code change.

## Concurrency model & constraints

- **All `graph.invoke` calls are serialized behind one process-wide lock**
  (`_SerializedGraph` in `main.py`). The nightly batch runs on an APScheduler
  background thread while uvicorn serves approve/reject on its own threads, and
  all of them share the single `PostgresSaver` checkpointer connection, which is
  not thread-safe. The lock guarantees only one invoke touches that connection
  at a time. *Upgrade path: a `PostgresSaver` connection pool if invoke
  contention ever limits throughput.*
- **Approve is race-safe.** `POST /approve` reads the row `FOR UPDATE`, holding a
  row lock for the whole transaction. A second concurrent approve for the same
  follow-up blocks, then reads `status='sent'` and returns `409` — no double
  send.
- **Run a single worker.** APScheduler runs in-process and the graph/checkpointer
  live in memory, so the agent must run with **one** uvicorn worker. Multiple
  workers would start multiple schedulers (duplicate nightly runs) and split
  state. To scale out, move the nightly trigger to an external cron driving
  `draft_now.py` and run the API stateless.
