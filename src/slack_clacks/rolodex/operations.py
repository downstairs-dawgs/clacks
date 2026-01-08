"""
Database operations for rolodex.
"""

from slack_sdk import WebClient
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from slack_clacks.rolodex.data import CHANNEL, PLATFORM_TARGET_TYPES, SLACK, USER
from slack_clacks.rolodex.models import Alias


def get_platform_target_types(platform: str) -> list[str] | None:
    """Get valid target types for a platform. Returns None if platform unknown."""
    return PLATFORM_TARGET_TYPES.get(platform)


def validate_platform_target_type(platform: str, target_type: str) -> None:
    """Validate platform and target_type combination. Raises ValueError if invalid."""
    valid_types = get_platform_target_types(platform)
    if valid_types is None:
        valid_platforms = ", ".join(PLATFORM_TARGET_TYPES.keys())
        raise ValueError(f"Unknown platform '{platform}'. Valid: {valid_platforms}")
    if target_type not in valid_types:
        raise ValueError(
            f"Invalid target_type '{target_type}' for platform '{platform}'. "
            f"Valid: {', '.join(valid_types)}"
        )


def add_alias(
    session: Session,
    alias: str,
    context: str,
    target_type: str,
    platform: str,
    target_id: str,
) -> Alias:
    """
    Add or update an alias using atomic upsert.
    Unique per (alias, context, target_type).
    """
    validate_platform_target_type(platform, target_type)

    stmt = insert(Alias).values(
        alias=alias,
        context=context,
        target_type=target_type,
        platform=platform,
        target_id=target_id,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["alias", "context", "target_type"],
        set_={"platform": stmt.excluded.platform, "target_id": stmt.excluded.target_id},
    )
    session.execute(stmt)
    session.flush()

    return (
        session.query(Alias)
        .filter(
            Alias.alias == alias,
            Alias.context == context,
            Alias.target_type == target_type,
        )
        .one()
    )


def get_alias(
    session: Session,
    alias: str,
    context: str,
    target_type: str,
) -> Alias | None:
    """Lookup an alias by (alias, context, target_type)."""
    return (
        session.query(Alias)
        .filter(
            Alias.alias == alias,
            Alias.context == context,
            Alias.target_type == target_type,
        )
        .first()
    )


def list_aliases(
    session: Session,
    context: str,
    platform: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Alias]:
    """List aliases with optional filtering."""
    query = session.query(Alias).filter(Alias.context == context)
    if platform is not None:
        query = query.filter(Alias.platform == platform)
    if target_type is not None:
        query = query.filter(Alias.target_type == target_type)
    if target_id is not None:
        query = query.filter(Alias.target_id == target_id)
    return query.order_by(Alias.alias).limit(limit).offset(offset).all()


def remove_alias(
    session: Session,
    alias: str,
    context: str,
    target_type: str,
) -> bool:
    """Remove an alias. Returns True if removed, False if not found."""
    existing = get_alias(session, alias, context, target_type)
    if existing:
        session.delete(existing)
        session.flush()
        return True
    return False


def resolve_alias(
    session: Session,
    identifier: str,
    context: str,
    target_type: str,
    platform: str | None = None,
) -> Alias | None:
    """Resolve an identifier to an alias in the current context."""
    alias = get_alias(session, identifier, context, target_type)
    if alias is None:
        return None
    if platform is not None and alias.platform != platform:
        return None
    return alias


def _insert_alias_if_not_exists(
    session: Session,
    alias: str,
    context: str,
    target_type: str,
    platform: str,
    target_id: str,
) -> None:
    """Insert alias only if it doesn't exist. Preserves manual aliases during sync."""
    stmt = insert(Alias).values(
        alias=alias,
        context=context,
        target_type=target_type,
        platform=platform,
        target_id=target_id,
    )
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["alias", "context", "target_type"],
    )
    session.execute(stmt)


def sync_from_slack(
    session: Session,
    client: WebClient,
    context: str,
) -> dict[str, int]:
    """
    Sync users and channels from Slack API to rolodex.
    Creates aliases using username/channel_name as the alias.
    Preserves existing aliases (does not overwrite manual entries).
    Returns {"users": count, "channels": count}.
    """
    users_count = 0
    channels_count = 0

    # Sync users
    cursor: str | None = None
    while True:
        response = client.users_list(cursor=cursor, limit=200)

        for member in response["members"]:
            if member.get("deleted"):
                continue
            username = member.get("name")
            if username:
                _insert_alias_if_not_exists(
                    session,
                    alias=username,
                    context=context,
                    target_type=USER,
                    platform=SLACK,
                    target_id=member["id"],
                )
                users_count += 1

        response_metadata = response.get("response_metadata")
        cursor = response_metadata.get("next_cursor") if response_metadata else None
        if not cursor:
            break

    # Sync channels
    cursor = None
    while True:
        response = client.conversations_list(
            cursor=cursor,
            limit=200,
            types="public_channel,private_channel",
        )

        for channel in response["channels"]:
            channel_name = channel.get("name")
            if channel_name:
                _insert_alias_if_not_exists(
                    session,
                    alias=channel_name,
                    context=context,
                    target_type=CHANNEL,
                    platform=SLACK,
                    target_id=channel["id"],
                )
                channels_count += 1

        response_metadata = response.get("response_metadata")
        cursor = response_metadata.get("next_cursor") if response_metadata else None
        if not cursor:
            break

    session.flush()
    return {"users": users_count, "channels": channels_count}
