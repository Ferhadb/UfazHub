# Agent quick start

UFAZ Hub is a student knowledge platform being rebuilt in vertical slices. Start here, then read only what the task needs. `docs/rebuild-spec.md` is the source of truth for scope; `PROJECT.md` has architecture and conventions; `docs/status.md` records what each slice built and deferred. Code wins if a document is stale.

## Where to work

| Task                  | Start with                                                                                  |
| --------------------- | ------------------------------------------------------------------------------------------- |
| API or business rule  | `backend/app/api/`, `backend/app/services/`, `backend/app/schemas/`, `backend/tests/`       |
| Database change       | `backend/app/models/`, then `make revision MSG="..."` into `backend/migrations/versions/`   |
| Page or UI            | `frontend/src/app/` (App Router), `frontend/src/components/`                                |
| Tokens and theming    | `frontend/src/styles/tokens.css` is the only token file; `frontend/src/app/globals.css`     |
| API types in the UI   | Never hand-write them: `make typegen`, then use `frontend/src/lib/api/client.ts`            |
| Deployment            | `DEPLOYMENT.md`, `docker-compose*.yml`, `nginx*.conf`, `docs/runbook.md`                    |

## Local workflow

- `bash scripts/pg.sh start` gives a real Postgres 16 on :5433. Tests never use SQLite.
- Backend: `cd backend && uv run ...`. Frontend: `cd frontend && npm ...`. TypeScript stays on 5.x (Next 15).
- Green means: `make lint` (black, pytest incl. migration down/up and `alembic check`, prettier, eslint, tsc, vitest, OpenAPI not stale) and `npm run build`.

## Conventions

- Routes stay thin; business logic lives in services. Enums are `VARCHAR` + CHECK. Errors use the `{code, message, fields?, request_id}` envelope. Lists are cursor-paginated.
- Add an Alembic migration for every schema change; CI runs `alembic upgrade head` then `alembic check`.
- Design: colours, type, spacing, radii, shadows, z-index and motion come from tokens only. WCAG AA in both themes; `prefers-reduced-motion` means fades.
- Secrets and `.env` files never go in Git. Production holds real student data: no destructive commands against it.
- Smallest complete change; never cut validation, security, accessibility, or tests.
