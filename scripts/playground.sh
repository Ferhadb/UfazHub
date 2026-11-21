#!/usr/bin/env bash
# Local playground supervisor — local Postgres (scripts/pg.sh) + seeded fake data, hot reload.
#
#   bash scripts/playground.sh start     # seed if needed, then run API + web
#   bash scripts/playground.sh seed      # rebuild the fake dataset
#   bash scripts/playground.sh reset     # stop, wipe, rebuild
#   bash scripts/playground.sh stop
#   bash scripts/playground.sh status
#   bash scripts/playground.sh logs
#   bash scripts/playground.sh db        # psql shell
#   bash scripts/playground.sh accounts
#
# Everything generated lives in backend/.playground/ and is gitignored.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
STATE="$BACKEND/.playground"
ENV_FILE="$BACKEND/.env.playground"
ENV_EXAMPLE="$BACKEND/.env.playground.example"
DB_FILE="$STATE/seeded"  # marker: playground DB has been seeded
BACKEND_LOG="$STATE/backend.log"
FRONTEND_LOG="$STATE/frontend.log"
BACKEND_PID_FILE="$STATE/backend.pid"
FRONTEND_PID_FILE="$STATE/frontend.pid"

BACKEND_PORT="${PLAYGROUND_BACKEND_PORT:-8000}"
FRONTEND_PORT="${PLAYGROUND_FRONTEND_PORT:-3000}"

mkdir -p "$STATE"

log() { printf '%s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

ensure_env() {
  if [ ! -f "$ENV_FILE" ]; then
    [ -f "$ENV_EXAMPLE" ] || die "missing $ENV_EXAMPLE"
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    log "created $ENV_FILE (gitignored)"
  fi
}

load_env() {
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
}

pid_running() {
  local file="$1"
  [ -f "$file" ] || return 1
  local pid
  pid="$(cat "$file" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

port_busy() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

stop_pid_file() {
  local file="$1" label="$2" pid
  if [ ! -f "$file" ]; then
    return 0
  fi
  pid="$(cat "$file" 2>/dev/null || true)"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 40); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.25
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
    log "stopped $label (pid $pid)"
  fi
  rm -f "$file"
}

seed_db() {
  ensure_env
  load_env
  if pid_running "$BACKEND_PID_FILE" || pid_running "$FRONTEND_PID_FILE"; then
    die "playground is running; stop it first (bash scripts/playground.sh stop)"
  fi
  log "rebuilding playground database at $DB_FILE ..."
  bash "$ROOT/scripts/pg.sh" start >/dev/null
  ( cd "$BACKEND" && uv run python scripts/seed.py --reset ) && touch "$DB_FILE"
}

wait_for_http() {
  local url="$1" label="$2" pid="$3" logfile="$4"
  for _ in $(seq 1 120); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "  $label ready: $url"
      return 0
    fi
    if ! kill -0 "$pid" 2>/dev/null; then
      log "$label exited during startup. Last log lines:"
      tail -n 40 "$logfile" >&2 || true
      return 1
    fi
    sleep 1
  done
  log "$label did not become ready in time. Last log lines:"
  tail -n 40 "$logfile" >&2 || true
  return 1
}

cleanup() {
  stop_pid_file "$BACKEND_PID_FILE" "backend"
  stop_pid_file "$FRONTEND_PID_FILE" "frontend"
}

start() {
  ensure_env
  bash "$ROOT/scripts/pg.sh" start >/dev/null

  if pid_running "$BACKEND_PID_FILE" || pid_running "$FRONTEND_PID_FILE"; then
    log "playground already running."
    status
    return 0
  fi
  rm -f "$BACKEND_PID_FILE" "$FRONTEND_PID_FILE"

  if [ ! -f "$DB_FILE" ]; then
    seed_db
  fi

  if port_busy "$BACKEND_PORT"; then
    die "port $BACKEND_PORT is busy (another backend?). Stop it or set PLAYGROUND_BACKEND_PORT."
  fi
  if port_busy "$FRONTEND_PORT"; then
    die "port $FRONTEND_PORT is busy (another frontend?). Stop it or set PLAYGROUND_FRONTEND_PORT."
  fi

  load_env
  log "starting backend on http://127.0.0.1:$BACKEND_PORT ..."
  (
    cd "$BACKEND"
    set -a
    . "$ENV_FILE"
    set +a
    exec uv run uvicorn app.main:app \
      --host 127.0.0.1 \
      --port "$BACKEND_PORT" \
      --reload \
      --reload-dir app
  ) >"$BACKEND_LOG" 2>&1 &
  local backend_pid=$!
  echo "$backend_pid" >"$BACKEND_PID_FILE"

  if ! wait_for_http "http://127.0.0.1:$BACKEND_PORT/api/health" "backend" "$backend_pid" "$BACKEND_LOG"; then
    cleanup
    die "backend failed to start"
  fi

  log "starting frontend on http://127.0.0.1:$FRONTEND_PORT ..."
  (
    cd "$FRONTEND"
    export API_PROXY_TARGET="http://127.0.0.1:$BACKEND_PORT"
    exec ./node_modules/.bin/next dev --port "$FRONTEND_PORT"
  ) >"$FRONTEND_LOG" 2>&1 &
  local frontend_pid=$!
  echo "$frontend_pid" >"$FRONTEND_PID_FILE"

  if ! wait_for_http "http://127.0.0.1:$FRONTEND_PORT" "frontend" "$frontend_pid" "$FRONTEND_LOG"; then
    cleanup
    die "frontend failed to start"
  fi

  log ""
  log "============================================================"
  log "  UFAZ Hub — local playground"
  log "============================================================"
  log "  Web:     http://127.0.0.1:$FRONTEND_PORT"
  log "  API:     http://127.0.0.1:$BACKEND_PORT/api/docs"
  log "  DB:      postgres://localhost:5433/ufazhub_playground"
  log "  Logs:    $BACKEND_LOG"
  log "           $FRONTEND_LOG"
  log "============================================================"
  if [ -f "$STATE/accounts.txt" ]; then
    log ""
    cat "$STATE/accounts.txt"
  fi
  log ""
  log "Hot reload is ON for both apps. Press Ctrl-C to stop everything."
  log "Reset the fake data anytime: make playground-reset"
  log ""

  trap 'log ""; log "stopping playground..."; cleanup; exit 0' INT TERM
  while pid_running "$BACKEND_PID_FILE" && pid_running "$FRONTEND_PID_FILE"; do
    sleep 1
  done

  log "one of the dev servers exited; shutting the other down."
  tail -n 30 "$BACKEND_LOG" 2>/dev/null || true
  tail -n 30 "$FRONTEND_LOG" 2>/dev/null || true
  cleanup
  exit 1
}

status() {
  local backend_state="stopped" frontend_state="stopped"
  if pid_running "$BACKEND_PID_FILE"; then
    backend_state="running (pid $(cat "$BACKEND_PID_FILE"))"
  fi
  if pid_running "$FRONTEND_PID_FILE"; then
    frontend_state="running (pid $(cat "$FRONTEND_PID_FILE"))"
  fi
  log "backend:  $backend_state  http://127.0.0.1:$BACKEND_PORT"
  log "frontend: $frontend_state  http://127.0.0.1:$FRONTEND_PORT"
  log "database: $([ -f "$DB_FILE" ] && echo "$DB_FILE" || echo "not seeded")"
  log "logs:     $BACKEND_LOG"
  log "          $FRONTEND_LOG"
}

logs() {
  [ -f "$BACKEND_LOG" ] || die "no backend log yet; run make playground first"
  tail -f "$BACKEND_LOG" "$FRONTEND_LOG"
}

show_accounts() {
  [ -f "$STATE/accounts.txt" ] || die "no seeded accounts yet; run make playground-seed"
  cat "$STATE/accounts.txt"
}

usage() {
  sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
}

command="${1:-start}"
case "$command" in
  start|up) start ;;
  seed) seed_db ;;
  reset)
    cleanup
    rm -f "$DB_FILE"
    seed_db
    ;;
  stop|down) cleanup ;;
  status|ps) status ;;
  logs) logs ;;
  db)
    [ -f "$DB_FILE" ] || die "database not seeded; run make playground-seed"
    exec bash "$ROOT/scripts/pg.sh" psql ufazhub_playground
    ;;
  accounts) show_accounts ;;
  -h|--help|help) usage ;;
  *) usage; die "unknown command: $command" ;;
esac
