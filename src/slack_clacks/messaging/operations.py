"""
Core messaging operations using Slack Web API.
"""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def resolve_channel_id(client: WebClient, channel_identifier: str) -> str | None:
    """
    Resolve channel identifier to channel ID.
    Accepts channel ID (C...), channel name (#general or general).
    Returns channel ID or None if not found.
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
    except SlackApiError:
        pass

    return None


def resolve_user_id(client: WebClient, user_identifier: str) -> str | None:
    """
    Resolve user identifier to user ID.
    Accepts user ID (U...), username (@username or username), or email.
    Returns user ID or None if not found.
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
    except SlackApiError:
        pass

    return None


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
