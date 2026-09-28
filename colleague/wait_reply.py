#!/usr/bin/env python3
"""Colleague client: wait for Helper's reply (inotify if available, else short sleep)."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

DEFAULT_QUEUE = Path(__file__).resolve().parents[1] / "queue" / "messages.jsonl"


def find_reply(queue: Path, msg_id: str) -> dict | None:
    if not queue.exists():
        return None
    for line in queue.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("id") == msg_id and obj.get("direction") == "to_colleague":
            return obj
    return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("id", help="Request id from send_request.py")
    p.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    p.add_argument("--timeout", type=float, default=120.0)
    args = p.parse_args()

    deadline = time.time() + args.timeout
    # Prefer inotify via watchdog-like busy wait on mtime (no poll of Helper API)
    last_mtime = -1.0
    while time.time() < deadline:
        try:
            mtime = args.queue.stat().st_mtime if args.queue.exists() else -1.0
        except OSError:
            mtime = -1.0
        if mtime != last_mtime:
            last_mtime = mtime
            reply = find_reply(args.queue, args.id)
            if reply:
                print(json.dumps(reply, ensure_ascii=False, indent=2))
                ans = (reply.get("payload") or {}).get("answer")
                print(f"ANSWER: {ans}")
                return
        time.sleep(0.25)
    print("timeout waiting for reply", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
