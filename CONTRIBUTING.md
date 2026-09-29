# Contributing

## Setup

```bash
make install              # pip install -r backend/requirements-dev.txt && npm ci
make dev-api              # terminal 1
make dev-web              # terminal 2
```

Python 3.11+ and Node 22+. Copy `.env.example` to `backend/.env` to override settings.

## Before you open a PR

```bash
make check                # ruff, format check, mypy, tsc, pytest (+coverage), vitest
```

CI runs the same checks plus a Docker build and smoke test.

## Conventions

- **Backend** – ruff (line length 130) and mypy must pass. Keep `app/domain/` pure (no I/O). Routes call `app/services/` only. Every DB query goes through `app/db/repository.py` and must be scoped by `device_id`.
- **Schemas are the contract.** After changing any Pydantic model exposed by the API, run `make openapi` and commit `frontend/openapi.json` and `frontend/src/api/schema.d.ts`.
- **Prompts** live in `backend/app/llm/prompts/*.md` (`string.Template`). Untrusted free text must be inserted inside the delimiters defined in `_common.md`.
- **Never log or persist the Gemini key.** `tests/test_api.py` and `tests/test_llm.py` assert this; keep them passing.
- **Safety rules belong in `app/domain/safety.py`**, not in prompts. The LLM may add caution, never remove it.
- **Tests** – use the mock LLM by default. The `live` marker is opt-in (`GEMINI_API_KEY=… pytest -m live`).
- **Frontend** – strict TypeScript, plain CSS in `src/styles.css`, accessible markup (labels, roles, `aria-live` for progress).

## Changing the models

1. Edit features in `backend/app/ml/features.py` (shared by training and serving) and cleaning rules in `ml_pipeline/cleaning.py`.
2. `make train` – it fails if held-out accuracy falls below `--min-accuracy`.
3. Update the numbers in `docs/MODEL_CARD.md` from `backend/artifacts/metadata.json`.
4. Commit the artifacts. `metadata.json` stores library versions and SHA-256 hashes; the app verifies both on load.

Do not add features that would be a proxy for the label (the old `Activity_Score` gave 98 % accuracy for exactly that reason) or that the app cannot observe at serving time.
