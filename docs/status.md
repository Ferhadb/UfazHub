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

## Slice 2: design system, auth, rate limiting, audit log

Built
- Design system: 22 accessible primitives in `frontend/src/components/ui` (Button, IconButton, Input, Textarea, Select, Combobox, Checkbox, Switch, Modal, Drawer, Toast, Tabs, Badge, Stamp, Avatar, Skeleton, EmptyState, Pagination, Tooltip, Card, Callout, Marginalia) on Radix where it helps; 24 hand-drawn icons, 6 original geometric ornaments, 5 illustrations; 44px targets, accent focus rings, reduced-motion fades. `/design` documents every primitive with light and dark previews side by side (scoped `[data-theme-preview]` tokens). Vitest covers keyboard and role behaviour for every primitive (Tooltip via IconButton, Combobox/Select/Tabs/Pagination/Modal/Drawer/Toast individually). Rate limiter tests cover 429 + Retry-After, window reset and fail-open when Redis is down.
- Backend auth (`/api/auth`): signup, login, refresh (rotation), logout, logout-all, me, verify-email, resend-verification, password forgot/reset, dev-only login-as. argon2id, 15 min access JWT in the body, httpOnly SameSite=Lax refresh cookie scoped to `/api/auth`, SHA-256 hashed refresh tokens in families with reuse detection (replay revokes the family), double-submit CSRF on refresh/logout, hashed expiring single-use email tokens (newest link only), `SIGNUP_ALLOWED_DOMAINS`, production refuses the default JWT secret and `COOKIE_SECURE=false`. Banned users cannot log in or use existing tokens.
- Redis fixed-window rate limiting (per IP and per user) with a 429 envelope and `Retry-After`; presets `limit_auth/write/vote/search` (auth applied now, the rest ready for later slices). Fails open if Redis is down.
- `audit_log` table and `services/audit.py` (actor, action, target, before/after diff of changed keys only, reason, request id); `Page[T]` cursor schema with encode/decode helpers; mail via arq job `send_email` (logged when SMTP is unset; dev logs directly without a worker). Migration `0002`.
- Frontend: `useSession` (TanStack Query, silent refresh at 80% of token lifetime, cross-tab refresh lock via Web Locks), typed openapi-fetch client injecting the in-memory token and CSRF header, middleware guard for protected prefixes, sign in / sign up / verify / reset pages, a minimal `/settings`, skip link and header.

Deferred
- Playwright e2e and axe runs; reference screenshots (home, article, profile) at 360/1440 in both themes.
- Sign-in via 401-retry on an expired access token (we rely on scheduled refresh); account lockout per email (only per-IP limits); admin audit viewer; email digest.
- Icons to 30+ (24 now) and more illustrations; theme toggle UI (OS default plus stored choice already supported).
- Content-writing endpoints will apply `limit_write/limit_vote/limit_search` and the muted/verified checks when they exist.

Decisions to review
- Strict reuse detection: two tabs refreshing simultaneously would revoke the family; mitigated client-side with `navigator.locks`, no server grace window.
- Login is allowed before email verification (`email_verified` is exposed; later slices gate writes on it). Signup reveals "email already registered" (409) rather than hiding it.
- Middleware can only see the readable `csrf_token` cookie, used as a session hint; real enforcement is the API.
- Select is the native element (best mobile picker, free a11y); Combobox is custom ARIA 1.2.
- Rate-limit auth default is 20 requests/min/IP because campus NAT shares IPs.
- CSRF token is a random unsigned double-submit value (adequate with SameSite=Lax); can be HMAC-signed later.
- Added `argon2-cffi`, `pyjwt`, `email-validator`, `@radix-ui/*` (dialog, tooltip, tabs, switch, checkbox, toast), `clsx`.
