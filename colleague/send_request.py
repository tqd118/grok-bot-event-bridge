#!/usr/bin/env python3
"""Colleague client: append a to_helper request to the shared JSONL queue."""
from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_QUEUE = Path(__file__).resolve().parents[1] / "queue" / "messages.jsonl"


def main() -> None:
    p = argparse.ArgumentParser(description="Send a question to Helper via shared queue")
    p.add_argument("question", help="Question text for Helper")
    p.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    p.add_argument("--from", dest="sender", default="colleague")
    args = p.parse_args()

    args.queue.parent.mkdir(parents=True, exist_ok=True)
    msg = {
        "v": 1,
        "id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "direction": "to_helper",
        "status": "pending",
        "from": args.sender,
        "payload": {"question": args.question},
    }
    with args.queue.open("a", encoding="utf-8") as f:
        f.write(json.dumps(msg, ensure_ascii=False) + "\n")
    print(f"queued id={msg['id']}")
    print(f"queue={args.queue}")
    print("Waiting for a to_colleague line with the same id (use wait_reply.py).")


if __name__ == "__main__":
    main()
