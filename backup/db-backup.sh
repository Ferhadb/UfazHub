#!/bin/sh
# Daily Postgres backup: pg_dump custom format into /backups (host mount:
# ./backups/), plus an off-site copy sent to a Telegram chat via the existing
# bot token (TELEGRAM_BOT_TOKEN from backend/.env).
#
# Runs forever as the `backup` compose service: one dump every 24h
# (BACKUP_INTERVAL_SECONDS to override). On startup it checks the newest dump
# and skips the immediate dump when that backup is still fresh, so restarting
# the stack does not create another dump. One-off manual dump:
# `make backup-now`. Restore: `make db-restore FILE=backups/db_<stamp>.dump`.
#
# Credentials come from container env only: PG* are set by compose
# (POSTGRES_* from the root .env), BACKUP_KEEP_DAYS also from the root .env.
# The Telegram copy is best-effort: a failed send never deletes the local
# dump and simply retries on the next run.

set -u

DUMP_DIR="${BACKUP_DIR:-/backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
TG_CHAT="${BACKUP_TELEGRAM_CHAT_ID:-}"
TG_TOKEN="${TELEGRAM_BOT_TOKEN:-}"

log() { echo "[backup] $*"; }

# Print the age (in seconds) of the newest local dump. Returns non-zero when
# there is no dump yet, so the caller can take an initial backup.
latest_backup_age() {
  latest="$(ls -1t "$DUMP_DIR"/db_*.dump 2>/dev/null | head -n 1)"
  [ -n "$latest" ] || return 1

  mtime="$(stat -c %Y "$latest" 2>/dev/null)" || mtime=0
  now="$(date +%s)"
  age=$((now - mtime))
  [ "$age" -ge 0 ] || age=0
  printf '%s\n' "$age"
}

run_backup() {
  stamp="$(date -u +%F_%H%M)"
  file="$DUMP_DIR/db_${stamp}.dump"

  log "pg_dump ${PGDATABASE}@${PGHOST:-db} -> $file"
  if ! pg_dump -Fc --no-owner -f "$file"; then
    rm -f "$file"
    log "ERROR: pg_dump failed — existing dumps kept, retrying on next run"
    return 1
  fi
  log "dump done: $(du -h "$file" | cut -f1)"

  if [ -n "$TG_TOKEN" ] && [ -n "$TG_CHAT" ]; then
    if [ "$(wc -c < "$file")" -gt 49500000 ]; then
      log "WARN: dump is larger than Telegram's ~50MB bot upload limit"
    fi
    if curl -sf --max-time 300 \
      -F chat_id="$TG_CHAT" \
      -F caption="ufazhub DB backup $stamp" \
      -F "document=@$file" \
      "https://api.telegram.org/bot$TG_TOKEN/sendDocument" >/dev/null; then
      log "Telegram off-site copy sent"
    else
      log "WARN: Telegram send failed (auth/network/limit?) — local dump kept, retries next run"
    fi
  else
    log "Telegram copy skipped — need both TELEGRAM_BOT_TOKEN (backend/.env) and BACKUP_TELEGRAM_CHAT_ID (root .env)"
  fi

  old_count="$(find "$DUMP_DIR" -type f -name 'db_*.dump' -mtime +"$KEEP_DAYS" | wc -l)"
  if [ "$old_count" -gt 0 ]; then
    find "$DUMP_DIR" -type f -name 'db_*.dump' -mtime +"$KEEP_DAYS" -delete
    log "pruned $old_count dump(s) older than $KEEP_DAYS day(s)"
  fi
}

trap 'log "TERM received — exiting"; exit 0' TERM INT

if [ "${1:-loop}" = "run" ]; then
  run_backup
  exit $?
fi

log "loop starting: every ${INTERVAL}s — keep ${KEEP_DAYS}d local, off-site: Telegram"
while :; do
  if age="$(latest_backup_age)"; then
    if [ "$age" -lt "$INTERVAL" ]; then
      wait_for=$((INTERVAL - age))
      log "latest dump is ${age}s old — next backup in ${wait_for}s"
      sleep "$wait_for" &
      wait $!
      continue
    fi
    log "latest dump is ${age}s old — backup due"
  else
    log "no existing dump found — taking initial backup"
  fi

  run_backup || true
  log "next backup in ${INTERVAL}s"
  sleep "$INTERVAL" &
  wait $!
done
