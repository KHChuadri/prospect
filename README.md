# Prospect

A job-application tracker with two agents attached: one drafts follow-up emails for
applications that have gone quiet, the other crawls the web for networking events,
panels and careers fairs and flags the ones where a company you've applied to will
be present.

- **`prospect-backend/`** — .NET 10 API. CRUD, auth, and **owner of every database table**.
- **`agent/`** — Python agent. FastAPI + APScheduler + LangGraph. Follow-up drafting and the event crawler.
- **`clients/prospect/`** — Next.js 16 frontend.

Architecture and design rationale: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Prerequisites

| | |
|---|---|
| Docker Desktop | Postgres, and the all-in-one image |
| .NET 10 SDK | backend + migrations (`dotnet tool install --global dotnet-ef`) |
| Python 3.9+ | the agent |
| Node 20+ and pnpm | the frontend |

You also need an **LLM API key**. The agent talks to any OpenAI-compatible endpoint —
Groq and Google Gemini both have usable free tiers, and `agent/.env.example` has
ready-made settings for OpenRouter, Groq and Gemini.

---

## Option A — everything in one container

Fastest way to see the whole app running.

```bash
# Put your key somewhere compose can read it. This file is gitignored.
cat > .env <<'EOF'
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=gsk_your_key_here
LLM_MODEL=llama-3.3-70b-versatile
JWT_SECRET=any-string-at-least-32-characters-long
EOF

docker compose up --build
```

Open **http://localhost:8080** and register an account.

Caddy fronts everything: `/api/*` to the backend, `/agent/*` to the agent, the rest to
Next.js. The backend applies EF migrations on startup, so the schema is created for you.

---

## Option B — local development

Four processes. Each in its own terminal.

### 1. Database

```bash
docker compose up -d postgres
```

### 2. Migrations

**Required.** The agent does not create its own tables — EF Core owns the whole schema,
including the agent's. Skipping this makes the agent start and then fail at query time.

```bash
cd prospect-backend/src/JobApplicationTracker
dotnet ef database update
```

### 3. Backend → http://localhost:5135

```bash
cd prospect-backend/src/JobApplicationTracker
dotnet run
```

API reference at http://localhost:5135/scalar/v1 (development builds only).

### 4. Agent → http://localhost:8000

```bash
cd agent
cp .env.example .env          # then put your real LLM key in it
pip install -r requirements.txt
./run.sh
```

`agent/.env` is loaded automatically — no `source` needed. At minimum set `DATABASE_URL`,
`JWT_SIGNING_KEY` and the `LLM_*` values. `JWT_SIGNING_KEY` must match the backend's
`JwtSettings__SecretKey`, or the agent will reject every token the backend issues.

### 5. Frontend → http://localhost:3000

```bash
cd clients/prospect
pnpm install
pnpm dev
```

The default API and agent URLs already point at ports 5135 and 8000, so no config needed.

---

## Running the event crawler

The scheduler crawls every 12 hours once the agent is up. To crawl **right now** and read
the results — which is how you judge whether extraction is any good — you only need the
database and a key. The backend and frontend can stay down.

```bash
cd agent
python3 crawl_now.py                # every configured source
python3 crawl_now.py unsw-events    # just one
```

It prints each event it stores with title, time, venue, organisations and URL.

**Expect most candidates to be rejected.** The UNSW feed is mostly concerts, exhibitions
and public lectures, and the `is_career_event` gate is supposed to throw those out. What
to check in the output:

- titles look like real events, not nav text or cookie banners
- `starts_at` is plausible — Sydney evening events land around 08:00–10:00 UTC
- `orgs` is populated on pages that name speakers or sponsors

Sites are configured in [`agent/events_sources.yaml`](agent/events_sources.yaml). Adding a
source needs a name, a listing URL, a link pattern and a timezone.

`EVENTBRITE_TOKEN` is optional and free from eventbrite.com/platform. Left blank, the
Eventbrite source skips itself and the HTML sources still run.

---

## Tests

```bash
cd agent && python3 -m pytest              # 168 tests; needs a migrated database
cd prospect-backend && dotnet test         # 14 tests
cd clients/prospect && pnpm test           # 34 tests
```

The Python suite skips its database tests with a hint if the database isn't migrated.

---

## Ports

| Service | Local | In the container |
|---|---|---|
| Frontend | 3000 | 8080 (via Caddy) |
| Backend | 5135 | 8080`/api` |
| Agent | 8000 | 8080`/agent` |
| Postgres | 5432 | 5432 |

---

## Things that will bite you

- **Run the agent with one worker.** APScheduler runs in-process and the LangGraph
  checkpointer is in memory. A second uvicorn worker means duplicate nightly runs and
  duplicate crawls.
- **Migrations are not optional.** See step 2 above.
- **`JWT_SIGNING_KEY` and `JwtSettings__SecretKey` must match.** The compose file feeds
  both from one variable so they cannot drift; running locally, you set them yourself.
- **Free LLM tiers rate-limit.** OpenRouter's free models in particular are flaky. A
  failed extraction is skipped and retried on the next crawl rather than lost, but a
  crawl against a rate-limited endpoint will store very little.
- **Never commit `.env`.** Both the root one and `agent/.env` are gitignored;
  `agent/.env.example` is the tracked template.
