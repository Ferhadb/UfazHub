# UFAZ Hub v2 — rebuild spec (source of truth)

Build UFAZ Hub from scratch: a student-run knowledge platform for UFAZ (Azerbaijan-France University). Students and alumni share learning resources, write articles, curate collections, publish research, and ask and answer questions. Visitors browse freely; signing in unlocks writing and voting; admins moderate.

Work in vertical slices. After each slice: run tests, lint, typecheck, and the migration, then commit. Do not start the next slice until the current one is green.

## 1. Stack (fixed)

- Backend: Python 3.13, FastAPI, async SQLAlchemy 2.0, Alembic, asyncpg, Pydantic v2, `uv` (with committed `uv.lock`), black, pytest + pytest-asyncio.
- DB: PostgreSQL 16 (tests run on real Postgres, never SQLite — SQLite hid enum and full-text bugs in v1). Locally: `bash scripts/pg.sh start` (port 5433, no Docker on this machine); CI: postgres service container.
- Frontend: Next.js 15 App Router, React 19, TypeScript strict, Tailwind (v4), TanStack Query, react-hook-form + zod, lucide-react, Vitest + Testing Library, Playwright for 3 e2e smoke flows.
- Infra: identical to the UFAZ GPA project (`/Users/farhadick/Developer/farhad/UfazGpa/UFAZ_GPA-calculator`); see 6b.
- Generate TypeScript API types from the FastAPI OpenAPI schema (`openapi-typescript`). Never hand-write API types.

## 2. Domain

Roles: `user`, `verified_ufazian`, `admin`. User status: `active`, `muted`, `banned`. Content types:

- Resource: link or file with type, category, difficulty, time commitment, prerequisites, best part, warning, student note, multiple links, attachments.
- Article: Markdown, slug, excerpt, reading time, cover, draft or published.
- Collection: ordered list of resources and articles with per-item notes.
- Question / Answer: topic, optional linked resource, accepted answer, pinned answer, duplicate merge.
- Research is a tag/flag on existing content, not a separate silo.
- Profile: bio, faculty, graduation year, current role, socials, avatar, reputation.

Shared behavior across all content: tags, votes, bookmarks, comments (threaded, one level), report button, hide/unhide with reason, pending-review state, view counts.

## 3. Fix these v1 problems

1. Auth: short-lived access JWT in memory, httpOnly refresh cookie with rotation and server-side revocation (hash stored, reuse detection), CSRF protection for cookie endpoints, email verification, password reset, logout-everywhere. Optional config flag to restrict signup to `@ufaz.az`.
2. Search: Postgres `tsvector` + GIN + `pg_trgm` for typo tolerance; one unified ranked search endpoint across all content types with highlighted snippets and filters.
3. Polymorphism: a single `content_items` base table (joined-table inheritance) or per-type vote tables so FKs are real. Votes unique per (user, item) by constraint; denormalized counters updated atomically.
4. Uploads: storage interface (local named volume at `/app/media`, swappable to S3). MIME by content sniffing, size limits, image variants, virus-scan hook point, signed URLs. No blobs in DB.
5. Rate limiting: per-IP and per-user on auth, writes, votes, search (Redis). `429` with `Retry-After`.
6. Guest tracking: minimal, GDPR-friendly, no IP storage by default, retention job, documented privacy page. Guests get read access plus "sign in to continue" prompts.
7. Errors: one envelope `{code, message, fields?, request_id}`, request-ID middleware, structured JSON logs, Sentry hook.
8. Enums: `VARCHAR` + CHECK constraints (or native enums with tested migration); CI runs `alembic upgrade head` then `alembic check`.
9. Admin: split moderation, users, content, audit into separate modules; one audit-log table (actor, action, target, before/after diff, reason).
10. Repo hygiene: no `.next-cache` committed, `.gitignore`, pre-commit (black, prettier).
11. Markdown safety: sanitize server-side (nh3) and client-side; allow-list tags; `rel="noopener nofollow ugc"` on user links.
12. Pagination: cursor-based everywhere, consistent `Page[T]`, no unbounded lists.

## 4. Useful additions

- Bookmarks and reading lists (private by default, shareable).
- Notifications (in-app + optional email digest): replies, accepted answers, vote milestones, moderation actions.
- Course/subject taxonomy tied to UFAZ programs; resources attach to a course page (e.g. "Algorithms L2") with a "start here" path.
- Reputation: transparent point table, privileges by thresholds, anti-abuse (no self-votes, daily caps), public "how reputation works" page.
- Duplicate detection when asking/submitting a link (similar titles, canonical URL normalization).
- Link health checker background job; "reported broken" state.
- Link previews (title, favicon, OG image) server-side with SSRF protection (block private IPs, capped redirects, timeouts).
- Leaderboard, "contributor of the month", badges.
- RSS/Atom feeds for articles and per tag.
- Moderation queue with report reasons, bulk actions, appeal flow, user-visible moderation history.
- Command palette (Cmd+K) backed by unified search.
- Dark mode; i18n scaffolding (EN, AZ, FR, RU) with `next-intl`, EN complete.
- SEO: metadata, OG images, sitemap.xml, robots.txt, JSON-LD for articles.
- Analytics-lite: privacy-friendly page-view counts per item.
- Background jobs (arq + same Redis): emails, link checks, previews, digest, retention cleanup.
- Health/readiness endpoints, graceful shutdown.
- Seed script with realistic UFAZ-flavoured data; dev "login as" only when `APP_ENV=development`.

## 5. Frontend requirements

- Search-first homepage; feed tabs (Latest, Top, For you via followed tags).
- Pages: home, resources, articles, collections, research, ask, people, profile, submit wizard (single composer that picks type from content), course pages, bookmarks, notifications, settings, admin.
- Auth via a single `useSession` hook, silent refresh, route guards in middleware, no manual token handling anywhere.
- Every list: loading skeletons, empty state, error state with retry, optimistic updates for votes and bookmarks.
- Accessibility: WCAG 2.2 AA, keyboard-complete, focus management in modals/palette, `prefers-reduced-motion`, visible focus rings, landmarks. axe in e2e.
- Design: section 5b is a hard requirement. Build the design system and a `/design` style page before any feature page.
- Performance: LCP < 2.5s mid-range mobile, server components by default, `next/image`, route-level splitting.

## 5b. Design direction: "The Living Archive"

Must not look like generic SaaS, blog or Reddit. A university library catalogue crossed with a student's annotated field notebook, set in Baku with a French atelier sensibility. Handmade, curated, a little playful, fast and readable.

Personality: warm, witty, scholarly, student-made. Editorial typography, tactile paper, marginal notes, stamps, index cards. Never corporate, no purple gradients, no glassmorphism, no stock icon grids, no emoji labels.

Palette (CSS variables, light + dark, WCAG AA verified):
- Light "paper": base `#F6F1E7`, cards `#FBF8F1`, ink `#17140F`, muted `#6B6458`.
- Dark "night reading room": deep ink-blue `#0F1420` base, cream text.
- Accent Caspian teal-blue `#0E5A6B`; flame vermilion `#E4572E` sparingly (stamps, highlights, notifications, "new"); highlighter yellow `#F4D35E` for highlights/selection. Muted semantic colors.
- Content tints (tabs, stamps, spines): Resource teal, Article vermilion, Collection ochre, Question plum, Research forest green.

Typography (DECIDED — every face covers latin, latin-ext AND cyrillic so EN/AZ/FR/RU all render in the real fonts, no fallback): display serif **Piazzolla** (variable opsz + wght, expressive, used large and tight); body humanist sans **Commissioner** (variable wght, FLAR, VOLM, slnt); metadata **JetBrains Mono** in small caps like call numbers; marginalia script **Caveat** (only in Marginalia). Load all via next/font/google with subsets ["latin","latin-ext","cyrillic"], display swap. Do NOT use Fraunces or Instrument Sans (no Cyrillic). The glyph test must render AZ (Əə Iı İi Şş Çç Ğğ Öö Üü), FR (é è ê à ç œ « ») and RU (Ёё Щщ Ыы) samples. Fluid `clamp()` scale, optical sizing, hanging punctuation, small caps, tabular numbers, proper quotes, drop caps on article openings. Must support Azerbaijani (ə ı ş ç ğ ö ü) and French accents — test this.

Signature visual language:
1. Catalogue cards: index card with call-number ID (`RES-0421`, `ART-0087`), coloured top edge, SVG noise paper grain, slightly irregular hairline borders, small stamp (VERIFIED, NEW, EDITOR'S PICK, DEAD LINK) rotated 2-4°.
2. Marginalia: comments/student notes in the margin in a script font (Caveat, only here) with a hand-drawn connector; inline bubbles on mobile.
3. Highlighter: search matches and reader selections get a hand-drawn SVG highlighter swipe (animated draw-on); save highlights to notebook.
4. Spines and shelves: collections as a shelf of book spines (varying heights/colours) that pull out on hover/tap; resources page has a shelf view toggle beside list and grid.
5. Geometric Azerbaijani ornament: restrained original pattern system (carpet/architecture geometry) for dividers, empty states, hero backgrounds, loading, at 4-8% opacity.
6. Hand-drawn touches: 30-40 custom SVG illustrations/icons, loose consistent line style; witty microcopy ("Nothing here yet. Be the first to leave a footprint.").
7. Asymmetric editorial layouts: oversized section numerals, pull quotes, offset images, sticky side index, magazine homepage with one large featured piece, "this week on campus" strip, marquee of fresh tags. No uniform three-column card grid on the homepage.

Key screens: homepage (giant serif headline, live search like a catalogue drawer, question of the day, featured collection shelf, trending tags as luggage tags, contributor spotlights); search/Cmd+K full-screen card catalogue overlay grouped by type with coloured tabs; article reader (bookmark-ribbon progress, margin notes, read time, scroll-tracking TOC, continue reading); profile as library card / student passport with badge stamps and a stitched contribution heatmap; Q&A as annotated exam papers (accepted answer red "✓ checked", teacher-style score in margin); submit composer as notebook page whose ruling changes by type with live index-card preview; empty/loading/404/error states each with illustration and witty line; skeletons as blank index cards with shimmer.

Motion: cards lift and straighten on hover (rotate 1°→0), stamps thunk in, view-transition page slides, highlighter/underline draw-ons, spring drawers/modals. `prefers-reduced-motion` → fades. Animate only transform/opacity. 60fps on mid-range phones.

Delight: pen cursor over annotate areas (desktop), `?` shortcut overlay, konami easter egg, random resource shuffle, seasonal exam-week accent, print stylesheet for articles.

Design-system engineering rules:
- Tokens in one file (CSS variables + Tailwind theme): colour, type scale, spacing (4/8), radii (small, slightly uneven), elevation (paper shadows), z-index, motion durations/easings.
- 15-20 primitives first: Button, IconButton, Input, Textarea, Select, Combobox, Checkbox, Switch, Modal/Drawer, Toast, Tabs (index tabs), Badge, Stamp, Avatar, Skeleton, EmptyState, Pagination, Tooltip, Card (catalogue card), Callout, Marginalia. Documented at `/design` with light and dark previews.
- Accessible first (Radix or equivalent), keyboard-complete, AA in both themes, 44px touch targets, accent focus rings.
- Mobile-first, works at 360px. Textures inline SVG or <10KB assets.
- Fonts self-hosted, `font-display: swap`, subset Latin Extended; no layout shift; at most one animation library (Motion) only where needed.
- Ship three reference screens (home, article, profile) reviewed with Playwright screenshots at 360px and 1440px in both themes.

## 6. Quality bar

- Backend ≥85% coverage on services; tests for auth flows, permissions matrix (guest/user/verified/admin/muted/banned × every write endpoint), moderation, voting constraints, search ranking, migrations up/down.
- OpenAPI is the contract; CI fails if generated frontend types are stale.
- Security: OWASP ASVS L2 checklist, secure headers (CSP, HSTS), CORS allow-list, parameterized queries, secrets from env, `COOKIE_SECURE` true in prod, `pip-audit` and `npm audit` in CI.
- Docs: README (quickstart in 5 commands), docs/architecture.md (with diagram), docs/api.md generated, docs/runbook.md (deploy, backup/restore, rotate secrets), ADRs in docs/adr/.

## 6b. Infra: copy UFAZ GPA exactly

Reuse patterns file for file, renaming `ufazgpa`→`ufazhub` (domain placeholder `ufazhub.xyz`). Layout: `backend/`, `frontend/`, `backup/`, `scripts/`, `docs/`, `docker-compose.yml`, `docker-compose.prod.yml`, `nginx.conf`, `nginx.dev.conf`, `Makefile`, `deploy.env.example`, `DEPLOYMENT.md`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`. Root `.env` from `deploy.env.example`; `backend/.env` from `backend/.env.example`. Compose, nginx, Dockerfiles, backup sidecar, Makefile targets (incl. `playground` set), CI (backend: setup-uv, py3.13, `uv sync --frozen --dev`, black --check, pytest with Postgres service, alembic upgrade head + alembic check; frontend: Node 24, npm ci, prettier --check, lint, typecheck, vitest, build), pre-commit, DEPLOYMENT.md / AGENTS.md / PROJECT.md in the GPA shape. Target host: single AWS EC2 with prod compose + Let's Encrypt.

## 7. Delivery order

1. Repo scaffold, CI, tooling, design tokens, compose (Postgres, Redis, backup, nginx, certbot).
2. Design system (5b), then auth, sessions, email verification, rate limiting, error envelope, audit log.
3. Content base model, tags, votes, bookmarks, resources, with search (tsvector).
4. Articles, collections, comments, link previews, uploads.
5. Q&A, reputation, notifications.
6. Moderation, reports, admin panel.
7. Courses taxonomy, research flag, people directory, profiles.
8. i18n, SEO, feeds, dark mode, a11y pass, performance pass.
9. Hardening: load test search and feed, security review, docs, prod deploy readiness.

At the end of each slice record a short status in `docs/status.md`: what was built, what is deferred, decisions to review.
