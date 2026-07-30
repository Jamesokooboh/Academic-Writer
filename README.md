# AI Academic Writing Editor

An editing assistant for academic writing — grammar, readability, flow, and tone-matching
to a target academic register. It is **not** a text generator, paraphraser, or humanizer:
the system is built to preserve the author's original meaning above all else, and every
rewrite it proposes is validated against the original before it's ever shown as accepted.

Built for authors polishing their own writing, not for disguising AI-generated text as
human-written.

## How it works (short version)

1. A document is chunked into paragraphs, then segmented into sentences.
2. Each sentence is scored against a weighted rubric (grammar, readability, passive voice,
   redundancy, AI-phrasing). Sentences below the threshold are flagged `NEEDS_IMPROVEMENT`;
   everything else is left untouched.
3. Flagged sentences are rewritten in batches by an LLM.
4. Every rewrite passes a two-stage check before it's accepted: a fast local embedding
   similarity filter (Stage A), then an LLM entailment judge (Stage B). Either stage failing
   discards the rewrite and keeps the original sentence.
5. Accepted rewrites show up as Track Changes — accept or reject each one individually.

The full design rationale (rubric weights, validation thresholds, database schema, API
surface) is in [docs/phase1-design.md](docs/phase1-design.md).

## Stack

- **Backend:** FastAPI, SQLAlchemy + Alembic (SQLite, Postgres-portable), JWT auth
- **Frontend:** Next.js (App Router), TypeScript, TailwindCSS, React Query
- **AI:** provider-agnostic adapters for OpenAI, Anthropic, Gemini, and Ollama
- **Similarity:** local `sentence-transformers` (Stage A) + LLM judge (Stage B)

## Quickstart

### Docker (recommended)

```bash
cp backend/.env.example backend/.env   # then fill in at least ADMIN_EMAIL/ADMIN_PASSWORD
docker compose up --build
```

Frontend: http://localhost:3000 · Backend API docs: http://localhost:8000/docs

See [docs/deployment-guide.md](docs/deployment-guide.md) for details, including secrets
handling and what to change for a non-local deployment.

### Manual (local development)

See [docs/developer-guide.md](docs/developer-guide.md) for backend/frontend setup without
Docker, running the test suites, and a tour of the project structure.

## Testing

- Backend: `cd backend && pytest -q` (44 tests: rubric scoring, pipeline orchestration with
  faked LLM/embedding dependencies, full API integration, import/export round-trips)
- Frontend unit tests: `cd frontend && npm run test` (Vitest + Testing Library)
- Frontend E2E: `cd frontend && npm run test:e2e` (Playwright; needs the backend running)

CI (`.github/workflows/ci.yml`) runs all three on every push/PR.

## Repo structure

```
backend/     FastAPI app, Alembic migrations, pytest suite, calibration script
frontend/    Next.js app, Vitest unit tests, Playwright E2E tests
docker/      Dockerfiles for both services
docs/        Design doc, deployment guide, developer guide, contributing guide
```

## Documentation

- [docs/phase1-design.md](docs/phase1-design.md) — architecture, DB schema, API design, rubric and validation-threshold rationale
- [docs/developer-guide.md](docs/developer-guide.md) — local setup, running tests, project tour
- [docs/deployment-guide.md](docs/deployment-guide.md) — Docker, environment variables, secrets
- [docs/contributing.md](docs/contributing.md) — branch/PR conventions, pre-PR checklist
- API reference — auto-generated OpenAPI docs at `/docs` on the running backend
