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

### Slice 2 verifier follow-up
- Added backend test that logout rejects a missing or forged CSRF token and leaves the session intact.
- Still deferred: applying `limit_write/limit_vote/limit_search` (no such routes yet); icons beyond 24; browser-based visual check of `/design` light/dark, focus rings and 44px targets (only build and jsdom tests so far).

## Slice 3: content base, resources, votes, bookmarks, search

Built
- Migration `0003`: `content_items` base table (joined-table inheritance; `type`/`status` VARCHAR + CHECK, `hidden` requires `hidden_reason`, call numbers like `RES-0421` from per-type sequences, counters, `search_vector`), `resources` subtype (all spec fields), `resource_links` (up to 5 per resource, canonical URL stored), `tags` + `content_tags`, `votes` (PK `(user_id, item_id)`, value CHECK +-1), `bookmarks`.
- Search: `ufaz_search` text-search configuration (unaccent + English stemming), trigger-maintained weighted `tsvector` (title A, tags B, description C, resource notes D) with GIN, trigram GIN on the folded title via an immutable `f_unaccent` wrapper. `GET /api/search`: `websearch_to_tsquery` + `ts_rank_cd`; when full text finds nothing it reruns on `pg_trgm` word similarity (typo tolerance). `ts_headline` snippets, filters (type, tag, research, difficulty), cursor pagination, rate limited. Highlights use U+0002/U+0003 markers so no markup ever reaches the client.
- API: `GET/POST/PATCH /api/resources`, `GET /api/resources/{call_number}`, `GET /api/resources/duplicates` (canonical-URL match + similar titles), `GET /api/tags`, `PUT /api/content/{id}/vote` (-1/0/1), `PUT|DELETE /api/content/{id}/bookmark`, admin `POST /api/content/{id}/hide|publish` (audited). Cursor-paginated lists (latest, top).
- Votes: item row is locked (`FOR UPDATE`) so the vote upsert and `vote_score` change are one serialised transaction; no self-votes; daily cap (`VOTE_DAILY_CAP`, default 200) answers 429. Bookmarks are idempotent; only the request that inserts or deletes the row moves `bookmark_count`.
- Permission layer `app/api/permissions.py`: `optional_user`, `ActiveUser` (muted blocked), `VerifiedUser` (email verified), `AdminUser`, `can_manage`, `initial_status`. Verified students and admins publish directly; everyone else lands in `pending_review`.
- Tests (backend 129, coverage 95% overall, services 96-99%): permission matrix (7 actors x 7 write endpoints), vote constraints and concurrency (15 voters, 8 simultaneous double clicks, concurrent flips: counter always equals the sum), bookmark idempotency, canonical URLs, duplicates, ranking weights, typo and accent folding, websearch syntax, snippets, filters, cursor stability, index following edits, rate limits. Test helpers in `tests/factories.py`.
- Seed: 6 users and 17 realistic UFAZ resources with tags, votes, bookmarks; writes demo logins to `backend/.playground/accounts.txt`; refuses production.
- Frontend: `/resources` (list/grid/shelf toggle, difficulty/order/research/tag filters in the URL, skeletons, empty, error + retry, load more by cursor), `/resources/[callNumber]` (links with `rel="noopener nofollow ugc"`, margin note, warning callout), `/submit` (react-hook-form + zod, server field errors mapped onto fields, duplicate warning, unverified-email block), Cmd/Ctrl+K palette (full-screen catalogue overlay, type tabs, results grouped by type, highlighted matches, combobox keyboard navigation, Radix focus trap and focus return), optimistic votes and bookmarks with rollback and sign-in redirect for guests. 2 icons added (arrow-up, arrow-down). Frontend tests: 116 passing.

Deferred
- Attachments: `resources.primary_attachment_id` is a plain nullable UUID; slice 4 adds the `attachments` table and the foreign key.
- View counting (`view_count` exists, nothing increments it), comments (`comment_count` exists), a bookmarks list page and `GET /api/me/bookmarks`, tag rename re-indexing, pending-review queue UI (approval is only `POST /content/{id}/publish`).
- Articles, collections and questions: the search endpoint, ranking and palette already accept their types; their routes (`/articles/...`) do not exist yet.
- Playwright e2e + axe for resources/palette; browser check was one manual pass of `/resources` and the palette in the dark theme.

Decisions to review
- Search falls back to trigram matching only when full text returns nothing (so `-word` and quoted phrases stay exact). A page mixing exact and fuzzy hits is not supported; the cursor records which mode produced it. Fuzzy hits are not highlighted.
- Stock `unaccent` does not fold the Azerbaijani schwa, so `f_unaccent` translates it to `e` and the vector indexes text both as written and folded. Highlights on folded matches are absent (the snippet shows the original text).
- Search uses the `english` stemmer for every language; EN is exact, AZ/FR/RU rely on exact tokens plus the trigram fallback.
- Daily vote cap counts vote rows touched in the last 24h; taking a vote back is always allowed, so delete-and-recast can reuse a slot. The per-minute limiter (60/min/user) bounds that.
- Muted users cannot vote or bookmark (all writes blocked); unverified-email users can vote and bookmark but not submit.
- `time_commitment_minutes` (integer) instead of free text; `category` is free text until the course taxonomy (slice 7).
- Resource detail is addressed by call number (`/resources/RES-0421`), votes and edits by UUID.
- One global `call_seq_<type>` sequence per type: numbers are never reused, but gaps appear when a create rolls back.
- `/api/tags` is a bounded top-N (limit <= 50) returned as a `Page` with no next cursor.
- Added `concurrency = ["greenlet", "thread"]` to coverage config; without it async SQLAlchemy lines were reported as missed.
