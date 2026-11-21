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

## Slice 4: articles, collections, comments, uploads

Built
- Backend: articles (markdown via markdown-it-py `html=False`, nh3 allow-list, `rel="noopener nofollow ugc"`, slug, excerpt, reading time, TOC, cover, draft/published), collections with ordered items and per-item notes, one-level threaded comments (rate limited, counters), storage interface (`LocalStorage` at MEDIA_ROOT, S3-ready), uploads (size limits, signature-sniffed MIME, Pillow WEBP variants, no-op virus-scan hook, HMAC signed URLs with expiry, avatars via storage), link-preview arq job behind a tested SSRF guard (connect-time IP validation, per-hop redirect checks). Migration 0004; search triggers now index article bodies. Backend tests: 271 passing.
- Frontend: article reader (distraction-free, bookmark-ribbon progress, scroll-tracking TOC, margin notes via Marginalia, drop cap, continue-reading memory, print stylesheet, DOMPurify second pass), `/articles` list, article editor (write/server preview, cover upload, draft/publish, `/articles/[ref]/edit`), `/collections` shelf of spines that pull out plus detail with notes, comments UI (also on resources), notebook-style `/submit` composer (type picker, ruling changes per type, live index-card preview), header links. Frontend tests: 137 passing.

Deferred
- Comment editing; avatar upload UI (endpoint and `avatar_url` exist); collection editing UI (PATCH exists); article/collection seed data; Playwright e2e + axe for the new pages.
- Real virus scanner and S3 backend (interfaces only); stale-image cleanup job for orphaned attachments.

Decisions to review
- Article detail resolves by call number or slug; slug collisions get a call-number suffix. Drafts and pending articles are visible only to the author and admins.
- Collections accept only published resources/articles (1 to 50); items hidden later silently drop off.
- Comments are plain text, one level deep, at most 50 replies per thread; the counter updates under an item row lock.
- Signed media URLs expire on a ttl-snapped boundary so cached pages keep stable URLs.
- SSRF guard allows only http/https on ports 80/443 and rejects private, loopback, link-local, NAT64 and IPv4-mapped addresses at connect time.
- Margin notes show up to three short top-level comments; the editor preview is rendered by the server so it matches what is published.

## Slice 5: Q&A, reputation, notifications

Built
- Migration `0005`: `questions` (topic, optional linked resource, `duplicate_of_id`) and `answers` (accepted/pinned timestamps with partial unique indexes: one of each per question) as content subtypes, so votes, comments and moderation work unchanged; `reputation_events` ledger (`UNIQUE (user_id, event_key)` makes every event idempotent); `notifications` (dedupe key, read/emailed timestamps); `users.reputation` and `users.email_digest`; `answer` added to the content type CHECK and a `call_seq_answer` sequence (`ANS-0001`). Down/up round trip and `alembic check` are covered by the existing migration tests.
- Q&A API: list (latest/top, topic, tag, unanswered), `GET /questions/similar` (trigram plus full-text, typo tolerant, excludes duplicates), detail, ask, answers list (accepted, then pinned, then score; keyset cursor), answer, `PUT|DELETE /answers/{id}/accept` (asker only, moves the tick along), `PUT|DELETE /answers/{id}/pin` (admin), `PUT|DELETE /questions/{id}/duplicate` (asker, admin, or 100 reputation; no chains, duplicates of a duplicate follow along; the API exposes `duplicate_of` and the page redirects). Answers are excluded from search.
- Reputation: points table, privileges and daily cap are constants in `services/reputation.py`; `GET /api/reputation/rules` feeds the public page from them. Vote events upsert one ledger row per (voter, item), so repeat, flip and undo never stack; vote reputation is capped per rolling day (`REP_DAILY_CAP`, 200); no self-votes (existing) and no reward for accepting your own answer; downvoting answers needs 15 reputation. `users.reputation` moves by the same delta in the same transaction; tests assert it always equals the ledger sum. `GET /api/me/reputation` is the user's cursor-paged ledger.
- Notifications: reply (item author and parent comment author), answer (to the asker), answer accepted, vote milestones (10/25/50/100/250/500, once each), moderation (hide/publish, pin, duplicate mark). Never notifies you of your own action. `GET /notifications` (cursor, unread filter), `/notifications/unread`, `POST /notifications/read` (ids or all), `GET|PUT /notifications/settings` (digest opt-in). arq cron `email_digest` (07:00) emails one summary per opted-in user and stamps `emailed_at`.
- Validation error envelope fix: a field literally named `body` was reported under `_`; only the leading source marker is stripped now.
- Backend tests: 308 passing (37 new for Q&A, acceptance permissions, duplicate merging, reputation rules and caps, notification fan-out, cursors, digest); services coverage 97%.
- Frontend: `/questions` (index tabs), `/questions/[callNumber]` as an annotated exam paper (red "checked" stamp on the accepted answer, circled score in the margin, pin, merge form, answer composer, per-answer notes, redirect for merged questions), `/ask` with live similar-question suggestions, `/notifications` (unread filter, mark read, digest switch), header bell with a flame dot and spoken count, public `/reputation` with your history. Frontend tests: 158 passing.

Deferred
- Editing questions and answers; answer comments are available but not counted on the question card; notification when a pending answer is later approved.
- Seed data for Q&A; Playwright e2e + axe for the new pages; real-time bell (it polls every 60s).
- Per-pair voting-ring detection (only the per-user caps exist); reputation floor at zero; privileges beyond downvote and duplicate marking (they arrive with moderation in slice 6).
- Course taxonomy for `topic` (free text until slice 7); "for you" tag feeds.

Decisions to review
- Answers are `content_items` rows (type `answer`, title copied from the question) rather than a separate table: one vote/comment/moderation path, at the cost of filtering them out of search and feeds.
- Answers are plain text (no Markdown); answer body max 10,000 characters.
- Only the asker accepts (an admin cannot); admins pin. Acceptance points are not subject to the daily cap.
- Merged questions keep their answers; new answers on a merged question are refused (409) with a pointer to the original.
- Point values (resource/article/question +5, collection +3, answer +10, any downvote -2, accepted +15 / accepting +2) and thresholds are placeholders to tune.
- The margin score is shown twice (circled mark and the vote control); the mark is decorative and hidden from screen readers.
- Answers by users who are not verified students go to `pending_review` like other content.

## Slice 6: moderation, reports, admin panel

Built
- Migration `0006`: `reports` (reason VARCHAR+CHECK: spam, offensive, copyright, inaccurate, broken_link, off_topic, other; free-text note; open/actioned/dismissed; one report per user per item) and `appeals` (content or ban; partial unique indexes allow one open appeal per subject).
- Backend split into `services/moderation` (reports, queue, user-visible history), `content_admin` (hide, unhide, approve, dismiss; bulk with per-item savepoints), `users_admin` (list, mute/unmute, ban/unban, role), `appeals`, and `audit` (now also the log query). Routers: `api/moderation.py` (report, appeal, `/me/moderation`, `/me/appeals`, `/auth/appeal`) and `api/admin.py` (queue with type/reason/view filters and cursor, bulk actions, users, appeals, audit viewer), all admin routes behind `admin_user`.
- Every action writes `audit_log` with a before/after diff and reason (`content.hide|unhide|approve`, `report.dismiss`, `user.mute|unmute|ban|unban|role`, `appeal.accept|reject`). Ban revokes all refresh tokens; banned users already fail login, refresh and every bearer call; muted users fail every write (existing `ActiveUser`).
- Old `/content/{id}/hide` and `/publish` routes kept as thin wrappers over `content_admin`.
- Backend tests: 330 passing (22 new: reports, queue filters, each admin action with audit assertions, permission matrix for admin endpoints, mute/ban/unban end to end, appeals both kinds, history, audit filters); services coverage 97%.
- Frontend: report button (flag icon) on resource, article, collection, question and answer pages; `/admin` (queue with filters and bulk actions, users, appeals, audit log) guarded by middleware plus a role check; moderation history and appeals section in settings; `/appeal` page for suspended users linked from the sign-in error; Admin link in the header for admins. Frontend tests: 164 passing.

Deferred
- Reporting comments and users (reports target content items only); comment hiding.
- Notification to a banned user's appeal outcome (ban appeals have no item to point a notification at); email on mute/ban.
- Auto-hide on N reports, report-abuse penalties, moderator notes on reports, Playwright e2e + axe for the admin panel.

Decisions to review
- "Server check" for `/admin`: the access token lives only in memory, so Next middleware sees only the session hint cookie. The page checks the role the API reported and every admin endpoint re-checks on the server (403).
- Admins cannot change their own role or status, and cannot mute or ban another admin (remove the role first); status changes require a reason; role changes too.
- A muted user may still appeal (appeals are not content writes); a banned user appeals with email and password at `/auth/appeal` since they cannot hold a session.
- Unhide always restores to `published`, even for an item hidden while pending review.
- Users see the reason and date of moderation actions but never which moderator acted.
- With a report-reason filter the queue's report count and reasons only cover matching reports.
