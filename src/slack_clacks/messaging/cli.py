import argparse

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from slack_clacks.configuration.database import (
    ensure_db_updated,
    get_current_context,
    get_session,
)

from .operations import (
    open_dm_channel,
    resolve_channel_id,
    resolve_user_id,
    send_message,
)


def handle_send(args: argparse.Namespace) -> None:
    try:
        ensure_db_updated(config_dir=args.config_dir)
        with get_session(args.config_dir) as session:
            context = get_current_context(session)
            if context is None:
                print("No active authentication context.")
                print("Authenticate with: clacks auth login")
                raise SystemExit(1)

            client = WebClient(token=context.access_token)

            channel_id = None

            if args.channel:
                channel_id = resolve_channel_id(client, args.channel)
                if channel_id is None:
                    print(f"Channel '{args.channel}' not found.")
                    raise SystemExit(1)
            elif args.user:
                user_id = resolve_user_id(client, args.user)
                if user_id is None:
                    print(f"User '{args.user}' not found.")
                    raise SystemExit(1)
                channel_id = open_dm_channel(client, user_id)
                if channel_id is None:
                    print(f"Failed to open DM with user '{args.user}'.")
                    raise SystemExit(1)
            else:
                print("Must specify either --channel or --user.")
                raise SystemExit(1)

            try:
                response = send_message(
                    client, channel_id, args.message, thread_ts=args.thread
                )
                print(f"Message sent: {response['ts']}")
            except SlackApiError as e:
                print(f"Failed to send message: {e.response['error']}")
                raise SystemExit(1)

    except Exception as e:
        print(f"Send failed: {e}")
        raise SystemExit(1)


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
    parser.set_defaults(func=handle_send)

    return parser
