# Handoff: UFAZ Hub v2 (continue from slice 8)

You are continuing a rebuild of UFAZ Hub. Read these files first, in this order:

1. `docs/rebuild-spec.md`: the full spec and the source of truth. Section 5b covers design and fonts; section 7 lists the slices in delivery order.
2. `docs/status.md`: what each finished slice built, what it deferred, and the decisions to review.
3. `AGENTS.md`, `README.md`, `DEPLOYMENT.md`, `docs/architecture.md`, `docs/adr/`.

## Where things stand

- Slices 1 to 7 are done and committed on `main`. The working tree is clean. Nothing has been pushed.
- Last commit: `6442507 feat: courses, profiles, reading lists, link health (slice 7)`.
- Tests at the last commit: 352 backend tests (services coverage about 97%) and 193 frontend tests, all passing.
- Migrations `0001` to `0007` are in `backend/migrations/versions/`.
- **Next:** slice 8, then slice 9 (spec section 7, details below).

## Confirmed decisions (do not change)

- `ufazhub.xyz` is the real production domain.
- Fonts: Piazzolla for display, Commissioner for body text, JetBrains Mono for metadata, and Caveat for marginalia only. Every face loads subsets `latin`, `latin-ext` and `cyrillic` through `next/font/google`, with the options written as literals in each call. Never use Fraunces or Instrument Sans: they have no Cyrillic.
- Tests always run on real Postgres 16, never SQLite.
- API types are generated, never hand-written: run `make typegen`.
- Enums are stored as VARCHAR with CHECK constraints.
- The access token lives only in memory. The refresh token is an httpOnly cookie that rotates and has reuse detection.
- Infra mirrors the UFAZ GPA repo at `/Users/farhadick/Developer/farhad/UfazGpa/UFAZ_GPA-calculator`. Treat it as read-only.

## Environment

- macOS with no Docker. Start the local Postgres with `bash scripts/pg.sh start`: it listens on localhost:5433 as user `postgres` with trust auth, and has the databases `ufazhub_test` and `ufazhub_playground`.
- Start Redis with `redis-server --daemonize yes` if needed.
- Backend: `cd backend && uv run ...` (Python 3.13).
- Frontend: `cd frontend && npm ...`. TypeScript is pinned to 5.x for Next 15; keep it there.
- Playground (seeded app with both servers): `make playground`.

## Definition of green (run before every commit)

```bash
cd backend && uv run black --check app tests scripts
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://postgres@localhost:5433/ufazhub_test uv run pytest -q   # includes migration down/up + alembic check
cd frontend && npm run format:check && npm run lint && npm run typecheck && npm test && npm run build
make typegen && git diff --exit-code frontend/openapi.json frontend/src/lib/api/schema.d.ts
```

When everything is green:

1. Add a section for the slice to `docs/status.md`: built, deferred, decisions to review.
2. Commit with a conventional commit message. Do not push.

## Slice 8: i18n, SEO, feeds, dark mode, a11y, performance

- **i18n:** `next-intl` with EN complete and AZ/FR/RU scaffolding (message files with keys), plus a locale switcher. Add a glyph test that renders Azerbaijani (Əə Iı İi Şş Çç Ğğ Öö Üü), French (é è ê à ç œ « ») and Russian (Ёё Щщ Ыы) samples.
- **SEO:** `generateMetadata` on every page, OG images with `next/og`, `sitemap.xml`, `robots.txt`, and JSON-LD on articles.
- **Feeds:** RSS/Atom for articles and one feed per tag.
- **Dark mode:** a polished toggle, with both themes at WCAG AA.
- **Homepage:** finish it as a magazine layout:
  - a giant serif headline with a live search that behaves like a catalogue drawer
  - a question of the day
  - a featured collection shelf
  - trending tags styled as luggage tags
  - contributor spotlights
  - a "this week on campus" strip
  - a marquee of fresh tags
  - feed tabs: Latest, Top, For you
- **Delight details:**
  - a `?` shortcut overlay
  - a konami easter egg
  - a random-resource shuffle button
  - a pen cursor over annotate areas (desktop only)
  - an exam-week accent
- **Privacy:** add a privacy page. Count views per item without storing IPs, and add a retention cleanup job (arq cron).
- **States:** 404, error and empty states each get their own illustration and a witty line.
- **Accessibility pass:** landmarks, focus management, reduced motion.
- **Playwright:**
  - 3 e2e smoke flows with axe checks: browse and search; sign up or sign in, then vote; submit content.
  - Screenshots of home, article and profile at 360px and 1440px in light and dark, saved to `frontend/e2e/screenshots`.
  - Run against the playground. If browsers are missing, run `npx playwright install chromium`.
- **Performance:** server components by default, `next/image`, and a check of bundle sizes.

## Slice 9: hardening

- Add `scripts/loadtest.py` (asyncio + httpx) to load test search and feed against the playground. Record p50/p95 in `docs/status.md` and add any missing indexes.
- Write `docs/security.md` as an OWASP ASVS L2 checklist with a status for each item. Verify CSP, HSTS, CORS and cookie flags.
- Get `pip-audit` and `npm audit` clean, or document why something can't be fixed.
- Keep coverage at 85% or more on `app/services`.
- Generate `docs/api.md` from the OpenAPI schema with a script.
- Complete the runbook: deploy, backup/restore, and rotating the JWT secret, DB password and SMTP credentials.
- Verify the README quickstart, and finish the EC2 steps and `curl` checks in `DEPLOYMENT.md`.
- Docker is not installed on this machine, so check the compose files by parsing the YAML only.
- Write a final summary in `docs/status.md`.

## Known deferred items from earlier slices (pick up when convenient)

See the "Deferred" lists in `docs/status.md`. The main ones:

- Playwright e2e + axe for the pages from slices 3 to 7
- Comment editing, and reporting comments and users
- Admin UI for programs and courses
- A course picker in the submit composer
- An avatar upload UI
- Seed data for articles, collections and Q&A
