"""
CLI commands for rolodex.
"""

import argparse
import json
import sys
from pathlib import Path

from slack_clacks.auth.client import create_client
from slack_clacks.configuration.database import (
    ensure_db_updated,
    get_current_context,
    get_session,
)
from slack_clacks.rolodex.operations import (
    add_channel,
    add_user,
    clear_rolodex,
    list_channels,
    list_users,
    remove_channel,
    remove_user,
    search_channels,
    search_users,
    sync_channels,
    sync_users,
)


def get_workspace_id(args: argparse.Namespace) -> str:
    """Get workspace_id from current context."""
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )
        return context.workspace_id


def handle_add_user(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        user = add_user(
            session,
            workspace_id=context.workspace_id,
            user_id=args.user_id,
            username=args.username,
            real_name=args.real_name,
            email=args.email,
        )

        output = {
            "status": "added",
            "user_id": user.user_id,
            "username": user.username,
            "real_name": user.real_name,
            "email": user.email,
        }
        with args.outfile as ofp:
            json.dump(output, ofp)


def handle_add_channel(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        channel = add_channel(
            session,
            workspace_id=context.workspace_id,
            channel_id=args.channel_id,
            channel_name=args.channel_name,
            is_private=args.private,
        )

        output = {
            "status": "added",
            "channel_id": channel.channel_id,
            "channel_name": channel.channel_name,
            "is_private": channel.is_private,
        }
        with args.outfile as ofp:
            json.dump(output, ofp)


def handle_list_users(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        users = list_users(
            session,
            workspace_id=context.workspace_id,
            limit=args.limit,
            offset=args.offset,
        )

        output = {
            "users": [
                {
                    "user_id": u.user_id,
                    "username": u.username,
                    "real_name": u.real_name,
                    "email": u.email,
                }
                for u in users
            ],
            "count": len(users),
        }
        with args.outfile as ofp:
            json.dump(output, ofp)


def handle_list_channels(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        channels = list_channels(
            session,
            workspace_id=context.workspace_id,
            limit=args.limit,
            offset=args.offset,
        )

        output = {
            "channels": [
                {
                    "channel_id": c.channel_id,
                    "channel_name": c.channel_name,
                    "is_private": c.is_private,
                }
                for c in channels
            ],
            "count": len(channels),
        }
        with args.outfile as ofp:
            json.dump(output, ofp)


def handle_search_users(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        users = search_users(
            session,
            workspace_id=context.workspace_id,
            query=args.query,
            limit=args.limit,
        )

        output = {
            "users": [
                {
                    "user_id": u.user_id,
                    "username": u.username,
                    "real_name": u.real_name,
                    "email": u.email,
                }
                for u in users
            ],
            "count": len(users),
            "query": args.query,
        }
        with args.outfile as ofp:
            json.dump(output, ofp)


def handle_search_channels(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        channels = search_channels(
            session,
            workspace_id=context.workspace_id,
            query=args.query,
            limit=args.limit,
        )

        output = {
            "channels": [
                {
                    "channel_id": c.channel_id,
                    "channel_name": c.channel_name,
                    "is_private": c.is_private,
                }
                for c in channels
            ],
            "count": len(channels),
            "query": args.query,
        }
        with args.outfile as ofp:
            json.dump(output, ofp)


def handle_sync(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        client = create_client(context.access_token, context.app_type)

        output: dict = {"status": "synced"}

        if args.target in ("users", "all"):
            users_count = sync_users(session, client, context.workspace_id)
            output["users_synced"] = users_count

        if args.target in ("channels", "all"):
            channels_count = sync_channels(session, client, context.workspace_id)
            output["channels_synced"] = channels_count

        with args.outfile as ofp:
            json.dump(output, ofp)


def handle_remove_user(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        removed = remove_user(session, context.workspace_id, args.identifier)

        output = {
            "status": "removed" if removed else "not_found",
            "identifier": args.identifier,
        }
        with args.outfile as ofp:
            json.dump(output, ofp)


def handle_remove_channel(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        removed = remove_channel(session, context.workspace_id, args.identifier)

        output = {
            "status": "removed" if removed else "not_found",
            "identifier": args.identifier,
        }
        with args.outfile as ofp:
            json.dump(output, ofp)


def handle_clear(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        users_deleted, channels_deleted = clear_rolodex(session, context.workspace_id)

        output = {
            "status": "cleared",
            "users_deleted": users_deleted,
            "channels_deleted": channels_deleted,
        }
        with args.outfile as ofp:
            json.dump(output, ofp)


def generate_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage local cache of users and channels"
    )
    parser.set_defaults(func=lambda _: parser.print_help())

    subparsers = parser.add_subparsers(dest="rolodex_command")

    # --- add user ---
    add_user_parser = subparsers.add_parser("add-user", help="Add a user to rolodex")
    add_user_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory",
    )
    add_user_parser.add_argument(
        "user_id",
        type=str,
        help="User ID (e.g., U0876FVQ58C)",
    )
    add_user_parser.add_argument(
        "-u",
        "--username",
        type=str,
        help="Username (e.g., nkashy1)",
    )
    add_user_parser.add_argument(
        "-n",
        "--real-name",
        type=str,
        help="Real name / display name",
    )
    add_user_parser.add_argument(
        "-e",
        "--email",
        type=str,
        help="Email address",
    )
    add_user_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    add_user_parser.set_defaults(func=handle_add_user)

    # --- add channel ---
    add_channel_parser = subparsers.add_parser(
        "add-channel", help="Add a channel to rolodex"
    )
    add_channel_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory",
    )
    add_channel_parser.add_argument(
        "channel_id",
        type=str,
        help="Channel ID (e.g., C08740LGAE6)",
    )
    add_channel_parser.add_argument(
        "-n",
        "--channel-name",
        type=str,
        help="Channel name (e.g., general)",
    )
    add_channel_parser.add_argument(
        "-p",
        "--private",
        action="store_true",
        help="Mark channel as private",
    )
    add_channel_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    add_channel_parser.set_defaults(func=handle_add_channel)

    # --- list users ---
    list_users_parser = subparsers.add_parser(
        "list-users", help="List users in rolodex"
    )
    list_users_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory",
    )
    list_users_parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=100,
        help="Maximum number of results (default: 100)",
    )
    list_users_parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Number of results to skip (default: 0)",
    )
    list_users_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    list_users_parser.set_defaults(func=handle_list_users)

    # --- list channels ---
    list_channels_parser = subparsers.add_parser(
        "list-channels", help="List channels in rolodex"
    )
    list_channels_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory",
    )
    list_channels_parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=100,
        help="Maximum number of results (default: 100)",
    )
    list_channels_parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Number of results to skip (default: 0)",
    )
    list_channels_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    list_channels_parser.set_defaults(func=handle_list_channels)

    # --- search users ---
    search_users_parser = subparsers.add_parser(
        "search-users", help="Search users in rolodex"
    )
    search_users_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory",
    )
    search_users_parser.add_argument(
        "query",
        type=str,
        help="Search query (matches username, real_name, email)",
    )
    search_users_parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=100,
        help="Maximum number of results (default: 100)",
    )
    search_users_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    search_users_parser.set_defaults(func=handle_search_users)

    # --- search channels ---
    search_channels_parser = subparsers.add_parser(
        "search-channels", help="Search channels in rolodex"
    )
    search_channels_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory",
    )
    search_channels_parser.add_argument(
        "query",
        type=str,
        help="Search query (matches channel_name)",
    )
    search_channels_parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=100,
        help="Maximum number of results (default: 100)",
    )
    search_channels_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    search_channels_parser.set_defaults(func=handle_search_channels)

    # --- sync ---
    sync_parser = subparsers.add_parser(
        "sync", help="Sync users/channels from Slack API"
    )
    sync_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory",
    )
    sync_parser.add_argument(
        "target",
        type=str,
        nargs="?",
        default="all",
        choices=["users", "channels", "all"],
        help="What to sync (default: all)",
    )
    sync_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    sync_parser.set_defaults(func=handle_sync)

    # --- remove user ---
    remove_user_parser = subparsers.add_parser(
        "remove-user", help="Remove a user from rolodex"
    )
    remove_user_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory",
    )
    remove_user_parser.add_argument(
        "identifier",
        type=str,
        help="User ID, username, or email",
    )
    remove_user_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    remove_user_parser.set_defaults(func=handle_remove_user)

    # --- remove channel ---
    remove_channel_parser = subparsers.add_parser(
        "remove-channel", help="Remove a channel from rolodex"
    )
    remove_channel_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory",
    )
    remove_channel_parser.add_argument(
        "identifier",
        type=str,
        help="Channel ID or name",
    )
    remove_channel_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    remove_channel_parser.set_defaults(func=handle_remove_channel)

    # --- clear ---
    clear_parser = subparsers.add_parser(
        "clear", help="Clear all rolodex entries for current workspace"
    )
    clear_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory",
    )
    clear_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    clear_parser.set_defaults(func=handle_clear)

    return parser
