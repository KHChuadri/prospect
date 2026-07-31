# Job Application Tracker API

A production-shaped REST API for tracking job applications — multi-user, JWT-authenticated, with per-user data ownership enforced at the database layer.

**Stack:** .NET 10, ASP.NET Core Web API, Entity Framework Core, Npgsql (PostgreSQL), xUnit + Testcontainers

---

## Setup

**Prerequisites:** Docker Desktop, .NET 10 SDK

```bash
# 1. Start the database
docker compose up -d

# 2. Apply migrations (auto-applied on startup; manual command if needed)
cd src/JobApplicationTracker
dotnet ef database update

# 3. Run the API
dotnet run

# 4. Open API docs
open http://localhost:5237/scalar/v1
```

Copy `.env.example` to `.env` and fill in production values before deploying.

---

## Design Decisions

### 1. Status enum + history table

`ApplicationStatus` is stored as an `int` (enum) on `JobApplication` for the current status. Every change also appends a row to `StatusTransitions` with `FromStatus`, `ToStatus`, and `TransitionedAt`. This makes "average time in stage" analytically tractable without full-table scans.

### 2. Global EF Core query filter for ownership

Every `JobApplication` query is automatically scoped to the caller's `UserId` via an EF Core global query filter in `AppDbContext.OnModelCreating`. The filter reads the current user ID from `ICurrentUserService`, which reads from the JWT claim. There is no per-controller ownership check — it's structurally impossible to forget.

Cross-user access returns `404`, not `403` — the filtered query makes the record invisible, so "not found" is accurate and avoids confirming that another user's record exists.

### 3. Dedicated status endpoint

`PATCH /api/applications/{id}/status` is separate from the general update endpoint. Reason: status changes have a side effect (writing `StatusTransition`) and require their own transition-validation logic (terminal state guard). Mixing this into a general PATCH would obscure the business rule.

---

## API Surface

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Register a new user |
| POST | `/api/auth/login` | Login and get tokens |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/revoke` | Revoke refresh token |
| GET | `/api/auth/me` | Current user info |
| GET | `/api/applications` | List applications (filter by `?status=`) |
| POST | `/api/applications` | Create application |
| GET | `/api/applications/{id}` | Get application |
| PATCH | `/api/applications/{id}` | Update application fields |
| DELETE | `/api/applications/{id}` | Delete application |
| PATCH | `/api/applications/{id}/status` | Transition status (writes history) |
| GET | `/api/applications/{id}/notes` | List notes |
| POST | `/api/applications/{id}/notes` | Add note |
| GET | `/api/analytics/summary` | Counts by status, apps per week, avg time in stage |

---

## Running Tests

Tests use real PostgreSQL via Testcontainers — Docker must be running.

```bash
dotnet test tests/JobApplicationTracker.Tests
```

Key test: `UserA_CannotAccess_UserB_Application` — verifies the global query filter actually prevents cross-user access (structural ownership, not just per-controller checks).

---

## Known Limitations / What I'd Do Next

- **No pagination** — `GET /api/applications` returns all records. Add `?page=&pageSize=` when the list grows.
- **Analytics computed in-process** — the aggregation loads all transitions into memory. Push to SQL GROUP BY for large datasets.
- **Refresh token is a plain DB column** — fine for single-instance but not safe under horizontal scale (race condition on rotation). A dedicated `RefreshTokens` table with revocation timestamps is the upgrade.
- **No rate limiting on auth endpoints** — `/api/auth/register` and `/api/auth/login` are open to credential-stuffing. Add `Microsoft.AspNetCore.RateLimiting` before going to production.
- **No stale-application detection** — a background job (`IHostedService`) flagging applications with no activity for N days would improve UX.
