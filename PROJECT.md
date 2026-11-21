# PROJECT.md — UFAZ Hub (canonical context for engineers and AI agents)

Domain placeholder: **ufazhub.xyz**. Student-run knowledge platform for UFAZ. Start with [`AGENTS.md`](AGENTS.md); scope lives in [`docs/rebuild-spec.md`](docs/rebuild-spec.md). Trust code over prose.

## Repo map

| Path                                | What it is                                                                                         |
| ----------------------------------- | -------------------------------------------------------------------------------------------------- |
| `backend/`                          | FastAPI (Python 3.13, `uv`), async SQLAlchemy 2 + Alembic, asyncpg, PostgreSQL 16, Redis, arq      |
| `frontend/`                         | Next.js 15 App Router, React 19, strict TypeScript, Tailwind v4, TanStack Query, Vitest, Playwright |
| `backup/`                           | `Dockerfile` + `db-backup.sh`: daily `pg_dump` into `./backups/` + Telegram off-site copy          |
| `scripts/`                          | `pg.sh` (local Postgres on :5433), `playground.sh` (local demo supervisor)                          |
| `docs/`                             | spec, status, architecture, runbook, ADRs                                                          |
| `docker-compose.yml` (+ `.prod.yml`)| postgres, redis, backup, backend, worker, frontend, nginx (+ certbot, media volume in prod)        |
| `nginx.conf` / `nginx.dev.conf`     | TLS production proxy (HSTS, CSP) / plain HTTP dev proxy                                             |

## Command cheat sheet

```bash
bash scripts/pg.sh start                 # real Postgres 16 on :5433 (DBs ufazhub_test, ufazhub_playground)
cd backend && uv run alembic upgrade head
cd backend && uv run uvicorn app.main:app --reload       # http://localhost:8000/docs
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://postgres@localhost:5433/ufazhub_test uv run pytest -q
cd backend && uv run black --check app tests scripts
cd frontend && npm run dev | lint | typecheck | test | build | format:check
make typegen                             # openapi.json + schema.d.ts (CI fails if stale)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build   # prod
```

## Backend

- `app/main.py` wires the app: request-ID middleware, error envelope handlers, JSON logs, Sentry hook, CORS allow-list. Routers mount under `API_PREFIX` (`/api`).
- `app/core/` config (asyncpg URL coercion), errors, logging, middleware, redis. `app/db/` base + async session. `app/models/` SQLAlchemy models. `app/worker.py` arq settings.
- `/api/health` is liveness; `/api/ready` checks Postgres and Redis.
- Migrations live in `backend/migrations/versions/` (`0001_extensions` enables `pg_trgm` etc.). Excluded from black.
- Tests use a real Postgres (`TEST_DATABASE_URL`); the session fixture runs `alembic downgrade base` then `upgrade head`.

## Frontend

- `src/styles/tokens.css` is the single token file (Tailwind v4 `@theme`): colours light + dark, content tints, fluid type scale, 4/8 spacing, uneven radii, paper shadows, z-index, motion. Dark follows the OS unless `data-theme` is set; an inline script in `layout.tsx` applies the stored choice before paint.
- Fonts via `next/font/google` (Piazzolla, Commissioner, JetBrains Mono, Caveat; latin, latin-ext, cyrillic).
- `src/lib/api/client.ts` is the only API entry point (openapi-fetch over generated `schema.d.ts`).
- `tokens.test.ts` asserts WCAG AA contrast for key pairs in both themes.

## Deployment

Single AWS EC2, prod compose + Let's Encrypt. Pushes to `main` that pass CI deploy over SSH (`.github/workflows/ci.yml`). See `DEPLOYMENT.md`.
