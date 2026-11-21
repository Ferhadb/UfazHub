# AWS Deployment

## Files to use

- `docker-compose.yml` (Postgres, Redis, backend, arq worker, frontend, backup, nginx — HTTP-only dev config)
- `docker-compose.prod.yml` (production overrides — image-built backend and worker, `media` volume for uploads, backend on 127.0.0.1 only, TLS nginx, certbot; use on EC2)
- `nginx.conf` (production TLS) and `nginx.dev.conf` (development HTTP, no certs needed)
- `backend/Dockerfile` (installs deps with `uv sync`)
- `backend/pyproject.toml` and `backend/uv.lock`
- `frontend/Dockerfile`
- `backend/.env` copied from `backend/.env.example`
- root `.env` copied from `deploy.env.example`

## Compose: development vs production

| Environment                                                     | Command                                                                         |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **Local / dev on server** (live-edit `backend/` via bind mount) | `docker compose up -d --build`                                                  |
| **Production EC2** (backend code from the image only)           | `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` |

Optional shortcut on the server:

```bash
export COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml
docker compose up -d --build
```

After changing only the backend or frontend image, rebuild and recreate that service (`nginx.conf` uses Docker DNS re-resolution so a nginx restart is optional):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d backend
```

After editing `nginx.conf` (gzip, cache and security headers, upstream DNS), reload nginx:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx
```

Verify gzip and caching: `curl -Ik -H 'Accept-Encoding: gzip' https://ufazhub.xyz/` should show `Content-Encoding: gzip`; a `/_next/static/...` asset should include `Cache-Control: public, max-age=31536000, immutable`. Both responses should include the HSTS (with `includeSubDomains`), content-type, frame, referrer, and Content Security Policy headers from `nginx.conf`.

**Verify prod mounts:** `docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend ls /app/app` should match the image (rebuild after git pull), not an out-of-date host checkout.

## On the EC2 instance

1. Copy the repository to the server.
2. In the project root, create the env files:
   - `cp deploy.env.example .env`
   - `cp backend/.env.example backend/.env`
3. Edit `backend/.env` and set:
   - `JWT_SECRET_KEY` (64 random characters; production refuses the default)
   - `APP_ENV=production`, `COOKIE_SECURE=true`, `SITE_URL=https://ufazhub.xyz`
   - `CORS_ORIGINS=["https://ufazhub.xyz"]`
   - `SMTP_USERNAME`, `SMTP_PASSWORD`, `MAIL_FROM` for verification and reset emails
   - `SIGNUP_ALLOWED_DOMAINS=ufaz.az` to restrict signup to university addresses (optional)
   - `SENTRY_DSN` (optional)
   - `DATABASE_URL` and `REDIS_URL` can stay as-is: compose overrides them
4. Uploads are stored in the `media` named volume (`/app/media`), shared by backend and worker. It is not part of the database dump; see `docs/runbook.md` for backing it up.
5. After deploy, run `docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend alembic upgrade head` (the backend container also runs migrations automatically on start).
6. Edit `.env` if you want custom database credentials.
7. Start the stack (production compose):
   - `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
8. Check logs:
   - `docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f backend`
   - `docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f frontend`

For Gmail SMTP, create a Google app password for the mailbox that sends email. The backend uses `smtp.gmail.com` on port `587` with STARTTLS.

## Database backups (daily, local + Telegram)

The compose stack includes a `backup` sidecar (`backup/Dockerfile` running Postgres client
tools over `backup/db-backup.sh`). Every run:

1. `pg_dump -Fc` (custom format) of the live DB into `./backups/db_<UTC-stamp>.dump`
   on the host — one dump every 24h. On container startup it checks the newest dump
   and skips the immediate dump when that backup is still fresh, so restarting the
   stack does not create another dump.
2. Sends that dump as a file to a Telegram chat (off-site copy, **best-effort**: a failed
   send only logs a warning and retries on the next run — the local file is always kept).
3. Prunes local dumps older than `BACKUP_KEEP_DAYS` days (default 14).

The off-site copy is what matters if the AWS account/instance becomes unreachable: dumps
stay archived in the Telegram chat and download from any device. Telegram's bot upload
limit is 50 MB per file — the current DB is far below it; larger dumps still land locally
with a WARN in the logs (the local file is always kept).

### Enable the Telegram copy

1. `backend/.env` already carries `TELEGRAM_BOT_TOKEN` (the same bot as the in-app bot).
2. Get a target chat id: message **@userinfobot** (it replies with your chat id), or make
   the bot an **admin** of a private channel dedicated to backups and use that channel's
   id (negative, `-100…`). A channel works even in webhook mode, unlike `getUpdates`.
3. In the root `.env` (see `deploy.env.example`): `BACKUP_TELEGRAM_CHAT_ID=<id>` and
   optionally `BACKUP_KEEP_DAYS=14`.
4. Recreate the stack: `make update` — then watch `make logs S=backup` for
   "dump done" and "Telegram off-site copy sent".

Without the token/chat id backups still run locally every day; the log just says the
Telegram copy was skipped.

### Manual ops

```bash
make backup-now    # one dump immediately (still uploaded to Telegram if configured)
make backups       # list dumps inside ./backups/
```

### Restore

Telegram chat → download a dump → `scp` it into the server's `./backups/`, then:

```bash
make db-restore FILE=backups/db_2026-10-20_0317.dump
make restart S=backend
```

`db-restore` drops and recreates the `ufazhub` database and rebuilds it from the dump —
everything else (Redis, the `media` volume, secrets files) is unaffected; the backend just needs a
restart to pick up fresh connections. Restoring into a *fresh* server: start the stack
first (creates an empty DB), then run the same two commands.

## HTTPS (Let's Encrypt + Nginx in Docker)

This repo serves traffic through the `nginx` container. HTTPS is enabled by:

- Sharing `/etc/letsencrypt` and the ACME challenge webroot with a `certbot` container
- Serving `/.well-known/acme-challenge/` on port 80
- Redirecting all other HTTP traffic to HTTPS

### Prerequisites (DNS)

- `A` record: `ufazhub.xyz` -> your EC2 public IPv4
- `CNAME` record: `www` -> `ufazhub.xyz`

Wait until these resolve from your laptop:

- `nslookup ufazhub.xyz`
- `nslookup www.ufazhub.xyz`

### First certificate issuance

The base compose runs an HTTP-only nginx (`nginx.dev.conf`), so a fresh machine boots without any certificates. But the first certificate needs port 80, so issue it **standalone** while nginx is down:

1. Stop nginx (a base `docker compose up` may have started it):
   - `docker compose stop nginx`
2. Run certbot standalone (replace the email):
   - `docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm -p 80:80 certbot certonly --standalone -d ufazhub.xyz -d www.ufazhub.xyz --agree-tos -m you@example.com --no-eff-email`
3. Bring the full production stack up (nginx now finds the issued cert and serves TLS):
   - `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`

2. Run Certbot once to issue the cert (replace the email):
   - `docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm certbot certonly --webroot -w /var/www/certbot \
  -d ufazhub.xyz -d www.ufazhub.xyz \
  --email you@example.com --agree-tos --no-eff-email`

3. Reload nginx:
   - `docker compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx`

4. Verify:
   - `curl -I http://ufazhub.xyz` (should be 301 -> https)
   - `curl -Ik https://ufazhub.xyz` (should be 200/301 with valid cert)

### Auto-renewal

The `certbot` service runs `certbot renew` every 12 hours. After renewal, Nginx needs a reload.
The simplest approach is a periodic restart of the nginx container (e.g. daily via cron), or you
can change the renew loop to run `nginx -s reload` if you switch to a combined image.

Minimal manual check:

- `docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f certbot`

## Notes

- Docker builds use BuildKit cache mounts in `backend/Dockerfile` and `frontend/Dockerfile` (faster rebuilds when only app code changes). BuildKit is on by default in Docker 23+; if builds fail on an older host, run `export DOCKER_BUILDKIT=1` before `docker compose build`.
- On EC2, always include `docker-compose.prod.yml` so the backend runs code baked into the image (`./backend:/app` in the base file is for local dev only) and the backend port is **published on `127.0.0.1` only** — nginx (80/443) is the public entrypoint; SSH in and curl `localhost:8000` for direct debugging.
- Locally, `docker compose up` serves plain HTTP on port 80 through `nginx.dev.conf` (no certificates needed); `next dev` still talks to the published `localhost:8000` backend.
- The app is exposed on ports `80`/`443` through Nginx in production.
- API requests from the browser go to `/api` and are proxied to FastAPI.
- The backend runs Alembic migrations automatically before Uvicorn starts.
- **Redis** holds rate-limit counters and the arq job queue. Compose sets `REDIS_URL=redis://redis:6379/0` for the backend and worker services.
- The `worker` service runs `arq app.worker.WorkerSettings` (emails, link checks, previews, digests, retention).
- Backend Python dependencies are installed with **uv** (`uv sync --frozen` into `/usr/local` via `UV_PROJECT_ENVIRONMENT`), not `pip install -r requirements.txt`.
