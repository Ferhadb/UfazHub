# Status

## Slice 1: scaffold, CI, tooling, design tokens, compose

Built
- Backend skeleton: config (asyncpg URL coercion), error envelope, request-ID middleware, JSON logs, Sentry hook, `/api/health` and `/api/ready`, async Alembic with `0001` extensions migration, tests on real Postgres including migration down/up and `alembic check`, arq worker stub.
- Infra copied from GPA and renamed: compose (dev + prod with worker and `media` volume), nginx (HSTS with `includeSubDomains`, CSP baseline), backup sidecar, Makefile (incl. playground), pg.sh, pre-commit, env examples, CI (backend with postgres + redis services, pip-audit; frontend with OpenAPI drift check and `npm audit`; SSH deploy to `~/ufazhub`).
- Frontend: Next 15 shell, `src/styles/tokens.css` as the single token file (colour light + dark with OS default and no-flash script, content tints, fluid type scale, 4/8 spacing, uneven radii, paper shadows, z-index, motion with reduced-motion handling), fonts via `next/font` (Piazzolla, Commissioner, JetBrains Mono, Caveat; latin, latin-ext, cyrillic), inline SVG paper grain, placeholder home, typed API client (`openapi-fetch` over generated `schema.d.ts`).
- Tests: WCAG AA contrast for key pairs in both themes, AZ/FR/RU glyph render, typed client call.
- Docs: README, DEPLOYMENT, AGENTS, PROJECT, architecture (mermaid), runbook, ADRs 0001-0005.

Deferred
- Playwright e2e specs and screenshots (config only), `/design` page and primitives (slice 2), `docs/api.md` generation, Sentry, nonce-based CSP (removes `'unsafe-inline'` from `script-src`; tracked deferred).
- Docker images were not built here (no Docker on this machine); compose and Dockerfiles are untested end to end.
- Fonts are fetched from Google at build time by `next/font` and self-hosted in the output; builds need network access once.

Decisions to review
- Domain placeholder `ufazhub.xyz`.
- Typography follows the spec's decided set (Piazzolla, Commissioner), covering Cyrillic, so RU needs no fallback.
- CSP allows `'unsafe-inline'` for scripts and styles (Next hydration and the theme script). Tighten with nonces later (runbook).
- API client base URL is the site origin because generated paths already include `/api`; the old `NEXT_PUBLIC_API_URL` build arg was removed. `INTERNAL_API_URL` is now `http://backend:8000` (no `/api`) for the same reason.
- `postcss` is pinned through npm `overrides` to clear a high-severity audit finding in Next's nested copy; drop it once Next 15 ships a fixed postcss.
- `export_openapi.py` now adds the backend dir to `sys.path` so `make typegen` works from anywhere.
- `vitest.config.ts` renamed to `.mts` to silence the CJS/ESM loader warning.
- Fonts: an earlier brief named Fraunces/Instrument Sans, but spec line 85 forbids them. The spec wins (Piazzolla/Commissioner). Human to confirm.
