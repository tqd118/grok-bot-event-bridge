#!/usr/bin/env bash
# Watch JSONL queue; on new to_helper line, POST webhook to wake Helper (send_task).
# Personal machine only. Fill webhook.env from Helper routine panel (you never paste the key into chat).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
QUEUE="${QUEUE:-$ROOT/queue/messages.jsonl}"
ENV_FILE="${ENV_FILE:-$ROOT/scripts/webhook.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  cat > "$ENV_FILE" << 'EON'
# Copy from Helper → Routines → "Bridge queue wake" panel:
WEBHOOK_URL=
WEBHOOK_KEY=
EON
  echo "Created $ENV_FILE — paste WEBHOOK_URL and WEBHOOK_KEY from the routine panel, then re-run."
  exit 1
fi
# shellcheck disable=SC1090
source "$ENV_FILE"
if [[ -z "${WEBHOOK_URL:-}" || -z "${WEBHOOK_KEY:-}" ]]; then
  echo "Set WEBHOOK_URL and WEBHOOK_KEY in $ENV_FILE"
  exit 1
fi

mkdir -p "$(dirname "$QUEUE")"
touch "$QUEUE"

wake() {
  # Fire-and-forget wake; Helper reads the queue itself
  curl -sS -X POST "$WEBHOOK_URL" \
    -H "Authorization: Bearer $WEBHOOK_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"source\":\"queue-watch\",\"queue\":\"$QUEUE\"}" \
    || echo "wake POST failed" >&2
}

echo "watching $QUEUE (inotify) → Helper webhook"
# Only wake when a new pending to_helper line appears
last_size=$(wc -c < "$QUEUE" || echo 0)
if command -v inotifywait >/dev/null; then
  while inotifywait -e modify,close_write,create "$QUEUE" >/dev/null 2>&1; do
    new_size=$(wc -c < "$QUEUE" || echo 0)
    if (( new_size > last_size )); then
      added=$(tail -c +$((last_size + 1)) "$QUEUE" || true)
      last_size=$new_size
      if echo "$added" | grep -q '"direction":"to_helper"'; then
        echo "$(date -Iseconds) wake Helper"
        wake
      fi
    else
      last_size=$new_size
    fi
  done
else
  echo "inotifywait not found; install inotify-tools. Falling back to 2s mtime check (still no Helper API poll)."
  while true; do
    new_size=$(wc -c < "$QUEUE" || echo 0)
    if (( new_size > last_size )); then
      added=$(tail -c +$((last_size + 1)) "$QUEUE" || true)
      last_size=$new_size
      if echo "$added" | grep -q '"direction":"to_helper"'; then
        echo "$(date -Iseconds) wake Helper"
        wake
      fi
    fi
    sleep 2
  done
fi
