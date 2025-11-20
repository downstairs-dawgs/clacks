import argparse
import json
import sys

from slack_sdk import WebClient

from slack_clacks.auth.validation import get_scopes_for_mode, validate
from slack_clacks.configuration.database import (
    ensure_db_updated,
    get_current_context,
    get_session,
)

from .operations import (
    add_reaction,
    get_recent_activity,
    open_dm_channel,
    read_messages,
    read_thread,
    remove_reaction,
    resolve_channel_id,
    resolve_user_id,
    send_message,
)


def handle_send(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        client = WebClient(token=context.access_token)

        channel_id = None

        if args.channel:
            channel_id = resolve_channel_id(client, args.channel)
        elif args.user:
            user_id = resolve_user_id(client, args.user)
            channel_id = open_dm_channel(client, user_id)
            if channel_id is None:
                raise ValueError(f"Failed to open DM with user '{args.user}'.")
        else:
            raise ValueError("Must specify either --channel or --user.")

        response = send_message(client, channel_id, args.message, thread_ts=args.thread)

        with args.outfile as ofp:
            json.dump(response.data, ofp)


def generate_send_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send a message",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        help="Configuration directory (default: platform-specific user config dir)",
    )
    parser.add_argument(
        "-c",
        "--channel",
        type=str,
        help="Channel ID or name (e.g., #general, C123456)",
    )
    parser.add_argument(
        "-u",
        "--user",
        type=str,
        help="User ID or name for DM (e.g., @username, U123456)",
    )
    parser.add_argument(
        "-m",
        "--message",
        type=str,
        required=True,
        help="Message text",
    )
    parser.add_argument(
        "-t",
        "--thread",
        type=str,
        help="Thread timestamp for replying to thread",
    )
    parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    parser.set_defaults(func=handle_send)

    return parser


def handle_read(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        client = WebClient(token=context.access_token)

        channel_id = None

        if args.channel:
            channel_id = resolve_channel_id(client, args.channel)

            scopes = get_scopes_for_mode(context.app_type)
            if channel_id.startswith("C"):
                validate("channels:history", scopes, raise_on_error=True)
            elif channel_id.startswith("G"):
                validate("groups:history", scopes, raise_on_error=True)

        elif args.user:
            user_id = resolve_user_id(client, args.user)
            channel_id = open_dm_channel(client, user_id)
            if channel_id is None:
                raise ValueError(f"Failed to open DM with user '{args.user}'.")
        else:
            raise ValueError("Must specify either --channel or --user.")

        if args.thread:
            response = read_thread(client, channel_id, args.thread, limit=args.limit)
        elif args.message:
            response = read_messages(
                client, channel_id, limit=1, latest=args.message, oldest=None
            )
        else:
            response = read_messages(
                client, channel_id, limit=args.limit, latest=None, oldest=None
            )

        with args.outfile as ofp:
            json.dump(response.data, ofp)


def generate_read_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read messages from a channel, DM, or thread",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        help="Configuration directory (default: platform-specific user config dir)",
    )
    parser.add_argument(
        "-c",
        "--channel",
        type=str,
        help="Channel ID or name (e.g., #general, C123456)",
    )
    parser.add_argument(
        "-u",
        "--user",
        type=str,
        help="User ID or name for DM (e.g., @username, U123456)",
    )
    parser.add_argument(
        "-t",
        "--thread",
        type=str,
        help="Thread timestamp to read thread replies",
    )
    parser.add_argument(
        "-m",
        "--message",
        type=str,
        help="Specific message timestamp to read",
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=20,
        help="Max messages to retrieve (default: 20)",
    )
    parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    parser.set_defaults(func=handle_read)

    return parser


def handle_recent(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        scopes = get_scopes_for_mode(context.app_type)
        validate("channels:history", scopes, raise_on_error=True)

        client = WebClient(token=context.access_token)

        messages = get_recent_activity(client, message_limit=args.limit)

        with args.outfile as ofp:
            json.dump(messages, ofp)


def generate_recent_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Show recent messages across all conversations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        help="Configuration directory (default: platform-specific user config dir)",
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=20,
        help="Max recent messages to retrieve (default: 20)",
    )
    parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    parser.set_defaults(func=handle_recent)

    return parser


def handle_react(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        client = WebClient(token=context.access_token)

        if args.channel:
            channel_id = resolve_channel_id(client, args.channel)
        else:
            user_id = resolve_user_id(client, args.user)
            dm_channel = open_dm_channel(client, user_id)
            if dm_channel is None:
                raise ValueError(f"Failed to open DM with user '{args.user}'.")
            channel_id = dm_channel

        if args.remove:
            response = remove_reaction(client, channel_id, args.message, args.emoji)
        else:
            response = add_reaction(client, channel_id, args.message, args.emoji)

        with args.outfile as ofp:
            json.dump(response.data, ofp)


def generate_react_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Add or remove emoji reactions on messages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        help="Configuration directory (default: platform-specific user config dir)",
    )

    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        "-c",
        "--channel",
        type=str,
        help="Channel ID or name (e.g., #general, C123456)",
    )
    target_group.add_argument(
        "-u",
        "--user",
        type=str,
        help="User ID or name for DM (e.g., @username, U123456)",
    )
    parser.add_argument(
        "-m",
        "--message",
        type=str,
        required=True,
        help="Message timestamp",
    )
    parser.add_argument(
        "-e",
        "--emoji",
        type=str,
        required=True,
        help="Emoji name (e.g., thumbsup or :thumbsup:)",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove reaction instead of adding",
    )
    parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    parser.set_defaults(func=handle_react)

    return parser
