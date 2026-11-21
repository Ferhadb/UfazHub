# db-backup sidecar — same pattern as backend/frontend images (built by the
# `backup` service in docker-compose.yml): Postgres client tools for pg_dump/
# pg_restore + curl for the Telegram off-site copy + the entrypoint script.
# See DEPLOYMENT.md → "Database backups".
FROM postgres:16-alpine

RUN apk add --no-cache curl

COPY --chmod=755 backup/db-backup.sh /usr/local/bin/db-backup.sh

ENTRYPOINT ["/usr/local/bin/db-backup.sh"]
