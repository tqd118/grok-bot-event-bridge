#!/usr/bin/env python3
"""Bot A — requester: publishes need_answer, waits for reply event (no poll)."""
from __future__ import annotations

import sys
import threading
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import publish, serve_events, subscribe  # noqa: E402

BOT_ID = "bot-a"
HOST, PORT = "127.0.0.1", 9001
WEBHOOK = f"http://{HOST}:{PORT}/events"

_waiters: dict[str, threading.Event] = {}
_results: dict[str, dict] = {}
_lock = threading.Lock()


def on_event(event: dict) -> None:
    if event.get("type") != "answer":
        return
    cid = event.get("correlation_id")
    print(f"[bot-a] got answer id={cid}: {(event.get('payload') or {}).get('answer')!r}", flush=True)
    with _lock:
        _results[cid] = event
        ev = _waiters.get(cid)
    if ev:
        ev.set()


def ask(question: str, timeout: float = 10.0) -> str:
    cid = str(uuid.uuid4())
    done = threading.Event()
    with _lock:
        _waiters[cid] = done
    publish(
        {
            "channel": "requests",
            "type": "need_answer",
            "from": BOT_ID,
            "correlation_id": cid,
            "payload": {"question": question},
        }
    )
    print(f"[bot-a] published need_answer id={cid} q={question!r}", flush=True)
    # Wait on Event set by webhook — not a "is there news?" poll loop
    if not done.wait(timeout):
        raise TimeoutError(f"no reply for {cid}")
    with _lock:
        event = _results.pop(cid)
        _waiters.pop(cid, None)
    return (event.get("payload") or {}).get("answer", "")


def main() -> None:
    serve_events(HOST, PORT, on_event)
    for _ in range(50):
        try:
            subscribe(BOT_ID, WEBHOOK, ["replies"])
            break
        except Exception:
            time.sleep(0.1)
    else:
        raise SystemExit("relay not reachable")
    print(f"[bot-a] ready on {WEBHOOK}, subscribed to replies", flush=True)
    time.sleep(0.3)
    answer = ask("нужен ответ по X")
    print(f"[bot-a] RESULT: {answer}", flush=True)


if __name__ == "__main__":
    main()
