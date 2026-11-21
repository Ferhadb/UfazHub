# UFAZ Hub

A student-run knowledge platform for UFAZ (Azerbaijan-France University): learning resources, articles, collections, research, and questions and answers. Visitors browse freely; signing in unlocks writing and voting; admins moderate. Design direction: "The Living Archive" (see `docs/rebuild-spec.md`).

Stack: FastAPI + async SQLAlchemy + PostgreSQL 16 + Redis (arq worker) behind nginx; Next.js 15 (App Router, React 19, Tailwind v4). TypeScript API types are generated from the OpenAPI schema.

## Quickstart (5 commands)

Needs `uv`, Node 24, Postgres 16 binaries (`brew install postgresql@16`) and Redis.

```bash
make install                  # uv sync + npm ci
bash scripts/pg.sh start      # local Postgres 16 on :5433 (no Docker)
cp backend/.env.example backend/.env   # then point DATABASE_URL at localhost:5433
make be                       # API on http://localhost:8000/docs (new terminal)
make fe                       # web on http://localhost:3000 (new terminal)
```

Full stack in Docker: `cp deploy.env.example .env && cp backend/.env.example backend/.env && docker compose up -d --build`, then open http://localhost.

## Everyday commands

| Command          | What it does                                                          |
| ---------------- | --------------------------------------------------------------------- |
| `make test`      | Backend tests (real Postgres, migration down/up) + frontend unit tests |
| `make lint`      | Every CI check: black, pytest, prettier, eslint, tsc, OpenAPI drift   |
| `make typegen`   | Regenerate `frontend/openapi.json` and `src/lib/api/schema.d.ts`      |
| `make format`    | black + prettier                                                      |
| `make playground`| Disposable local demo with seeded data                                |

`make help` lists the rest. Deployment: [DEPLOYMENT.md](DEPLOYMENT.md). Operations: [docs/runbook.md](docs/runbook.md). Architecture: [docs/architecture.md](docs/architecture.md). Decisions: [docs/adr/](docs/adr/). Progress: [docs/status.md](docs/status.md).
