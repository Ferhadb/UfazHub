# UFAZ Hub

A student-run knowledge platform for UFAZ (Azerbaijan-France University): learning resources, articles, collections, research, and questions and answers. Visitors browse freely; signing in unlocks writing and voting; admins moderate. Design direction: "The Living Archive" (see `docs/rebuild-spec.md`).

Stack: FastAPI + async SQLAlchemy + PostgreSQL 16 + Redis (arq worker) behind nginx; Next.js 15 (App Router, React 19, Tailwind v4). TypeScript API types are generated from the OpenAPI schema.

## Quickstart

Needs `uv`, Node 24, PostgreSQL 16 binaries (`brew install postgresql@16` on macOS), and Redis. From the repo root:

```bash
make install
bash scripts/pg.sh start      # creates ufazhub_playground and ufazhub_test on :5433
redis-server --daemonize yes  # or start your existing local Redis service on :6379
cp backend/.env.example backend/.env
```

In `backend/.env`, set `DATABASE_URL=postgresql+asyncpg://postgres@localhost:5433/ufazhub_playground` and `REDIS_URL=redis://localhost:6379/0`. Then run `make migrate`, `make be`, and `make fe` (the last two in separate terminals). The API is at http://localhost:8000/docs and the site at http://localhost:3000. Development without SMTP logs email links in the backend terminal.

Full stack in Docker: copy `deploy.env.example` to `.env`, copy `backend/.env.example` to `backend/.env`, then run `docker compose up -d --build` and open http://localhost. Set a real `POSTGRES_PASSWORD` in the root `.env` for any nonlocal stack. The production procedure is in [DEPLOYMENT.md](DEPLOYMENT.md).

## Everyday commands

| Command          | What it does                                                          |
| ---------------- | --------------------------------------------------------------------- |
| `make test`      | Backend tests (real Postgres, migration down/up) + frontend unit tests |
| `make lint`      | Every CI check: black, pytest, prettier, eslint, tsc, OpenAPI drift   |
| `make typegen`   | Regenerate `frontend/openapi.json` and `src/lib/api/schema.d.ts`      |
| `python3 scripts/generate-api-docs.py` | Regenerate [docs/api.md](docs/api.md) from OpenAPI |
| `make format`    | black + prettier                                                      |
| `make playground`| Disposable local demo with seeded data                                |

`make help` lists the rest. API: [docs/api.md](docs/api.md). Deployment: [DEPLOYMENT.md](DEPLOYMENT.md). Operations: [docs/runbook.md](docs/runbook.md). Architecture: [docs/architecture.md](docs/architecture.md). Decisions: [docs/adr/](docs/adr/). Progress: [docs/status.md](docs/status.md).
