#!/usr/bin/env bash
# Local Postgres 16 for tests and the playground, without Docker.
#
#   bash scripts/pg.sh start   # init (once) + start on :5433, create databases
#   bash scripts/pg.sh stop
#   bash scripts/pg.sh status
#   bash scripts/pg.sh psql [db]
#
# Data lives in backend/.pgtest/ (gitignored). Needs Postgres 16 binaries:
# macOS `brew install postgresql@16`, Debian/Ubuntu `apt install postgresql-16`.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="$ROOT/backend/.pgtest/data"
LOG="$ROOT/backend/.pgtest/postgres.log"
PORT="${PGTEST_PORT:-5433}"
export LC_ALL="${LC_ALL:-en_US.UTF-8}"

for d in /opt/homebrew/opt/postgresql@16/bin /usr/local/opt/postgresql@16/bin /usr/lib/postgresql/16/bin; do
  [ -x "$d/pg_ctl" ] && PATH="$d:$PATH" && break
done
command -v pg_ctl >/dev/null || { echo "error: Postgres 16 binaries not found" >&2; exit 1; }

case "${1:-start}" in
  start)
    mkdir -p "$(dirname "$DATA")"
    [ -d "$DATA" ] || initdb -D "$DATA" -U postgres --auth=trust -E UTF8 >/dev/null
    pg_ctl -D "$DATA" status >/dev/null 2>&1 || pg_ctl -D "$DATA" -o "-p $PORT -k /tmp" -l "$LOG" -w start >/dev/null
    for db in ufazhub_test ufazhub_playground; do
      psql -h localhost -p "$PORT" -U postgres -tAc "select 1 from pg_database where datname='$db'" | grep -q 1 \
        || createdb -h localhost -p "$PORT" -U postgres "$db"
    done
    echo "postgres ready on localhost:$PORT (databases: ufazhub_test, ufazhub_playground)"
    ;;
  stop) pg_ctl -D "$DATA" -m fast stop ;;
  status) pg_ctl -D "$DATA" status ;;
  psql) exec psql -h localhost -p "$PORT" -U postgres "${2:-ufazhub_playground}" ;;
  *) sed -n '2,10p' "$0"; exit 1 ;;
esac
