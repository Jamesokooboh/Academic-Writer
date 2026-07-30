# Developer Guide

## Backend setup (no Docker)

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # .venv/bin/python on macOS/Linux
cp .env.example .env
# fill in ADMIN_EMAIL / ADMIN_PASSWORD at minimum; provider API keys only needed to
# actually call an LLM (analyze/scoring work with zero keys configured)
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs (FastAPI's auto-generated OpenAPI/Swagger UI — this
*is* the API documentation; there's no separate hand-written copy to keep in sync).

Run the test suite:

```bash
.venv/Scripts/python -m pytest -q
```

44 tests, no external network dependencies — grammar scoring's external call
(languagetool.org) is stubbed globally in `tests/conftest.py`, and every test that needs an
LLM or an embedding model uses a fake implementation of the relevant interface instead.

## Frontend setup (no Docker)

```bash
cd frontend
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL, defaults to http://localhost:8000
npm run dev
```

```bash
npm run test        # Vitest + Testing Library (component-level)
npm run test:e2e    # Playwright — needs the backend running on :8000 first
```

## Backend project tour

```
app/
  api/         FastAPI routers — request/response wiring only, no business logic
  core/        config, JWT auth, structured logging, error tracking
  domain/      chunking, segmentation, rubric scoring, rewrite batching, pipeline
                orchestration, import/export — the actual business logic, framework-free
  ai/          ProviderAdapter interface + OpenAI/Anthropic/Gemini/Ollama adapters
  similarity/  Stage A (embedding) + Stage B (LLM entailment) validation
  db/          SQLAlchemy models, session, repositories
  schemas/     Pydantic request/response DTOs
alembic/       Migrations — includes data migrations that seed/calibrate rubric and
                validation config, not just schema changes
scripts/       calibrate_thresholds.py — recalibrate Stage A/B thresholds against
                tests/data/semantic_pairs.json
```

The dependency direction is one-way: `domain/` never imports from `api/`, `ai/`, or
`similarity/` directly — it depends on the interfaces those modules define
(`ProviderAdapter`, `EmbeddingSimilarity`, `EntailmentChecker`), which callers inject. That's
what makes it possible to test the whole pipeline (`tests/test_pipeline.py`) with a fake LLM
and a fake embedding model and no network calls at all.

## Frontend project tour

```
app/          Next.js App Router pages (login, editor) + root layout/providers
components/   Shell, AuthGuard, SettingsPanel, TrackChanges (diff-match-patch based)
lib/          api.ts (typed fetch client), auth-context.tsx (React Query-backed auth state)
e2e/          Playwright specs
```

Auth is a client-held JWT in `localStorage`, sent as a Bearer token — not cookie-based
sessions — because the frontend talks to a separate FastAPI backend rather than using
Next.js Server Actions against its own database.

## Recalibrating validation thresholds

```bash
cd backend
.venv/Scripts/python scripts/calibrate_thresholds.py
```

Stage A (local embeddings) always runs live and re-suggests a `stage_a_threshold`. Stage B
needs a real, billable LLM call per labeled pair and is skipped automatically if no provider
API key is configured. To apply a new suggested threshold, write a new Alembic data
migration inserting a `validation_configs` row with `active=1` and deactivating the old one
(see `alembic/versions/ad5fbc05deea_*.py` for the pattern) — thresholds are versioned in the
database, not hardcoded, specifically so this doesn't require a code change.
