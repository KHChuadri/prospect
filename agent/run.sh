#!/usr/bin/env bash
# Start the follow-up agent service (API + nightly scheduler).
# Env is auto-loaded from agent/.env by config.load_settings (python-dotenv),
# so no `source .env` needed. Activates .venv if present.
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] && source .venv/bin/activate
exec uvicorn followup_agent.main:app --reload --port 8000
