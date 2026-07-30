# Contributing

## Before opening a PR

```bash
# backend
cd backend && .venv/Scripts/python -m pytest -q

# frontend
cd frontend && npx tsc --noEmit && npx eslint . && npm run test && npm run build
```

CI runs the same checks (`.github/workflows/ci.yml`) plus the Playwright E2E suite — a PR
that doesn't pass these locally won't pass CI either.

## Conventions

- **Migrations:** every schema or seed-data change to the database goes through a new
  Alembic revision (`alembic revision --autogenerate -m "..."` for schema changes,
  `alembic revision -m "..."` + hand-written `upgrade()`/`downgrade()` for data changes).
  Never hand-edit an already-applied migration file.
- **Domain layer stays framework-free:** `backend/app/domain/` shouldn't import from
  `api/`, `ai/`, or `similarity/` directly — depend on the interfaces
  (`ProviderAdapter`, `EmbeddingSimilarity`, `EntailmentChecker`) instead, so the pipeline
  stays testable with fakes and swappable without touching business logic.
- **New provider/model:** implement `ProviderAdapter` (see `app/ai/anthropic_adapter.py` for
  the shape) and register it in `app/ai/factory.py` — nothing else should need to change.
- **Meaning preservation is non-negotiable:** any change touching the rewrite prompt, the
  rubric, or the two-stage validator should err toward returning the original sentence
  unchanged when uncertain, not toward a "better-sounding" rewrite. See the non-negotiable
  rules in [phase1-design.md](phase1-design.md).
- Commit messages: imperative mood, explain *why* over *what* where it's not obvious from
  the diff.

## Branching

`main` is deployable. Branch per change, PR into `main`. No direct pushes to `main`.
