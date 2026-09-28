#!/usr/bin/env python3
"""Bot B — worker: listens for need_answer, publishes reply. No polling."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import publish, serve_events, subscribe  # noqa: E402

BOT_ID = "bot-b"
HOST, PORT = "127.0.0.1", 9002
WEBHOOK = f"http://{HOST}:{PORT}/events"


def on_event(event: dict) -> None:
    if event.get("type") != "need_answer":
        return
    q = (event.get("payload") or {}).get("question", "")
    cid = event.get("correlation_id")
    print(f"[bot-b] got need_answer id={cid} q={q!r}", flush=True)
    # Simulate work, then publish result on replies channel
    answer = f"Ответ от bot-b: обработал «{q}»"
    publish(
        {
            "channel": "replies",
            "type": "answer",
            "from": BOT_ID,
            "correlation_id": cid,
            "payload": {"answer": answer},
        }
    )
    print(f"[bot-b] published answer id={cid}", flush=True)


def main() -> None:
    serve_events(HOST, PORT, on_event)
    # wait until relay is up
    for _ in range(50):
        try:
            subscribe(BOT_ID, WEBHOOK, ["requests"])
            break
        except Exception:
            time.sleep(0.1)
    else:
        raise SystemExit("relay not reachable")
    print(f"[bot-b] ready on {WEBHOOK}, subscribed to requests", flush=True)
    while True:
        time.sleep(3600)  # idle; wake only via webhook


if __name__ == "__main__":
    main()
