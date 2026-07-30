# Phase 1 — Design & Architecture

## 1. Scope recap

Academic editing assistant, not a generator/paraphraser/humanizer. Preserve meaning above all; only rewrite sentences that fail a quality rubric, and only accept a rewrite if it passes two-stage semantic validation. This tool polishes an author's own writing — not a tool for disguising fully AI-generated text as human-written; keep that framing in all UI copy/docs.

## 2. Architecture (Clean Architecture)

```
backend/app/
  api/         Presentation — FastAPI routers, request/response wiring only
  core/        Config (pydantic-settings/.env), JWT auth, logging, DI wiring
  domain/      Business logic — pipeline orchestration, entities, use-cases (no framework imports)
  ai/          AI Layer — ProviderAdapter interface + OpenAI/Anthropic/Gemini/Ollama adapters
  similarity/  Similarity Engine — Stage A (embedding) + Stage B (entailment), each behind an interface
  db/          Storage — SQLAlchemy models, session, repositories
  schemas/     Pydantic DTOs shared between api/ and domain/
backend/alembic/   Migrations (SQLite now, Postgres-portable: no SQLite-only types)
backend/tests/
frontend/app/          Next.js App Router pages
frontend/components/   Editor, Track Changes UI, Settings panel
frontend/lib/          API client, diff rendering helpers
frontend/hooks/        React Query hooks
shared/    OpenAPI-generated types shared FE/BE (generated, not hand-written)
docker/    Dockerfiles + docker-compose
docs/      This file + README, DB schema, deployment/dev/contributing guides
scripts/   One-off dev scripts (seed data, migration helpers)
tests/     Cross-cutting integration/e2e tests that span FE+BE
```

Dependency rule: `domain/` depends on nothing else in the app (only stdlib + Pydantic DTOs); `ai/` and `similarity/` are called through interfaces domain defines, so swapping a provider or model never touches domain code.

### Key tech decisions (locked for Phase 1)
- **Diffing:** `diff-match-patch` for word-level Track Changes diffs (handles the added/removed/modified granularity needed for color-coded diffs better than raw `difflib`).
- **Auth:** JWT, single-user, password hash (bcrypt via `passlib`) stored in `users` table. Built in Phase 2, not deferred.
- **DB:** SQLite + SQLAlchemy + Alembic from day one. Models use portable types only (`String`, `Text`, `Integer`, `Float`, `Boolean`, `DateTime`, `JSON`) so swapping the Alembic connection string to Postgres later requires no model changes.
- **Observability:** structured JSON logging (request id, provider, model, tokens, latency, similarity/entailment score per rewrite) from Phase 2; Sentry-compatible hook via `sentry-sdk`, no-op if DSN unset.
- **Secrets:** provider API keys via `.env` / environment only, never logged (log middleware redacts known key-shaped fields), documented in the Deployment Guide.

## 3. Database schema (SQLite → Postgres-ready)

| Table | Purpose | Key columns |
|---|---|---|
| `users` | single-user auth | id, email, password_hash, created_at |
| `documents` | one per uploaded/authored doc | id, user_id (FK), title, writing_mode, word_count_mode, rewrite_strength, created_at, updated_at |
| `document_versions` | full-text snapshots for history/undo | id, document_id (FK), version_number, content, created_at |
| `chunks` | paragraph/section-level chunks with context tail | id, document_id (FK), order_index, raw_text, context_tail |
| `sentences` | segmented sentences per chunk | id, chunk_id (FK), order_index, original_text, rewritten_text (nullable), status (`GOOD`\|`NEEDS_IMPROVEMENT`\|`REWRITTEN`), quality_score, quality_breakdown (JSON) |
| `rewrites` | every rewrite attempt, including discarded ones | id, sentence_id (FK), model_used, stage_a_score, stage_b_score, passed_validation (bool), accepted (bool, user Track-Changes decision), created_at |
| `rubric_versions` | versioned scoring rubric | id, version, weights (JSON), threshold, active (bool), created_at |
| `validation_configs` | versioned similarity/entailment thresholds | id, version, stage_a_threshold, stage_b_threshold, active (bool), created_at |
| `api_usage_log` | cost/token tracking per request | id, document_id (FK), request_id, provider, model, input_tokens, output_tokens, latency_ms, cost_usd, created_at |

Rationale for `rewrites` logging every attempt (not just accepted ones): Phase 4 needs a labeled corpus of scored pairs to calibrate thresholds, and post-launch threshold changes must be replayable against historical scores without new LLM calls.

## 4. API design (REST, FastAPI)

```
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/me

GET    /api/documents
POST   /api/documents
GET    /api/documents/{id}
PUT    /api/documents/{id}
DELETE /api/documents/{id}
GET    /api/documents/{id}/versions
POST   /api/documents/{id}/versions/{version_id}/restore

POST   /api/documents/{id}/analyze          # chunk + segment + score → GOOD/NEEDS_IMPROVEMENT, no LLM rewrite yet
POST   /api/documents/{id}/rewrite          # batched rewrite of NEEDS_IMPROVEMENT sentences + two-stage validation
POST   /api/documents/{id}/changes/{sentence_id}/accept
POST   /api/documents/{id}/changes/{sentence_id}/reject
GET    /api/documents/{id}/metrics          # meaning-preservation, readability, grammar, cost/tokens, etc.

POST   /api/documents/{id}/export?format=docx|pdf|txt|md

GET    /api/config/writing-modes
GET    /api/config/rubric                   # currently active rubric_versions row
```

`analyze` and `rewrite` are separate endpoints deliberately: scoring/classification uses a cheap/fast model and no user-facing cost commitment; `rewrite` is the expensive step and is what the UI's running-cost estimate gates.

## 5. Sentence quality rubric (v1, versioned in `rubric_versions`)

Each sub-score normalized to 0–1 (1 = best), composite = weighted sum:

| Signal | Weight | Source |
|---|---|---|
| Grammar | 0.30 | LanguageTool error count, normalized by sentence length |
| Readability fit | 0.20 | Flesch-Kincaid grade level distance from the document's Writing Mode target band |
| Passive voice | 0.15 | passive-clause ratio, inverted |
| Redundancy/wordiness | 0.15 | filler-phrase + nominalization count, normalized |
| AI-phrasing | 0.20 | regex/pattern match count against a stock-LLM-ism list ("it's important to note", "delve into", ...), normalized |

`composite < threshold` → `NEEDS_IMPROVEMENT`, else `GOOD`. Threshold default **0.75**, stored in `rubric_versions.threshold`, calibrated empirically in Phase 4 against the labeled sentence-pair set — not hardcoded in application code.

## 6. Two-stage semantic validation

- **Stage A (fast filter):** cosine similarity between original and rewrite sentence embeddings. Default model: local `sentence-transformers` (`all-MiniLM-L6-v2`) so this stage never depends on a paid API; swappable to `text-embedding-3-large` via the same provider abstraction used for LLM calls. Threshold `stage_a_threshold`, calibrated in Phase 4 to **0.89** (was a 0.90 placeholder) — see `scripts/calibrate_thresholds.py` and `validation_configs` version 2.
- **Stage B (meaning check):** only runs if Stage A passes (cost control). Implemented as a structured LLM-judge prompt (`app/similarity/entailment.py`) reusing the existing provider adapters, per the "hosted LLM judge" option below. Threshold `stage_b_threshold` remains the **0.85** placeholder — calibrating it requires live, billable LLM calls that haven't been run yet (the harness is in place; rerun the script once that's approved).
- Either stage failing → discard rewrite, return original sentence unchanged, sentence stays flagged as attempted-but-reverted.
- Every attempt logs both scores to `rewrites` regardless of pass/fail, so thresholds are revisited from real data, not re-tuned blind.
- Thresholds live in `validation_configs`, not as code constants — Phase 4 calibrates the actual default against a labeled set of human-reviewed pairs (some deliberately meaning-altered).

## 7. Assumptions

- Single user for v1 (JWT skeleton is single-account; multi-tenant is out of scope).
- SQLite is sufficient for v1 data volumes; Postgres migration is a connection-string + Alembic-env change only, not a schema rewrite.
- Local sentence-transformers model is acceptable for Stage A by default (no per-request API cost for the cheap filter); Stage B may use a hosted LLM judge when a good local NLI model isn't configured.
- `rewrites` table growing unbounded is acceptable for v1 (no retention policy yet — flag if calibration data volume becomes a storage concern).

Open for review before Phase 2 (backend foundation, JWT skeleton, provider abstraction, logging).
