#!/usr/bin/env python3
"""Bot A (personal) — requester on Redis pub/sub."""
from __future__ import annotations

import sys
import threading
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from redis_common import (  # noqa: E402
    CHANNEL_REPLIES,
    CHANNEL_REQUESTS,
    publish,
    subscribe_forever,
)

BOT_ID = "bot-a"
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
        CHANNEL_REQUESTS,
        {
            "type": "need_answer",
            "from": BOT_ID,
            "correlation_id": cid,
            "payload": {"question": question},
        },
    )
    print(f"[bot-a] published need_answer id={cid} q={question!r}", flush=True)
    if not done.wait(timeout):
        raise TimeoutError(f"no reply for {cid}")
    with _lock:
        event = _results.pop(cid)
        _waiters.pop(cid, None)
    return (event.get("payload") or {}).get("answer", "")


def main() -> None:
    print(f"[bot-a] starting (personal Redis bridge)", flush=True)
    t = threading.Thread(
        target=subscribe_forever,
        args=([CHANNEL_REPLIES], on_event, BOT_ID),
        daemon=True,
    )
    t.start()
    time.sleep(0.4)  # let subscribe settle (not a poll for messages)
    answer = ask("нужен ответ по X")
    print(f"[bot-a] RESULT: {answer}", flush=True)


if __name__ == "__main__":
    main()
