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
from slack_clacks.rolodex.data import PLATFORM_TARGET_TYPES
from slack_clacks.rolodex.operations import (
    add_alias,
    get_platform_target_types,
    list_aliases,
    remove_alias,
    sync_from_slack,
)


def handle_add(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        alias_obj = add_alias(
            session,
            alias=args.alias,
            context=context.name,
            target_type=args.target_type,
            platform=args.platform,
            target_id=args.target_id,
        )

        output = {
            "status": "added",
            "alias": alias_obj.alias,
            "context": alias_obj.context,
            "target_type": alias_obj.target_type,
            "platform": alias_obj.platform,
            "target_id": alias_obj.target_id,
        }
        with args.outfile as ofp:
            json.dump(output, ofp)


def handle_list(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        aliases = list_aliases(
            session,
            context=context.name,
            platform=args.platform,
            target_type=args.target_type,
            target_id=args.target_id,
            limit=args.limit,
            offset=args.offset,
        )

        output = {
            "aliases": [
                {
                    "alias": a.alias,
                    "platform": a.platform,
                    "target_type": a.target_type,
                    "target_id": a.target_id,
                }
                for a in aliases
            ],
            "count": len(aliases),
        }
        with args.outfile as ofp:
            json.dump(output, ofp)


def handle_remove(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        removed = remove_alias(
            session,
            alias=args.alias,
            context=context.name,
            target_type=args.target_type,
        )

        output = {
            "status": "removed" if removed else "not_found",
            "alias": args.alias,
            "target_type": args.target_type,
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
        result = sync_from_slack(session, client, context.name)

        output = {
            "status": "synced",
            "users": result["users"],
            "channels": result["channels"],
        }
        with args.outfile as ofp:
            json.dump(output, ofp)


def handle_platforminfo(args: argparse.Namespace) -> None:
    target_types = get_platform_target_types(args.platform)
    if target_types is None:
        valid_platforms = ", ".join(PLATFORM_TARGET_TYPES.keys())
        raise ValueError(
            f"Unknown platform '{args.platform}'. Valid platforms: {valid_platforms}"
        )

    output = {
        "platform": args.platform,
        "target_types": target_types,
    }
    with args.outfile as ofp:
        json.dump(output, ofp)


def generate_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage rolodex aliases")
    parser.set_defaults(func=lambda _: parser.print_help())

    subparsers = parser.add_subparsers(dest="rolodex_command")

    # --- add ---
    add_parser = subparsers.add_parser("add", help="Add an alias")
    add_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory",
    )
    add_parser.add_argument(
        "alias",
        type=str,
        help="Alias name",
    )
    add_parser.add_argument(
        "-t",
        "--target-id",
        type=str,
        required=True,
        help="Target ID (e.g., U123456, C123456)",
    )
    add_parser.add_argument(
        "-T",
        "--target-type",
        type=str,
        required=True,
        help="Target type (e.g., user, channel)",
    )
    add_parser.add_argument(
        "-p",
        "--platform",
        type=str,
        default="slack",
        help="Platform (default: slack)",
    )
    add_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    add_parser.set_defaults(func=handle_add)

    # --- list ---
    list_parser = subparsers.add_parser("list", help="List aliases")
    list_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory",
    )
    list_parser.add_argument(
        "-p",
        "--platform",
        type=str,
        help="Filter by platform",
    )
    list_parser.add_argument(
        "-T",
        "--target-type",
        type=str,
        help="Filter by target type",
    )
    list_parser.add_argument(
        "-t",
        "--target-id",
        type=str,
        help="Filter by target ID",
    )
    list_parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=100,
        help="Maximum results (default: 100)",
    )
    list_parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip results (default: 0)",
    )
    list_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    list_parser.set_defaults(func=handle_list)

    # --- remove ---
    remove_parser = subparsers.add_parser("remove", help="Remove an alias")
    remove_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory",
    )
    remove_parser.add_argument(
        "alias",
        type=str,
        help="Alias name to remove",
    )
    remove_parser.add_argument(
        "-T",
        "--target-type",
        type=str,
        required=True,
        help="Target type (required for unique identification)",
    )
    remove_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    remove_parser.set_defaults(func=handle_remove)

    # --- sync ---
    sync_parser = subparsers.add_parser("sync", help="Sync from Slack API")
    sync_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory",
    )
    sync_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    sync_parser.set_defaults(func=handle_sync)

    # --- platforminfo ---
    platforminfo_parser = subparsers.add_parser(
        "platforminfo", help="Show valid target types for a platform"
    )
    platforminfo_parser.add_argument(
        "-p",
        "--platform",
        type=str,
        required=True,
        help="Platform name",
    )
    platforminfo_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    platforminfo_parser.set_defaults(func=handle_platforminfo)

    return parser
