"""
Core listen operations using Slack Web API.
"""

import time
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

from slack_sdk import WebClient


def listen_channel(
    client: WebClient,
    channel_id: str,
    thread_ts: str | None = None,
    interval: float = 2.0,
    timeout: float | None = None,
    include_history: int = 0,
) -> Iterator[dict]:
    """
    Yield new messages as they appear in channel or thread.

    Args:
        client: Slack WebClient instance
        channel_id: Channel ID to listen to
        thread_ts: If provided, listen to thread replies instead of channel
        interval: Poll interval in seconds (default: 2.0)
        timeout: Exit after this many seconds (default: None = infinite)
        include_history: Include last N messages on start (default: 0)

    Yields:
        Message dicts with 'received_at' ISO timestamp added
    """
    start_time = time.monotonic()
    latest_ts: str | None = None

    # Fetch history if requested
    if include_history > 0:
        messages: list[Any]
        if thread_ts:
            response = client.conversations_replies(
                channel=channel_id, ts=thread_ts, limit=include_history
            )
            messages = response.get("messages", [])
            # First message is parent, rest are replies
            if len(messages) > 1:
                messages = messages[1:]  # Skip parent
            else:
                messages = []
        else:
            response = client.conversations_history(
                channel=channel_id, limit=include_history
            )
            messages = response.get("messages", [])

        # Messages come in reverse chronological order, reverse to chronological
        messages = list(reversed(messages))

        for msg in messages:
            msg["received_at"] = datetime.now(timezone.utc).isoformat()
            yield msg
            # Track latest timestamp seen
            msg_ts = msg.get("ts")
            if msg_ts and (latest_ts is None or msg_ts > latest_ts):
                latest_ts = msg_ts

    # If no history fetched, start from now
    if latest_ts is None:
        latest_ts = str(time.time())

    # Poll for new messages
    while True:
        if timeout is not None:
            elapsed = time.monotonic() - start_time
            if elapsed >= timeout:
                break

        time.sleep(interval)

        if thread_ts:
            response = client.conversations_replies(
                channel=channel_id, ts=thread_ts, oldest=latest_ts
            )
            messages = response.get("messages", [])
            # Filter out parent and already-seen messages
            messages = [m for m in messages if m.get("ts", "") > latest_ts]
        else:
            response = client.conversations_history(
                channel=channel_id, oldest=latest_ts
            )
            messages = response.get("messages", [])
            # Filter out already-seen messages (oldest is exclusive in our usage)
            messages = [m for m in messages if m.get("ts", "") > latest_ts]

        # Messages come in reverse chronological order, reverse to chronological
        messages = list(reversed(messages))

        for msg in messages:
            msg["received_at"] = datetime.now(timezone.utc).isoformat()
            yield msg
            # Track latest timestamp seen
            msg_ts = msg.get("ts")
            if msg_ts and (latest_ts is None or msg_ts > latest_ts):
                latest_ts = msg_ts
