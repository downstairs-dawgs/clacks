"""
Core messaging operations using Slack Web API.
"""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .exceptions import ClacksChannelNotFoundError, ClacksUserNotFoundError


def resolve_channel_id(client: WebClient, channel_identifier: str) -> str:
    """
    Resolve channel identifier to channel ID.
    Accepts channel ID (C...), channel name (#general or general).
    Returns channel ID or raises ClacksChannelNotFoundError if not found.
    """
    if channel_identifier.startswith("C") or channel_identifier.startswith("D"):
        return channel_identifier

    channel_name = channel_identifier.lstrip("#")

    # TODO(zomglings): Implement pagination via response_metadata.next_cursor
    # Currently only searches first page (up to 1000 channels)
    # Plan: Cache channel list in database to avoid repeated API calls
    try:
        response = client.conversations_list(
            types="public_channel,private_channel", limit=1000
        )
        for channel in response["channels"]:
            if channel["name"] == channel_name:
                return channel["id"]
    except SlackApiError as e:
        raise ClacksChannelNotFoundError(channel_identifier) from e

    raise ClacksChannelNotFoundError(channel_identifier)


def resolve_user_id(client: WebClient, user_identifier: str) -> str:
    """
    Resolve user identifier to user ID.
    Accepts user ID (U...), username (@username or username), or email.
    Returns user ID or raises ClacksUserNotFoundError if not found.
    """
    if user_identifier.startswith("U"):
        return user_identifier

    username = user_identifier.lstrip("@")

    # TODO(zomglings): Implement pagination via response_metadata.next_cursor
    # Currently only searches first page (100-200 users depending on tier)
    # Plan: Cache user list in database to avoid repeated API calls
    try:
        response = client.users_list()
        for user in response["members"]:
            if (
                user.get("name") == username
                or user.get("real_name") == username
                or user.get("profile", {}).get("email") == user_identifier
            ):
                return user["id"]
    except SlackApiError as e:
        raise ClacksUserNotFoundError(user_identifier) from e

    raise ClacksUserNotFoundError(user_identifier)


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
