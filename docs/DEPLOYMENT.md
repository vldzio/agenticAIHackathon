# Deployment

> The Docker images and compose file have **not been run in CI yet** (no Docker daemon was available while writing them). Run `docker compose up --build` once and check `/api/v1/health` before relying on them.

## Docker Compose (single host)

```bash
docker compose up --build -d
curl http://localhost:8080/api/v1/health
```

| Service | Image | Notes |
|---|---|---|
| `backend` | `python:3.12-slim`, non-root, port 8000 | one uvicorn worker (in-process rate limiter); SQLite at `/data/aetherfit.db` on the `aetherfit-data` volume; healthcheck on `/api/v1/health` |
| `frontend` | `nginx:1.27-alpine`, port 80 → host 8080 | serves the static SPA and proxies `/api/` to `BACKEND_URL` with buffering disabled (needed for SSE); sets CSP and security headers |

The browser only talks to the nginx origin, so no CORS configuration is needed in this topology.

## Configuration

All backend settings are `AETHERFIT_*` environment variables – see [`.env.example`](../.env.example).

| Variable | Production advice |
|---|---|
| `AETHERFIT_ENV=prod` | set by the image |
| `AETHERFIT_CORS_ORIGINS` | list only the origins that serve the SPA (needed only if the SPA is on a different origin from the API) |
| `AETHERFIT_TRUST_PROXY_HEADERS=true` | only behind a proxy you control, otherwise clients can spoof their IP and dodge rate limits |
| `AETHERFIT_DATABASE_URL` | keep the SQLite file on a persistent volume, or use Postgres (SQLAlchemy URL) |
| `AETHERFIT_STRICT_MODEL_VERSIONS=true` | refuse to start if scikit-learn/numpy/pandas differ from training |

There is deliberately **no server-side Gemini key**. Live mode is bring-your-own-key: the browser sends the user's key per request; the server never stores or logs it.

## TLS and the BYOK key

Because the key travels in a request header, **serve everything over HTTPS** (terminate TLS at your load balancer / Cloud Run / Caddy). Do not enable access logging of request headers on any proxy in front of the app.

## Scaling and state

- Rate limiting is per process. For more than one replica, put a shared limiter (gateway, Cloudflare, Redis-based) in front.
- SQLite is fine for a single instance. For several instances use Postgres.
- Tables are created with `create_all`; there is no migration tool yet. Add Alembic before changing the schema in production.

## Health and operations

- `GET /api/v1/health` – `status`, `database`, `models_loaded`, `version`.
- Logs are JSON, carry a per-request `request_id` (also returned in error bodies and the `X-Request-ID` header) and redact API keys.
- Back up `/data/aetherfit.db` (plans and progress logs; contains health information users typed into the form, so treat it as sensitive).

## Model artifacts

Artifacts are committed (`backend/artifacts/`, ~12 MB). Retrain with `make train`; the image does not contain the training CSVs, only the small evaluation set used by `/models/evaluation`.
