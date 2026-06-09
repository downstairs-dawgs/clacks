import argparse
import json
import sys
from decimal import Decimal
from typing import Any

from slack_clacks.auth.client import create_client
from slack_clacks.auth.validation import get_scopes_for_mode, validate
from slack_clacks.configuration.cli import add_context_argument
from slack_clacks.configuration.database import (
    ensure_db_updated,
    get_session,
    resolve_context,
)
from slack_clacks.constants import SLACK_TS_EPSILON
from slack_clacks.messaging.operations import (
    add_reaction,
    delete_message,
    get_recent_activity,
    open_dm_channel,
    parse_schedule_time,
    parse_timestamp,
    read_messages,
    read_thread,
    remove_reaction,
    resolve_channel_id,
    resolve_message_timestamp,
    resolve_user_id,
    schedule_message,
    search_messages,
    send_message,
)


def sort_messages_by_ts(messages: list, order: str) -> list:
    """Sort a list of Slack message dicts by their ``ts`` field.

    Slack ``ts`` is a string of the form ``"<seconds>.<micros>"``. We parse
    as ``float`` so the sort is canonical numeric ordering; messages
    missing or unparseable ``ts`` sort as 0.0. Pagination and response
    shape are untouched — only the local list order changes.
    """

    def _key(m: Any) -> float:
        try:
            return float(m.get("ts", 0))
        except (TypeError, ValueError):
            return 0.0

    return sorted(messages, key=_key, reverse=(order == "desc"))


def add_order_argument(parser: argparse.ArgumentParser) -> None:
    """Attach the shared ``--order {asc,desc}`` flag.

    Default ``desc`` preserves Slack's native reverse-chronological return
    order. ``asc`` re-sorts the returned messages locally before printing
    — convenient for agentic loops that consume oldest-first.
    """
    parser.add_argument(
        "--order",
        type=str,
        choices=("asc", "desc"),
        default="desc",
        help=(
            "Order returned messages by timestamp. "
            "'desc' (default) preserves Slack's newest-first order; "
            "'asc' re-sorts locally to oldest-first before printing."
        ),
    )


def _resolve_target_channel(
    client: Any,
    args: argparse.Namespace,
    session: Any,
    context_name: str,
) -> str:
    if getattr(args, "channel", None):
        return resolve_channel_id(client, args.channel, session, context_name)
    elif getattr(args, "user", None):
        user_id = resolve_user_id(client, args.user, session, context_name)
        channel_id = open_dm_channel(client, user_id)
        if channel_id is None:
            raise ValueError(f"Failed to open DM with user '{args.user}'.")
        return channel_id
    else:
        raise ValueError("Must specify either --channel or --user.")


def handle_send(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = resolve_context(session, args.context)

        client = create_client(context.access_token, context.app_type)
        channel_id = _resolve_target_channel(client, args, session, context.name)
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
    add_context_argument(parser)
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


def handle_schedule(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = resolve_context(session, args.context)

        client = create_client(context.access_token, context.app_type)
        channel_id = _resolve_target_channel(client, args, session, context.name)
        post_at = parse_schedule_time(args.at)
        response = schedule_message(
            client, channel_id, args.message, post_at, thread_ts=args.thread
        )

        with args.outfile as ofp:
            json.dump(response.data, ofp)


def generate_schedule_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Schedule a message for future delivery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        help="Configuration directory (default: platform-specific user config dir)",
    )
    add_context_argument(parser)
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
        "-a",
        "--at",
        type=str,
        required=True,
        help=(
            "When to send (e.g., '9pm CET', '21:00 UTC', "
            "'in 2 hours', '2026-03-12T21:00:00+01:00')"
        ),
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
    parser.set_defaults(func=handle_schedule)

    return parser


def handle_read(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = resolve_context(session, args.context)

        client = create_client(context.access_token, context.app_type)

        channel_id = None

        if args.channel:
            channel_id = resolve_channel_id(client, args.channel, session, context.name)

            scopes = get_scopes_for_mode(context.app_type)
            if channel_id.startswith("C"):
                validate("channels:history", scopes, raise_on_error=True)
            elif channel_id.startswith("G"):
                validate("groups:history", scopes, raise_on_error=True)

        elif args.user:
            user_id = resolve_user_id(client, args.user, session, context.name)
            channel_id = open_dm_channel(client, user_id)
            if channel_id is None:
                raise ValueError(f"Failed to open DM with user '{args.user}'.")
        else:
            raise ValueError("Must specify either --channel or --user.")

        oldest = None
        if args.since:
            oldest = parse_timestamp(args.since)
        elif args.after:
            oldest = str(Decimal(parse_timestamp(args.after)) + SLACK_TS_EPSILON)

        latest = None
        if args.until:
            latest = parse_timestamp(args.until)
        elif args.before:
            latest = str(Decimal(parse_timestamp(args.before)) - SLACK_TS_EPSILON)

        if args.thread:
            response = read_thread(
                client,
                channel_id,
                args.thread,
                limit=args.limit,
                oldest=oldest,
                latest=latest,
                cursor=args.cursor,
            )
        elif args.message:
            ts = resolve_message_timestamp(args.message)
            response = read_messages(client, channel_id, limit=1, latest=ts, oldest=ts)
        else:
            response = read_messages(
                client,
                channel_id,
                limit=args.limit,
                latest=latest,
                oldest=oldest,
                cursor=args.cursor,
            )

        data = dict(response.data)
        data["messages"] = sort_messages_by_ts(data.get("messages", []), args.order)

        with args.outfile as ofp:
            json.dump(data, ofp)


def assert_cursor_nonempty(value: str) -> str:
    """Reject empty/whitespace cursors at parse time.

    Slack signals the last page with an empty ``next_cursor``; passing that
    back would silently re-fetch page 1, so a paging loop would never end.
    """
    if not value.strip():
        raise argparse.ArgumentTypeError(
            "empty cursor: an empty next_cursor means the previous page was the last"
        )
    return value


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
    add_context_argument(parser)
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
    # --message reads exactly one message; --cursor pages through many.
    message_or_cursor = parser.add_mutually_exclusive_group()
    message_or_cursor.add_argument(
        "-m",
        "--message",
        type=str,
        help="Specific message timestamp to read",
    )
    lower_bound = parser.add_mutually_exclusive_group()
    lower_bound.add_argument(
        "--since",
        type=str,
        help=(
            "Only messages at or after this time (inclusive) "
            "(Slack link, timestamp, ISO 8601, "
            "or relative like '5 minutes ago')"
        ),
    )
    lower_bound.add_argument(
        "--after",
        type=str,
        help=(
            "Only messages after this time (exclusive) "
            "(Slack link, timestamp, ISO 8601, "
            "or relative like '5 minutes ago')"
        ),
    )

    upper_bound = parser.add_mutually_exclusive_group()
    upper_bound.add_argument(
        "--until",
        type=str,
        help=(
            "Only messages at or before this time (inclusive) "
            "(Slack link, timestamp, ISO 8601, "
            "or relative like '1 hour ago')"
        ),
    )
    upper_bound.add_argument(
        "--before",
        type=str,
        help=(
            "Only messages before this time (exclusive) "
            "(Slack link, timestamp, ISO 8601, "
            "or relative like '1 hour ago')"
        ),
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=20,
        help="Max messages per request (default: 20); does not auto-follow cursors",
    )
    message_or_cursor.add_argument(
        "--cursor",
        type=assert_cursor_nonempty,
        default=None,
        help=(
            "Pagination cursor from a previous response's "
            "response_metadata.next_cursor; fetches the next page. "
            "Stop paging when has_more is false (next_cursor empty)."
        ),
    )
    add_order_argument(parser)
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
        context = resolve_context(session, args.context)

        scopes = get_scopes_for_mode(context.app_type)
        validate("channels:history", scopes, raise_on_error=True)

        client = create_client(context.access_token, context.app_type)

        messages = get_recent_activity(client, message_limit=args.limit)
        messages = sort_messages_by_ts(messages, args.order)

        with args.outfile as ofp:
            json.dump(messages, ofp)


def generate_recent_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Show recent messages across all conversations "
            "(makes one history request per conversation; "
            "conversations whose fetch fails are skipped)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        help="Configuration directory (default: platform-specific user config dir)",
    )
    add_context_argument(parser)
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=20,
        help="Max recent messages to retrieve (default: 20)",
    )
    add_order_argument(parser)
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
        context = resolve_context(session, args.context)

        client = create_client(context.access_token, context.app_type)
        channel_id = _resolve_target_channel(client, args, session, context.name)
        ts = resolve_message_timestamp(args.message)

        if args.remove:
            response = remove_reaction(client, channel_id, ts, args.emoji)
        else:
            response = add_reaction(client, channel_id, ts, args.emoji)

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
    add_context_argument(parser)

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


def handle_search(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = resolve_context(session, args.context)

        scopes = get_scopes_for_mode(context.app_type)
        validate("search:read", scopes, raise_on_error=True)

        if not args.query.strip():
            raise ValueError("Search query cannot be empty.")

        if args.limit < 1 or args.limit > 100:
            raise ValueError("Limit must be between 1 and 100.")

        client = create_client(context.access_token, context.app_type)
        response = search_messages(
            client,
            query=args.query,
            sort=args.sort,
            sort_dir=args.sort_dir,
            count=args.limit,
            page=args.page,
            cursor=args.cursor,
        )

        # ``--order`` is a local post-fetch sort of the result list,
        # independent of the upstream ``--sort``/``--sort-dir`` flags
        # (which control the Slack search.messages API). Slack's response
        # shape is ``{messages: {matches: [...], paging: {...}, ...}}``;
        # we re-sort ``matches`` in place and leave pagination alone.
        data = dict(response.data)
        nested = dict(data.get("messages", {}))
        nested["matches"] = sort_messages_by_ts(nested.get("matches", []), args.order)
        data["messages"] = nested

        with args.outfile as ofp:
            json.dump(data, ofp)


def generate_search_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search messages across the workspace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  clacks search -q "deployment error"
  clacks search -q "in:#general deployment error"
  clacks search -q "from:@alice bug fix"
  clacks search -q "with:@bob in:#project"
  clacks search -q "in:#ops from:@alice after:2026-01-01"
  clacks search -q "has:link in:#general" --sort score
  clacks search -q "is:thread during:2026-03"
  clacks search -q '"exact error message" -wip'
""",
    )

    parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        help="Configuration directory (default: platform-specific user config dir)",
    )
    add_context_argument(parser)
    parser.add_argument(
        "-q",
        "--query",
        type=str,
        required=True,
        help=(
            "Search query. Supports filters: "
            "in:#channel, from:@user, with:@user, "
            "before:/after:/on:YYYY-MM-DD, during:YYYY-MM, "
            'has:link/pin/:emoji:, is:thread/saved, "exact phrase", -exclude.'
        ),
    )
    parser.add_argument(
        "-s",
        "--sort",
        type=str,
        choices=["timestamp", "score"],
        default="timestamp",
        help="Sort results by timestamp or relevance score (default: timestamp)",
    )
    parser.add_argument(
        "--sort-dir",
        type=str,
        choices=["asc", "desc"],
        default="desc",
        help="Sort direction (default: desc)",
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=20,
        help="Results per page, 1-100 (default: 20)",
    )
    add_order_argument(parser)

    pagination_group = parser.add_mutually_exclusive_group()
    pagination_group.add_argument(
        "--page",
        type=int,
        help="Page number for page-based pagination",
    )
    pagination_group.add_argument(
        "--cursor",
        type=str,
        help="Cursor for cursor-based pagination (from previous response)",
    )

    parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    parser.set_defaults(func=handle_search)

    return parser


def handle_delete(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = resolve_context(session, args.context)

        client = create_client(context.access_token, context.app_type)
        channel_id = _resolve_target_channel(client, args, session, context.name)
        ts = resolve_message_timestamp(args.message)
        response = delete_message(client, channel_id, ts)

        with args.outfile as ofp:
            json.dump(response.data, ofp)


def generate_delete_parser() -> argparse.ArgumentParser:
    # Channel is required because Slack's chat.delete API requires both channel and ts.
    # Timestamps are only unique within a channel, not globally.
    # See: https://api.slack.com/methods/chat.delete
    parser = argparse.ArgumentParser(
        description="Delete a message",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        help="Configuration directory (default: platform-specific user config dir)",
    )
    add_context_argument(parser)

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
        help="Message timestamp to delete",
    )
    parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    parser.set_defaults(func=handle_delete)

    return parser
