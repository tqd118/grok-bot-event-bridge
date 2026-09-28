#!/usr/bin/env python3
"""Event bus: HTTP webhook relay (pub/sub without polling).

Bots subscribe with a webhook URL + channels. Publish fans out
immediately to matching subscribers via POST — no timers.
"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


HOST = "127.0.0.1"
PORT = 8765

# channel -> list of {bot_id, webhook}
_subs: dict[str, list[dict[str, str]]] = {}
_lock = threading.Lock()


def _json_response(handler: BaseHTTPRequestHandler, code: int, body: dict[str, Any]) -> None:
    data = json.dumps(body).encode()
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length else b"{}"
    return json.loads(raw.decode() or "{}")


def _deliver(webhook: str, event: dict[str, Any]) -> None:
    req = urllib.request.Request(
        webhook,
        data=json.dumps(event).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
    except urllib.error.URLError as exc:
        print(f"[relay] deliver failed → {webhook}: {exc}", flush=True)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[relay] {self.address_string()} {fmt % args}", flush=True)

    def do_GET(self) -> None:
        if self.path == "/health":
            with _lock:
                summary = {ch: [s["bot_id"] for s in subs] for ch, subs in _subs.items()}
            _json_response(self, 200, {"ok": True, "subscribers": summary})
            return
        _json_response(self, 404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path == "/subscribe":
            body = _read_json(self)
            bot_id = body["bot_id"]
            webhook = body["webhook"]
            channels = body.get("channels") or []
            with _lock:
                for ch in channels:
                    bucket = _subs.setdefault(ch, [])
                    bucket[:] = [s for s in bucket if s["bot_id"] != bot_id]
                    bucket.append({"bot_id": bot_id, "webhook": webhook})
            print(f"[relay] {bot_id} subscribed → {channels}", flush=True)
            _json_response(self, 200, {"ok": True})
            return

        if self.path == "/publish":
            event = _read_json(self)
            channel = event["channel"]
            with _lock:
                targets = list(_subs.get(channel, []))
            # Fan-out in background threads so publish returns immediately
            for sub in targets:
                if sub["bot_id"] == event.get("from"):
                    continue  # don't echo to publisher
                threading.Thread(
                    target=_deliver,
                    args=(sub["webhook"], event),
                    daemon=True,
                ).start()
            print(
                f"[relay] publish ch={channel} type={event.get('type')} "
                f"id={event.get('correlation_id')} → {len(targets)} sub(s)",
                flush=True,
            )
            _json_response(self, 200, {"ok": True, "delivered_to": len(targets)})
            return

        _json_response(self, 404, {"error": "not found"})


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[relay] listening on http://{HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
