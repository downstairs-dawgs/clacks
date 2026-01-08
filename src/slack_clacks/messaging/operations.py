"""
Core messaging operations using Slack Web API.
"""

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

    # Check aliases first (requires context for security)
    if session is not None and context_name is not None:
        from slack_clacks.rolodex.operations import resolve_alias

        alias = resolve_alias(session, channel_name, context_name, "channel", "slack")
        if alias:
            return alias.target_id

    # Fall back to API call with pagination
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

    # Check aliases first (requires context for security)
    if session is not None and context_name is not None:
        from slack_clacks.rolodex.operations import resolve_alias

        alias = resolve_alias(session, username, context_name, "user", "slack")
        if alias:
            return alias.target_id

    # Fall back to API call with pagination
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
    # Check if it's a Slack message link
    if timestamp_or_link.startswith("http"):
        # Link format: https://workspace.slack.com/archives/C08740LGAE6/p1767795445338939
        import re

        match = re.search(r"/p(\d+)(?:\?|#|$)", timestamp_or_link)
        if not match:
            raise ValueError(f"Invalid Slack message link: {timestamp_or_link}")
        raw_ts = match.group(1)
        # Insert decimal point 6 chars from end: p1767795445338939 -> 1767795445.338939
        if len(raw_ts) <= 6:
            raise ValueError(f"Invalid timestamp in link: {timestamp_or_link}")
        return f"{raw_ts[:-6]}.{raw_ts[-6:]}"

    # Assume it's a raw timestamp - validate format
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


def read_thread(client: WebClient, channel: str, thread_ts: str, limit: int = 100):
    """
    Read messages from a thread.
    Returns the Slack API response with thread replies.
    """
    return client.conversations_replies(channel=channel, ts=thread_ts, limit=limit)


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
