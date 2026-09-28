#!/usr/bin/env python3
"""Bot B (personal) — worker on Redis pub/sub."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from redis_common import (  # noqa: E402
    CHANNEL_REPLIES,
    CHANNEL_REQUESTS,
    publish,
    subscribe_forever,
)

BOT_ID = "bot-b"


def on_event(event: dict) -> None:
    if event.get("type") != "need_answer":
        return
    q = (event.get("payload") or {}).get("question", "")
    cid = event.get("correlation_id")
    print(f"[bot-b] got need_answer id={cid} q={q!r}", flush=True)
    answer = f"Ответ от bot-b: обработал «{q}»"
    publish(
        CHANNEL_REPLIES,
        {
            "type": "answer",
            "from": BOT_ID,
            "correlation_id": cid,
            "payload": {"answer": answer},
        },
    )
    print(f"[bot-b] published answer id={cid}", flush=True)


def main() -> None:
    print(f"[bot-b] starting (personal Redis bridge)", flush=True)
    subscribe_forever([CHANNEL_REQUESTS], on_event, BOT_ID)


if __name__ == "__main__":
    main()
