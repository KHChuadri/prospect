# Single-container build: .NET API + Python agent + Next.js frontend behind Caddy.
# Postgres is NOT in here — it runs as its own container (see docker-compose.yml).

# ---------- backend build ----------
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS backend-build
WORKDIR /src
COPY prospect-backend/JobApplicationTracker.slnx ./
COPY prospect-backend/src/JobApplicationTracker/JobApplicationTracker.csproj src/JobApplicationTracker/
RUN dotnet restore src/JobApplicationTracker/JobApplicationTracker.csproj
COPY prospect-backend/ ./
RUN dotnet publish src/JobApplicationTracker -c Release -o /app/publish

# ---------- frontend build ----------
FROM node:22-slim AS frontend-build
WORKDIR /app
RUN npm install -g pnpm@10
COPY clients/prospect/package.json clients/prospect/pnpm-lock.yaml clients/prospect/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY clients/prospect/ ./
# Baked into the JS bundle at build time. Relative paths keep the image
# portable across environments — Caddy resolves them to the right process.
ARG NEXT_PUBLIC_API_URL=/api
ARG NEXT_PUBLIC_AGENT_URL=/agent
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_AGENT_URL=$NEXT_PUBLIC_AGENT_URL
RUN pnpm build

# ---------- runtime ----------
FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl gnupg python3 python3-venv supervisor \
 && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

# Caddy is a static Go binary, so copying it across distros is safe.
COPY --from=caddy:2-alpine /usr/bin/caddy /usr/local/bin/caddy

COPY agent/requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

COPY --from=backend-build /app/publish /app/backend
COPY --from=frontend-build /app/.next/standalone /app/web
COPY --from=frontend-build /app/.next/static /app/web/.next/static
COPY --from=frontend-build /app/public /app/web/public
COPY agent/followup_agent /app/agent/followup_agent

COPY Caddyfile /etc/caddy/Caddyfile
COPY supervisord.conf /etc/supervisor/supervisord.conf

# Only Caddy binds a public interface; the three app processes stay on loopback.
ENV ASPNETCORE_ENVIRONMENT=Production \
    ASPNETCORE_URLS=http://127.0.0.1:5000 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

EXPOSE 8080
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
