# Operations runbook

Run commands from the repository root on the EC2 host. Set `PROD=1` in the local, gitignored `make.env` before using any `make` command below. Without it, use `docker compose -f docker-compose.yml -f docker-compose.prod.yml` explicitly. See [deployment setup](../DEPLOYMENT.md) for initial host, secrets, DNS, and TLS setup.

## Deploy and verify

A push to `main` deploys after CI passes: the SSH job pulls, builds, and starts production Compose. It does **not** take a backup or run smoke checks. For a deliberate manual deploy, `make deploy` pulls with `--ff-only`, runs `make backup-now`, then builds and recreates the stack. The backend applies Alembic migrations at startup.

```bash
make ps
curl -fsS http://127.0.0.1:8000/api/ready
curl -fsS https://ufazhub.xyz/api/ready
make logs S=backend
```

Readiness should report `status`, `db`, and `redis` as `ok`. Check the frontend, sign-in, and email delivery after changes to those paths. Review Nginx and worker logs if their services fail.

## Rollback

Take a fresh dump (`make backup-now`) and identify the last good commit before changing the checkout. Restore that commit with a deliberate branch or detached checkout, then run `make update`; verify readiness and key user flows. Migrations are **not** automatically reverted. Examine the migration's downgrade and data written since deployment before downgrading; an unsafe downgrade needs a forward fix or a coordinated restore. Do not run `git reset --hard` on a host with uncommitted work.

## Back up

The `backup` sidecar creates a daily custom-format PostgreSQL dump in `./backups`; local retention defaults to 14 days. Configure `BACKUP_TELEGRAM_CHAT_ID` in the root `.env` and `TELEGRAM_BOT_TOKEN` in `backend/.env` for a best-effort offsite copy. Check delivery and dump size in the backup logs. Run an additional dump before deploys or maintenance:

```bash
make backup-now
make backups
make logs S=backup
```

Back up uploads separately. Find the actual Docker volume name with `docker volume ls` (usually `<project>_media`), then archive it without changing its contents:

```bash
docker run --rm -v <project>_media:/media:ro -v "$PWD/backups":/backups alpine tar czf /backups/media_$(date -u +%F_%H%M).tgz -C /media .
```

Replace `<project>_media` with the actual volume name. Copy both the database and media archives off the instance. Keep an encrypted, access-controlled copy of the root `.env` and `backend/.env` through your normal secret store. Periodically test restoration on an isolated host; a successful `pg_dump` alone does not prove recovery.

## Restore

Restoring overwrites the target database. Choose a maintenance window, retain the current dump, and verify the intended backup file. If recovering from Telegram, download the dump into the host's `./backups/` first. The current `make db-restore` target assumes the default database and role names (`ufazhub` and `ufaz`) and asks for typed confirmation.

```bash
make backup-now
docker compose -f docker-compose.yml -f docker-compose.prod.yml stop nginx backend worker
make db-restore FILE=backups/db_YYYY-MM-DD_HHMM.dump
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d backend worker nginx
curl -fsS http://127.0.0.1:8000/api/ready
```

This stops public traffic and application database connections while leaving `db` and `backup` available for the Make target. Verify the database and application before reopening traffic. On a fresh host, set up secrets and start `db`, `redis`, and `backup` before restoring, then start the application services. Restore the matching media archive separately if uploads were lost; the DB dump contains references to files, not the files themselves. To avoid overwriting an existing media volume, inspect the archive and restore on an isolated host first.

## Rotate credentials

Changing an env file does not update a running container: use `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --force-recreate <service...>` after editing it. Avoid printing secret values in logs or shell history.

- **JWT_SECRET_KEY:** Generate a new random secret of at least 32 characters in `backend/.env`, then recreate `backend` and `worker`. Existing access JWTs fail immediately. Database-backed refresh sessions can still mint new access tokens. If `MEDIA_SIGNING_KEY` is empty, signed media URLs derive from the JWT secret and also become invalid until reissued; set a separate media signing key before routine JWT rotations if stable media links matter.
- **PostgreSQL password:** During a maintenance window, take and verify a dump. In the database container, use `psql -U ufaz -d postgres` and `\\password ufaz` to change the role password interactively. Update `POSTGRES_PASSWORD` in the root `.env`, then force recreate `db`, `backend`, `worker`, and `backup` with production Compose. Verify `/api/ready` and a new backup. Changing only the Compose variable does not change an existing PostgreSQL role password.
- **SMTP password:** Update `SMTP_PASSWORD` (and `SMTP_USERNAME` if needed) in `backend/.env`, recreate `worker` and `backend`, and test a verification/reset email. SMTP mail is sent by the worker.
- **Telegram bot token:** Update `TELEGRAM_BOT_TOKEN` in `backend/.env`, recreate `backup` and any bot-using application services, then run `make backup-now` and check the backup log for offsite delivery.

Keep env files out of Git. If a secret was exposed, revoke it at its provider as part of the rotation.

## Certificates

The certbot sidecar attempts renewal every 12 hours. Check its logs and the public certificate expiry. After renewal, restart Nginx so it loads the new files (`make restart S=nginx`). Initial issuance is documented in [DEPLOYMENT.md](../DEPLOYMENT.md).

## Content Security Policy

`nginx.conf` currently permits inline scripts and styles needed by Next.js hydration and the theme bootstrap. Tightening this requires per-request nonces in the application and an updated Nginx policy.
