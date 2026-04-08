"""
Core messaging operations using Slack Web API.
"""

import re
import time
from datetime import datetime, timedelta, timezone, tzinfo
from typing import Any
from zoneinfo import ZoneInfo

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from sqlalchemy.orm import Session

from slack_clacks.messaging.exceptions import (
    ClacksChannelNotFoundError,
    ClacksUserNotFoundError,
)


def resolve_channel_id(
    client: WebClient,
    channel_identifier: str,
    session: Session | None = None,
    context_name: str | None = None,
) -> str:
    """
    Resolve channel identifier to channel ID.
    Accepts channel ID (C..., D..., G...), channel name (#general or general), or alias.
    Returns channel ID or raises ClacksChannelNotFoundError if not found.

    Resolution order:
    1. Check if already a Slack channel ID (C..., D..., G...)
    2. Check aliases (if session and context_name provided)
    3. Fall back to Slack API
    """
    if channel_identifier.startswith(("C", "D", "G")):
        return channel_identifier

    channel_name = channel_identifier.lstrip("#")

    if session is not None and context_name is not None:
        from slack_clacks.rolodex.operations import resolve_alias

        alias = resolve_alias(session, channel_name, context_name, "channel", "slack")
        if alias:
            return alias.target_id

    try:
        cursor: str | None = None
        while True:
            response = client.conversations_list(
                types="public_channel,private_channel", limit=200, cursor=cursor
            )
            for channel in response["channels"]:
                if channel["name"] == channel_name:
                    return channel["id"]
            response_metadata = response.get("response_metadata")
            cursor = response_metadata.get("next_cursor") if response_metadata else None
            if not cursor:
                break
    except SlackApiError as e:
        raise ClacksChannelNotFoundError(channel_identifier) from e

    raise ClacksChannelNotFoundError(channel_identifier)


def resolve_user_id(
    client: WebClient,
    user_identifier: str,
    session: Session | None = None,
    context_name: str | None = None,
) -> str:
    """
    Resolve user identifier to user ID.
    Accepts user ID (U...), username (@username or username), email, or alias.
    Returns user ID or raises ClacksUserNotFoundError if not found.

    Resolution order:
    1. Check if already a Slack user ID (U...)
    2. Check aliases (if session and context_name provided)
    3. Fall back to Slack API
    """
    if user_identifier.startswith("U"):
        return user_identifier

    username = user_identifier.lstrip("@")

    if session is not None and context_name is not None:
        from slack_clacks.rolodex.operations import resolve_alias

        alias = resolve_alias(session, username, context_name, "user", "slack")
        if alias:
            return alias.target_id

    try:
        cursor: str | None = None
        while True:
            response = client.users_list(cursor=cursor, limit=200)
            for user in response["members"]:
                if (
                    user.get("name") == username
                    or user.get("real_name") == username
                    or user.get("profile", {}).get("email") == user_identifier
                ):
                    return user["id"]
            response_metadata = response.get("response_metadata")
            cursor = response_metadata.get("next_cursor") if response_metadata else None
            if not cursor:
                break
    except SlackApiError as e:
        raise ClacksUserNotFoundError(user_identifier) from e

    raise ClacksUserNotFoundError(user_identifier)


def resolve_message_timestamp(timestamp_or_link: str) -> str:
    """
    Resolve message identifier to timestamp.
    Accepts raw timestamp (1767795445.338939) or Slack message link
    (https://workspace.slack.com/archives/C.../p1767795445338939).
    Returns timestamp or raises ValueError if format is invalid.
    """
    if timestamp_or_link.startswith("http"):
        match = re.search(r"/p(\d+)(?:\?|#|$)", timestamp_or_link)
        if not match:
            raise ValueError(f"Invalid Slack message link: {timestamp_or_link}")
        raw_ts = match.group(1)
        if len(raw_ts) <= 6:
            raise ValueError(f"Invalid timestamp in link: {timestamp_or_link}")
        return f"{raw_ts[:-6]}.{raw_ts[-6:]}"

    if "." not in timestamp_or_link:
        raise ValueError(
            f"Invalid timestamp format (missing decimal): {timestamp_or_link}"
        )
    try:
        float(timestamp_or_link)
        return timestamp_or_link
    except ValueError:
        raise ValueError(
            f"Invalid message identifier: {timestamp_or_link}. "
            "Expected timestamp (e.g., 1767795445.338939) or Slack message link."
        )


def parse_timestamp(value: str) -> str:
    """
    Parse a flexible timestamp value into a Slack-compatible Unix timestamp string.

    Accepts:
    - Slack message links (https://workspace.slack.com/archives/C.../p...)
    - Raw Slack timestamps (1770088169.782279 or 1770088169)
    - ISO 8601 datetimes (2024-01-15T10:00:00, with or without timezone)
    - Relative times (5 minutes ago, 1 hour ago, 3 days ago)

    Returns a Unix timestamp string suitable for Slack API oldest/latest params.
    Raises ValueError on unrecognized formats.
    """
    value = value.strip()
    if not value:
        raise ValueError("Empty timestamp value")

    if value.startswith("http"):
        return resolve_message_timestamp(value)

    try:
        float(value)
        return value
    except ValueError:
        pass

    relative_match = re.match(
        r"^(\d+)\s+(second|minute|hour|day|week)s?\s+ago$", value, re.IGNORECASE
    )
    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2).lower()
        multipliers = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
            "week": 604800,
        }
        offset = amount * multipliers[unit]
        return str(time.time() - offset)

    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return str(dt.timestamp())
    except ValueError:
        pass

    raise ValueError(
        f"Unrecognized timestamp format: {value}. "
        "Expected a Slack link, numeric timestamp, ISO 8601 datetime, "
        'or relative time (e.g., "5 minutes ago").'
    )


def open_dm_channel(client: WebClient, user_id: str) -> str | None:
    """
    Open a DM channel with a user.
    Returns channel ID or None if failed.
    """
    try:
        response = client.conversations_open(users=[user_id])
        return response["channel"]["id"]
    except SlackApiError:
        return None


def send_message(
    client: WebClient,
    channel: str,
    text: str,
    thread_ts: str | None = None,
):
    """
    Send a message to a channel or DM.
    Returns the Slack API response.
    """
    return client.chat_postMessage(channel=channel, text=text, thread_ts=thread_ts)


def read_messages(
    client: WebClient,
    channel: str,
    limit: int = 20,
    latest: str | None = None,
    oldest: str | None = None,
):
    """
    Read messages from a channel or DM.
    Returns the Slack API response with messages.
    """
    return client.conversations_history(
        channel=channel, limit=limit, latest=latest, oldest=oldest, inclusive=True
    )


def read_thread(
    client: WebClient,
    channel: str,
    thread_ts: str,
    limit: int = 100,
    oldest: str | None = None,
    latest: str | None = None,
):
    """
    Read messages from a thread.
    Returns the Slack API response with thread replies.
    """
    return client.conversations_replies(
        channel=channel,
        ts=thread_ts,
        limit=limit,
        oldest=oldest,
        latest=latest,
        inclusive=True,
    )


def get_recent_activity(
    client: WebClient, conversation_limit: int = 100, message_limit: int = 20
):
    """
    Get recent messages across all user's conversations.
    Returns a list of messages with their conversation context, sorted by timestamp.
    """
    conversations_response = client.users_conversations(
        types="public_channel,private_channel,mpim,im", limit=conversation_limit
    )

    all_messages = []
    for channel in conversations_response["channels"]:
        try:
            history_response = client.conversations_history(
                channel=channel["id"], limit=1
            )
            if history_response["messages"]:
                for message in history_response["messages"]:
                    message["channel_id"] = channel["id"]
                    message["channel_name"] = channel.get("name", channel["id"])
                    all_messages.append(message)
        except Exception:
            continue

    all_messages.sort(key=lambda m: float(m.get("ts", 0)), reverse=True)
    return all_messages[:message_limit]


def add_reaction(client: WebClient, channel: str, timestamp: str, emoji: str):
    """
    Add an emoji reaction to a message.
    Returns the Slack API response.
    """
    emoji = emoji.strip(":")
    return client.reactions_add(channel=channel, timestamp=timestamp, name=emoji)


def remove_reaction(client: WebClient, channel: str, timestamp: str, emoji: str):
    """
    Remove an emoji reaction from a message.
    Returns the Slack API response.
    """
    emoji = emoji.strip(":")
    return client.reactions_remove(channel=channel, timestamp=timestamp, name=emoji)


def delete_message(client: WebClient, channel: str, timestamp: str):
    """
    Delete a message from a channel or DM.
    Returns the Slack API response.
    Note: Users can only delete their own messages.
    """
    return client.chat_delete(channel=channel, ts=timestamp)


# Timezone abbreviation mapping to fixed UTC offsets (in hours).
# Using fixed offsets so "9pm CET" always means UTC+1, regardless of DST.
# Users who want DST-aware behavior should use IANA zones directly
# (e.g., "9pm Europe/Berlin").
_TZ_FIXED_OFFSETS: dict[str, int | float] = {
    "UTC": 0,
    "GMT": 0,
    "EST": -5,
    "EDT": -4,
    "CST": -6,
    "CDT": -5,
    "MST": -7,
    "MDT": -6,
    "PST": -8,
    "PDT": -7,
    "CET": 1,
    "CEST": 2,
    "EET": 2,
    "EEST": 3,
    "IST": 5.5,
    "JST": 9,
    "AEST": 10,
    "AEDT": 11,
    "NZST": 12,
    "NZDT": 13,
}


def parse_schedule_time(value: str) -> int:
    """
    Parse a flexible time specification into a future Unix timestamp (integer).

    Accepts:
    - Unix timestamp: "1773500000"
    - ISO 8601 datetime: "2026-03-12T21:00:00+01:00"
    - Relative future time: "in 2 hours", "in 30 minutes"
    - Time of day with timezone: "9pm CET", "21:00 EST", "2:30pm UTC"
      (resolves to the next occurrence of that time)

    Returns integer Unix timestamp for Slack's chat.scheduleMessage post_at param.
    Raises ValueError on unrecognized formats or times in the past.
    """
    value = value.strip()
    if not value:
        raise ValueError("Empty schedule time value")

    now = int(time.time())

    try:
        ts = int(float(value))
    except (ValueError, OverflowError):
        ts = None
    if ts is not None:
        if ts <= now:
            raise ValueError(f"Schedule time is in the past: {value}")
        return ts

    relative_match = re.match(
        r"^in\s+(\d+)\s+(second|minute|hour|day|week)s?$", value, re.IGNORECASE
    )
    if relative_match:
        amount = int(relative_match.group(1))
        if amount <= 0:
            raise ValueError("Relative time amount must be positive")
        unit = relative_match.group(2).lower()
        multipliers = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
            "week": 604800,
        }
        return now + amount * multipliers[unit]

    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        iso_ts = int(dt.timestamp())
    except ValueError:
        iso_ts = None
    if iso_ts is not None:
        if iso_ts <= now:
            raise ValueError(f"Schedule time is in the past: {value}")
        return iso_ts

    time_tz_match = re.match(
        r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s+([A-Za-z][A-Za-z0-9/+\-_]*)$",
        value,
        re.IGNORECASE,
    )
    if time_tz_match:
        hour = int(time_tz_match.group(1))
        minute = int(time_tz_match.group(2) or "0")
        ampm = time_tz_match.group(3)
        tz_str = time_tz_match.group(4)

        if ampm:
            ampm = ampm.lower()
            if hour < 1 or hour > 12:
                raise ValueError(
                    f"Invalid hour for 12-hour format: {hour}. Must be 1-12."
                )
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
        else:
            if hour < 0 or hour > 23:
                raise ValueError(
                    f"Invalid hour for 24-hour format: {hour}. Must be 0-23."
                )

        if minute < 0 or minute > 59:
            raise ValueError(f"Invalid minute: {minute}. Must be 0-59.")

        tz_upper = tz_str.upper()
        tz: tzinfo
        if tz_upper in _TZ_FIXED_OFFSETS:
            offset_hours = _TZ_FIXED_OFFSETS[tz_upper]
            tz = timezone(timedelta(hours=offset_hours))
        else:
            try:
                tz = ZoneInfo(tz_str)
            except KeyError:
                raise ValueError(f"Unknown timezone: {tz_str}")

        now_in_tz = datetime.now(tz)
        target = now_in_tz.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now_in_tz:
            target += timedelta(days=1)

        return int(target.timestamp())

    raise ValueError(
        f"Unrecognized schedule time format: {value}. "
        "Expected Unix timestamp, ISO 8601 datetime, "
        '"in N minutes/hours/days", or "9pm CET".'
    )


def search_messages(
    client: WebClient,
    query: str,
    sort: str = "timestamp",
    sort_dir: str = "desc",
    count: int = 20,
    page: int | None = None,
    cursor: str | None = None,
):
    """
    Search messages across the workspace.
    Returns the Slack API response.
    """
    kwargs: dict[str, Any] = {
        "query": query,
        "sort": sort,
        "sort_dir": sort_dir,
        "count": count,
    }
    if cursor is not None:
        kwargs["cursor"] = cursor
    elif page is not None:
        kwargs["page"] = page
    return client.search_messages(**kwargs)


def schedule_message(
    client: WebClient,
    channel: str,
    text: str,
    post_at: int,
    thread_ts: str | None = None,
):
    """
    Schedule a message for future delivery.
    Returns the Slack API response including scheduled_message_id.
    """
    return client.chat_scheduleMessage(
        channel=channel, text=text, post_at=post_at, thread_ts=thread_ts
    )
