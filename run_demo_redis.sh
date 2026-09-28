#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Load personal-local config if present
if [[ -f config.env ]]; then
  set -a
  # shellcheck disable=SC1091
  source config.env
  set +a
fi

export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"

if ! command -v redis-cli >/dev/null || ! redis-cli ping >/dev/null 2>&1; then
  echo "Redis not running on ${REDIS_URL}."
  echo "Start local Redis (personal machine), e.g.:"
  echo "  redis-server --daemonize yes"
  echo "  # or: docker run -d --name gbeb-redis -p 6379:6379 redis:7-alpine"
  exit 1
fi

python3 -c 'import redis' 2>/dev/null || pip3 install -q -r requirements.txt

pkill -f 'bots/bot_b_redis.py' 2>/dev/null || true
pkill -f 'bots/bot_a_redis.py' 2>/dev/null || true
sleep 0.2

python3 bots/bot_b_redis.py > /tmp/gbeb-redis-b.log 2>&1 &
BOT_B_PID=$!
sleep 0.3
python3 bots/bot_a_redis.py > /tmp/gbeb-redis-a.log 2>&1
STATUS=$?

echo "===== bot-b ====="
cat /tmp/gbeb-redis-b.log
echo "===== bot-a ====="
cat /tmp/gbeb-redis-a.log

kill "$BOT_B_PID" 2>/dev/null || true
exit "$STATUS"
