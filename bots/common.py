#!/usr/bin/env python3
"""Shared helpers for bot clients."""
from __future__ import annotations

import json
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable


RELAY = "http://127.0.0.1:8765"


def post_json(url: str, body: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode() or "{}")


def publish(event: dict[str, Any]) -> None:
    post_json(f"{RELAY}/publish", event)


def subscribe(bot_id: str, webhook: str, channels: list[str]) -> None:
    post_json(
        f"{RELAY}/subscribe",
        {"bot_id": bot_id, "webhook": webhook, "channels": channels},
    )


def serve_events(
    host: str,
    port: int,
    on_event: Callable[[dict[str, Any]], None],
) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def do_POST(self) -> None:
            if self.path != "/events":
                self.send_response(404)
                self.end_headers()
                return
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            event = json.loads(raw.decode() or "{}")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            # Handle after ACK so relay isn't blocked
            threading.Thread(target=on_event, args=(event,), daemon=True).start()

    server = ThreadingHTTPServer((host, port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
