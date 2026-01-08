"""
Database operations for rolodex.
"""

from datetime import UTC, datetime

from slack_sdk import WebClient
from sqlalchemy import or_
from sqlalchemy.orm import Session

from slack_clacks.rolodex.models import Alias, RolodexChannel, RolodexUser


def add_user(
    session: Session,
    workspace_id: str,
    user_id: str,
    username: str | None = None,
    real_name: str | None = None,
    email: str | None = None,
) -> RolodexUser:
    """Add or update a user in the rolodex."""
    existing = (
        session.query(RolodexUser)
        .filter(
            RolodexUser.user_id == user_id,
            RolodexUser.workspace_id == workspace_id,
        )
        .first()
    )

    if existing:
        if username is not None:
            existing.username = username
        if real_name is not None:
            existing.real_name = real_name
        if email is not None:
            existing.email = email
        existing.last_updated = datetime.now(UTC)
        session.flush()
        return existing

    user = RolodexUser(
        user_id=user_id,
        workspace_id=workspace_id,
        username=username,
        real_name=real_name,
        email=email,
        last_updated=datetime.now(UTC),
    )
    session.add(user)
    session.flush()
    return user


def add_channel(
    session: Session,
    workspace_id: str,
    channel_id: str,
    channel_name: str | None = None,
    is_private: bool = False,
) -> RolodexChannel:
    """Add or update a channel in the rolodex."""
    existing = (
        session.query(RolodexChannel)
        .filter(
            RolodexChannel.channel_id == channel_id,
            RolodexChannel.workspace_id == workspace_id,
        )
        .first()
    )

    if existing:
        if channel_name is not None:
            existing.channel_name = channel_name
        existing.is_private = is_private
        existing.last_updated = datetime.now(UTC)
        session.flush()
        return existing

    channel = RolodexChannel(
        channel_id=channel_id,
        workspace_id=workspace_id,
        channel_name=channel_name,
        is_private=is_private,
        last_updated=datetime.now(UTC),
    )
    session.add(channel)
    session.flush()
    return channel


def get_user(
    session: Session,
    workspace_id: str,
    identifier: str,
) -> RolodexUser | None:
    """
    Lookup user by user_id, username, or email.
    Returns first match or None.
    """
    # Try user_id first (starts with U)
    if identifier.startswith("U"):
        user = (
            session.query(RolodexUser)
            .filter(
                RolodexUser.user_id == identifier,
                RolodexUser.workspace_id == workspace_id,
            )
            .first()
        )
        if user:
            return user

    # Strip @ prefix for username lookup
    username = identifier.lstrip("@")

    return (
        session.query(RolodexUser)
        .filter(
            RolodexUser.workspace_id == workspace_id,
            or_(
                RolodexUser.username == username,
                RolodexUser.email == identifier,
            ),
        )
        .first()
    )


def get_channel(
    session: Session,
    workspace_id: str,
    identifier: str,
) -> RolodexChannel | None:
    """
    Lookup channel by channel_id or channel_name.
    Returns first match or None.
    """
    # Try channel_id first (starts with C or D or G)
    if identifier.startswith(("C", "D", "G")):
        channel = (
            session.query(RolodexChannel)
            .filter(
                RolodexChannel.channel_id == identifier,
                RolodexChannel.workspace_id == workspace_id,
            )
            .first()
        )
        if channel:
            return channel

    # Strip # prefix for channel name lookup
    channel_name = identifier.lstrip("#")

    return (
        session.query(RolodexChannel)
        .filter(
            RolodexChannel.workspace_id == workspace_id,
            RolodexChannel.channel_name == channel_name,
        )
        .first()
    )


def list_users(
    session: Session,
    workspace_id: str,
    limit: int = 100,
    offset: int = 0,
) -> list[RolodexUser]:
    """List all users for a workspace."""
    return (
        session.query(RolodexUser)
        .filter(RolodexUser.workspace_id == workspace_id)
        .order_by(RolodexUser.username)
        .limit(limit)
        .offset(offset)
        .all()
    )


def list_channels(
    session: Session,
    workspace_id: str,
    limit: int = 100,
    offset: int = 0,
) -> list[RolodexChannel]:
    """List all channels for a workspace."""
    return (
        session.query(RolodexChannel)
        .filter(RolodexChannel.workspace_id == workspace_id)
        .order_by(RolodexChannel.channel_name)
        .limit(limit)
        .offset(offset)
        .all()
    )


def search_users(
    session: Session,
    workspace_id: str,
    query: str,
    limit: int = 100,
) -> list[RolodexUser]:
    """Search users by username, real_name, or email."""
    pattern = f"%{query}%"
    return (
        session.query(RolodexUser)
        .filter(
            RolodexUser.workspace_id == workspace_id,
            or_(
                RolodexUser.username.ilike(pattern),
                RolodexUser.real_name.ilike(pattern),
                RolodexUser.email.ilike(pattern),
            ),
        )
        .order_by(RolodexUser.username)
        .limit(limit)
        .all()
    )


def search_channels(
    session: Session,
    workspace_id: str,
    query: str,
    limit: int = 100,
) -> list[RolodexChannel]:
    """Search channels by channel_name."""
    pattern = f"%{query}%"
    return (
        session.query(RolodexChannel)
        .filter(
            RolodexChannel.workspace_id == workspace_id,
            RolodexChannel.channel_name.ilike(pattern),
        )
        .order_by(RolodexChannel.channel_name)
        .limit(limit)
        .all()
    )


def remove_user(
    session: Session,
    workspace_id: str,
    identifier: str,
) -> bool:
    """Remove a user from the rolodex. Returns True if removed, False if not found."""
    user = get_user(session, workspace_id, identifier)
    if user:
        session.delete(user)
        session.flush()
        return True
    return False


def remove_channel(
    session: Session,
    workspace_id: str,
    identifier: str,
) -> bool:
    """Remove a channel from the rolodex. Returns True if removed."""
    channel = get_channel(session, workspace_id, identifier)
    if channel:
        session.delete(channel)
        session.flush()
        return True
    return False


def clear_rolodex(
    session: Session,
    workspace_id: str,
) -> tuple[int, int]:
    """Clear all rolodex entries for a workspace. Returns (users, channels) deleted."""
    users_deleted = (
        session.query(RolodexUser)
        .filter(RolodexUser.workspace_id == workspace_id)
        .delete()
    )
    channels_deleted = (
        session.query(RolodexChannel)
        .filter(RolodexChannel.workspace_id == workspace_id)
        .delete()
    )
    session.flush()
    return users_deleted, channels_deleted


def sync_users(
    session: Session,
    client: WebClient,
    workspace_id: str,
) -> int:
    """
    Sync all users from Slack API to rolodex.
    Returns number of users synced.
    """
    count = 0
    cursor: str | None = None

    while True:
        response = client.users_list(cursor=cursor, limit=200)

        for member in response["members"]:
            if member.get("deleted"):
                continue
            profile = member.get("profile", {})
            add_user(
                session,
                workspace_id=workspace_id,
                user_id=member["id"],
                username=member.get("name"),
                real_name=member.get("real_name"),
                email=profile.get("email") if profile else None,
            )
            count += 1

        response_metadata = response.get("response_metadata")
        cursor = response_metadata.get("next_cursor") if response_metadata else None
        if not cursor:
            break

    return count


def sync_channels(
    session: Session,
    client: WebClient,
    workspace_id: str,
) -> int:
    """
    Sync all channels from Slack API to rolodex.
    Returns number of channels synced.
    """
    count = 0
    cursor: str | None = None

    while True:
        response = client.conversations_list(
            cursor=cursor,
            limit=200,
            types="public_channel,private_channel",
        )

        for channel in response["channels"]:
            add_channel(
                session,
                workspace_id=workspace_id,
                channel_id=channel["id"],
                channel_name=channel.get("name"),
                is_private=channel.get("is_private", False),
            )
            count += 1

        response_metadata = response.get("response_metadata")
        cursor = response_metadata.get("next_cursor") if response_metadata else None
        if not cursor:
            break

    return count


# --- Alias operations ---


def add_alias(
    session: Session,
    alias: str,
    platform: str,
    target_id: str,
    target_type: str,
    context: str,
) -> Alias:
    """
    Add an alias. Raises ValueError if alias already exists.
    Aliases are globally unique regardless of platform or context.
    """
    existing = session.query(Alias).filter(Alias.alias == alias).first()
    if existing:
        raise ValueError(f"Alias '{alias}' already exists")

    new_alias = Alias(
        alias=alias,
        platform=platform,
        target_id=target_id,
        target_type=target_type,
        context=context,
    )
    session.add(new_alias)
    session.flush()
    return new_alias


def get_alias(
    session: Session,
    alias: str,
    context: str | None = None,
) -> Alias | None:
    """
    Lookup an alias by name.
    If context is provided, only returns the alias if it matches the context.
    """
    query = session.query(Alias).filter(Alias.alias == alias)
    if context is not None:
        query = query.filter(Alias.context == context)
    return query.first()


def list_aliases(
    session: Session,
    context: str | None = None,
    platform: str | None = None,
    target_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Alias]:
    """List aliases with optional filtering by context, platform, or target_type."""
    query = session.query(Alias)
    if context is not None:
        query = query.filter(Alias.context == context)
    if platform is not None:
        query = query.filter(Alias.platform == platform)
    if target_type is not None:
        query = query.filter(Alias.target_type == target_type)
    return query.order_by(Alias.alias).limit(limit).offset(offset).all()


def remove_alias(
    session: Session,
    alias: str,
) -> bool:
    """Remove an alias. Returns True if removed, False if not found."""
    existing = session.query(Alias).filter(Alias.alias == alias).first()
    if existing:
        session.delete(existing)
        session.flush()
        return True
    return False


def resolve_alias(
    session: Session,
    identifier: str,
    context: str,
    target_type: str | None = None,
) -> Alias | None:
    """
    Resolve an identifier to an alias if it matches the current context.
    Returns None if no matching alias found or if alias is for a different context.

    Args:
        session: Database session
        identifier: The alias name to look up
        context: The current context (must match for security)
        target_type: Optional filter for 'user' or 'channel'
    """
    query = session.query(Alias).filter(
        Alias.alias == identifier,
        Alias.context == context,
    )
    if target_type is not None:
        query = query.filter(Alias.target_type == target_type)
    return query.first()
