#!/usr/bin/env python3
"""Process one pending to_helper message (what Helper runs after wake)."""
from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_QUEUE = Path(__file__).resolve().parents[1] / "queue" / "messages.jsonl"


def load_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def answered_ids(rows: list[dict]) -> set[str]:
    return {r["id"] for r in rows if r.get("direction") == "to_colleague" and r.get("id")}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    p.add_argument(
        "--answer",
        help="If set, use this answer text; else a stub reply",
    )
    args = p.parse_args()

    rows = load_lines(args.queue)
    done = answered_ids(rows)
    pending = [
        r
        for r in rows
        if r.get("direction") == "to_helper"
        and r.get("status") == "pending"
        and r.get("id") not in done
    ]
    if not pending:
        print("NO_PENDING")
        return
    req = pending[0]
    q = (req.get("payload") or {}).get("question", "")
    answer = args.answer or f"Helper получил: «{q}»"
    reply = {
        "v": 1,
        "id": req["id"],
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "direction": "to_colleague",
        "status": "done",
        "from": "helper",
        "payload": {"answer": answer, "echo_question": q},
    }
    args.queue.parent.mkdir(parents=True, exist_ok=True)
    with args.queue.open("a", encoding="utf-8") as f:
        f.write(json.dumps(reply, ensure_ascii=False) + "\n")
    print(f"REPLIED id={req['id']}")
    print(answer)


if __name__ == "__main__":
    main()
