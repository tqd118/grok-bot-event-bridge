#!/usr/bin/env python3
"""Shared Redis pub/sub helpers — event-driven, no polling loops."""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Callable

import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
CHANNEL_REQUESTS = os.environ.get("CHANNEL_REQUESTS", "bots:requests")
CHANNEL_REPLIES = os.environ.get("CHANNEL_REPLIES", "bots:replies")


def client() -> redis.Redis:
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


def publish(channel: str, event: dict[str, Any]) -> None:
    client().publish(channel, json.dumps(event, ensure_ascii=False))


def subscribe_forever(
    channels: list[str],
    on_event: Callable[[dict[str, Any]], None],
    bot_id: str,
) -> None:
    """Block on Redis pub/sub; wake only when a message arrives (not a poll)."""
    r = client()
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(*channels)
    print(f"[{bot_id}] subscribed → {channels}", flush=True)
    for message in pubsub.listen():
        if message.get("type") != "message":
            continue
        try:
            event = json.loads(message["data"])
        except json.JSONDecodeError:
            continue
        if event.get("from") == bot_id:
            continue
        on_event(event)
