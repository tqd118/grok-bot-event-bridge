#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

pkill -f 'grok-bot-event-bridge/bus/relay.py' 2>/dev/null || true
pkill -f 'grok-bot-event-bridge/bots/bot_' 2>/dev/null || true
sleep 0.2

python3 bus/relay.py > /tmp/gbeb-relay.log 2>&1 &
RELAY_PID=$!
python3 bots/bot_b.py > /tmp/gbeb-bot-b.log 2>&1 &
BOT_B_PID=$!
sleep 0.4
python3 bots/bot_a.py > /tmp/gbeb-bot-a.log 2>&1
STATUS=$?

echo "===== relay ====="
cat /tmp/gbeb-relay.log
echo "===== bot-b ====="
cat /tmp/gbeb-bot-b.log
echo "===== bot-a ====="
cat /tmp/gbeb-bot-a.log

kill "$BOT_B_PID" "$RELAY_PID" 2>/dev/null || true
exit "$STATUS"
