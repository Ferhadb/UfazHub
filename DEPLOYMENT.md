# EC2 deployment

UFAZ Hub runs on one EC2 host with Docker Compose. Use both Compose files for production; the base file alone is an HTTP development stack with a backend bind mount. Production publishes Nginx on ports 80/443 and the API on `127.0.0.1:8000`. PostgreSQL and Redis have no host ports. Uploads live in the `media` Docker volume; database dumps live in `./backups` on the host.

## Prepare the host

1. Install Docker Engine with the Compose plugin and Git. Give the deploy user access to Docker and enough disk for images, the PostgreSQL volume, uploads, and backups. Restrict SSH to trusted addresses; allow inbound TCP 80 and 443.
2. Point the `ufazhub.xyz` A record at the EC2 public IPv4 and `www.ufazhub.xyz` at the same host (A or CNAME). Confirm both resolve before requesting a certificate.
3. Clone the repository as `~/ufazhub` (or set the `EC2_TARGET_DIR` GitHub secret to another existing checkout). The CI deploy job needs `EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY`, and optionally `EC2_PORT` and `EC2_TARGET_DIR` repository secrets. A push to `main` deploys only after backend and frontend checks pass. The job pulls, builds, recreates containers, and prunes unused images; it does not take a pre-deploy backup or run HTTP smoke checks.
4. From the repo root, copy `deploy.env.example` to `.env` and `backend/.env.example` to `backend/.env`. Set restrictive permissions (`chmod 600 .env backend/.env`). Set a strong unique `POSTGRES_PASSWORD` in the root `.env`; keep the default `POSTGRES_USER=ufaz` and `POSTGRES_DB=ufazhub` because the current restore Make target uses those names. In `backend/.env`, set a random `JWT_SECRET_KEY` (at least 32 characters), `APP_ENV=production`, `COOKIE_SECURE=true`, `SITE_URL=https://ufazhub.xyz`, and `CORS_ORIGINS=["https://ufazhub.xyz"]`. Set `SMTP_USERNAME`, `SMTP_PASSWORD`, `MAIL_FROM` and the correct SMTP host/port for email verification and password reset. Optionally set `SIGNUP_ALLOWED_DOMAINS=ufaz.az`, `SENTRY_DSN`, and a separate `MEDIA_SIGNING_KEY`. Compose supplies the database and Redis URLs to its services. Never commit either env file.
5. Create `make.env` containing `PROD=1` if using the runbook's `make` commands. This file is local to the host. Without it, always pass both Compose files as shown below.

Use a separate SMTP account or app password. The supplied example uses Gmail STARTTLS on port 587; sender address and mailbox policy must permit the configured `MAIL_FROM`.

## First TLS certificate and start

The production Nginx configuration requires certificate files before it can start. Wait for DNS to resolve and ensure port 80 is free. From the project root:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm -p 80:80 --entrypoint certbot certbot certonly --standalone -d ufazhub.xyz -d www.ufazhub.xyz --agree-tos -m you@example.com --no-eff-email
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

Replace the email. If an HTTP server already occupies port 80, stop it first. The certificate is stored in the `certbot_conf` volume shared with Nginx. The backend runs `alembic upgrade head` on startup, so wait for the backend to start before checking readiness; no separate migration command is required. Check logs if a service exits:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=100 backend worker nginx certbot
```

## Verify a deploy

Run these from the EC2 host after the stack starts:

```bash
curl -fsS http://127.0.0.1:8000/api/ready
curl -sSI http://ufazhub.xyz/ | head -n 1
curl -fsSI https://ufazhub.xyz/
curl -fsS https://ufazhub.xyz/api/ready
```

Readiness must return `{"status":"ok","db":"ok","redis":"ok"}`. HTTP should return `301` to HTTPS. The HTTPS command validates the certificate because it does not use `-k`; it should return a successful status and the Nginx security headers. For compression, request a nontrivial page with `curl -sS -D - -o /dev/null -H 'Accept-Encoding: gzip' https://ufazhub.xyz/` and inspect `Content-Encoding`. A `/_next/static/...` response should include `Cache-Control: public, max-age=31536000, immutable`; use a real asset URL from the page. Check signup and email delivery through a test account after SMTP configuration.

The production override removes the backend/worker source bind mounts. To inspect the merged configuration without starting containers, run `docker compose -f docker-compose.yml -f docker-compose.prod.yml config`.

## Update and rollback

With `PROD=1` in `make.env`, `make deploy` pulls with `--ff-only`, takes a database dump, builds, and recreates services. `make update` builds and recreates without pulling or backing up. The GitHub deploy workflow performs its own pull/build/up sequence as described above. For a manual update without `make.env`:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Review migrations before rolling back application code: migrations are applied on backend startup and are not automatically reversed. Follow [the runbook](docs/runbook.md) for rollback and secret rotation.

## Backups and restore

The `backup` service creates a PostgreSQL custom-format dump at `./backups/db_<UTC-stamp>.dump` on startup and roughly every 24 hours. It keeps local dumps for `BACKUP_KEEP_DAYS` (default 14). If `TELEGRAM_BOT_TOKEN` is set in `backend/.env` and `BACKUP_TELEGRAM_CHAT_ID` in the root `.env`, it also attempts a Telegram copy. Upload failures are logged; the local dump remains. Telegram Bot API upload size limits can prevent larger offsite dumps, so monitor the backup logs and arrange independent offsite storage as data grows.

The dump contains the database only. Back up the `media` volume and the two env files separately; Redis contains rate-limit counters and queued jobs, not source-of-truth content. See [the runbook](docs/runbook.md) for backup verification, restore, and secret rotation. A restore overwrites the live database, so use a maintenance window and a verified dump.

## Certificate renewal

The `certbot` service runs `certbot renew --webroot` every 12 hours. Nginx does not reload certificates automatically; restart Nginx after a successful renewal (`make restart S=nginx` with `PROD=1`, or the equivalent Compose command). Check `docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=100 certbot` and the served certificate expiry regularly.
