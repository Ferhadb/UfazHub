# Runbook

All commands run from the repo root on the EC2 host. Prod compose: `docker compose -f docker-compose.yml -f docker-compose.prod.yml` (or put `PROD=1` in `make.env` and use `make`).

## Deploy

Merging to `main` runs CI; if green, the deploy job SSHes in, `git pull`s, rebuilds and restarts. By hand: `make deploy` (pulls, takes a backup, rebuilds, restarts). The backend container runs `alembic upgrade head` on start.

Check: `make ps`, `curl -s localhost:8000/api/ready` (expects `db` and `redis` ok), `make logs S=backend`.

## Rollback

`git log`, `git checkout <good-sha>`, `make update`. Migrations are not auto-reverted: if the bad release added one, run `docker compose exec backend alembic downgrade -1` first (only if the migration's downgrade is safe for data created since).

## Backup and restore

The `backup` sidecar writes `./backups/db_<stamp>.dump` daily (kept `BACKUP_KEEP_DAYS`) and copies it to Telegram when `BACKUP_TELEGRAM_CHAT_ID` is set. Details in `DEPLOYMENT.md`.

```bash
make backup-now
make backups
make db-restore FILE=backups/db_2026-10-20_0317.dump && make restart S=backend
```

Uploads live in the `media` Docker volume and are not in the dump: back up with
`docker run --rm -v ufazhub_media:/m -v "$PWD/backups":/b alpine tar czf /b/media.tgz -C /m .` (volume name is `<project>_media`; check `docker volume ls`).

## Rotate secrets

- `JWT_SECRET_KEY`: edit `backend/.env`, `make restart S=backend`. All access tokens become invalid; refresh cookies are server-side records and keep working.
- `POSTGRES_PASSWORD`: change it inside Postgres (`ALTER USER`), then in root `.env`, then `make update`.
- SMTP password and `TELEGRAM_BOT_TOKEN`: edit `backend/.env`, `make restart S=backend` (and `S=worker`, `S=backup`).
- After any rotation, never commit `.env` files.

## Certificates

Issued and renewed by the `certbot` service; see `DEPLOYMENT.md` for first issuance. After a renewal, `make restart S=nginx`.

## CSP

`nginx.conf` ships a baseline CSP that allows inline scripts and styles because Next.js hydration and the no-flash theme script are inline. To tighten it, issue per-request nonces from Next middleware and drop `'unsafe-inline'` from `script-src`.
