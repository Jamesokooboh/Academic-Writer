# Deployment Guide

## Docker Compose (local / single-host)

```bash
cp backend/.env.example backend/.env
# edit backend/.env — see "Secrets" below
docker compose up --build
```

This starts two services:

- **backend** — FastAPI + Uvicorn on `:8000`. Runs `alembic upgrade head` automatically on
  container start, then serves the API. The SQLite database file and the
  `sentence-transformers` model cache both live in named Docker volumes
  (`backend_data`, `hf_cache`) so they survive `docker compose down`/`up` cycles instead of
  re-downloading the embedding model and losing data every restart.
- **frontend** — Next.js production build (`output: "standalone"`) on `:3000`.

`NEXT_PUBLIC_API_URL` is baked into the frontend's client-side JS **at build time** (that's
how Next.js's `NEXT_PUBLIC_*` variables work). The compose file passes it as a build arg
defaulting to `http://localhost:8000`, which is correct for local/single-host use where the
browser and the Docker host are the same machine. Deploying frontend and backend on
different hosts means rebuilding the frontend image with
`docker compose build --build-arg NEXT_PUBLIC_API_URL=https://your-api-host frontend`.

## Secrets

All secrets are environment variables, loaded from `backend/.env` — **never** hardcoded and
never logged (the structured JSON logger in `app/core/logging.py` redacts any field whose
key looks like `password`, `token`, `api_key`, `authorization`, or `secret`).

| Variable | Required? | Notes |
|---|---|---|
| `JWT_SECRET_KEY` | Yes | Generate with `openssl rand -base64 32`. Rotating it invalidates all issued tokens. |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Yes (first boot) | Bootstraps the single user account. No-op if a user already exists. |
| `SENTRY_DSN` | No | Leave blank to disable error tracking entirely. |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | At least one, to actually rewrite | Analysis/scoring works with zero keys configured — keys are only needed for the `/rewrite` endpoint (batch rewriting) and Stage B validation (LLM entailment judge). |
| `OLLAMA_BASE_URL` | No | Only used if `DEFAULT_PROVIDER=ollama`. |

An explicitly blank value (`ANTHROPIC_API_KEY=`) is treated the same as unset — the config
layer coerces empty strings to `None` so a blank `.env` line never gets passed to a provider
SDK as a literal empty-string credential (see the `_blank_string_means_unset` validator in
`app/core/config.py`).

## Database

SQLite by default, with SQLAlchemy models using only portable column types (no SQLite-only
features) specifically so a Postgres migration later is a `DATABASE_URL` + Alembic
connection-string change, not a schema rewrite. To move to Postgres:

1. Set `DATABASE_URL=postgresql+psycopg://user:pass@host/db` (add `psycopg[binary]` to
   `backend/requirements.txt`).
2. Run `alembic upgrade head` against the new database — every migration, including the data
   migrations that seed the rubric/validation config, replays cleanly.

## Health check

`GET /health` returns `{"status": "ok"}` once the app has finished startup (admin bootstrap,
error tracking init). Use it as the container/load-balancer health check endpoint.

## What's not handled yet

- No HTTPS termination — put this behind a reverse proxy (Caddy, nginx, or your platform's
  load balancer) for anything beyond local use.
- No multi-user support — the JWT auth is single-account by design (see
  [phase1-design.md](phase1-design.md)); don't expose this publicly as-is.
- `rewrites` (every validation attempt, pass or fail) grows unbounded — there's no retention
  policy yet. Fine for the data volumes this is designed for; revisit if that changes.
