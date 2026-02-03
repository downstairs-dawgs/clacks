"""
CLI for listen command.
"""

import argparse
import json
import sys

from slack_clacks.auth.client import create_client
from slack_clacks.configuration.database import (
    ensure_db_updated,
    get_current_context,
    get_session,
)
from slack_clacks.listen.operations import listen_channel, spawn_claude_with_skill
from slack_clacks.messaging.operations import (
    resolve_channel_id,
    resolve_user_id,
)


def handle_listen(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        client = create_client(context.access_token, context.app_type)

        # Resolve channel
        channel_id = resolve_channel_id(client, args.channel, session, context.name)

        # Resolve from_user if specified
        from_user_id: str | None = None
        if args.from_user:
            from_user_id = resolve_user_id(
                client, args.from_user, session, context.name
            )

        messages_received = 0

        try:
            for msg in listen_channel(
                client,
                channel_id,
                thread_ts=args.thread_ts,
                interval=args.interval,
                timeout=args.timeout,
                include_history=args.include_history,
                continuous=args.continuous,
            ):
                # Filter by from_user if specified
                if from_user_id and msg.get("user") != from_user_id:
                    continue

                # Filter out bot messages unless --include-bots
                if not args.include_bots:
                    if msg.get("bot_id") or msg.get("subtype") == "bot_message":
                        continue

                # Execute Claude Code if skill specified
                if args.claude_exec_skill:
                    msg_ts = msg.get("ts", "unknown")
                    print(
                        f"Spawning Claude Code for message {msg_ts}...",
                        file=sys.stderr,
                    )
                    try:
                        exit_code = spawn_claude_with_skill(
                            message=msg,
                            skill_param=args.claude_exec_skill,
                            cwd=args.claude_cwd,
                            timeout=args.claude_timeout,
                        )
                        print(
                            f"Claude Code exited with code {exit_code} "
                            f"for message {msg_ts}",
                            file=sys.stderr,
                        )
                    except FileNotFoundError as e:
                        print(f"Error: {e}", file=sys.stderr)
                        # Only print this error once, then exit
                        return
                    except Exception as e:
                        print(
                            f"Unexpected error processing message {msg_ts}: {e}",
                            file=sys.stderr,
                        )
                        # Continue listening despite error

                messages_received += 1
                line = json.dumps(msg)
                args.outfile.write(line + "\n")
                args.outfile.flush()

        except KeyboardInterrupt:
            pass
        finally:
            # Print final status to stderr
            status = {"status": "stopped", "messages_received": messages_received}
            print(json.dumps(status), file=sys.stderr)


def generate_listen_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Listen for new messages in a channel or thread",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "channel",
        type=str,
        help="Channel name, ID, or alias (e.g., #general, C123456)",
    )
    parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        help="Configuration directory (default: platform-specific user config dir)",
    )
    parser.add_argument(
        "--thread",
        dest="thread_ts",
        type=str,
        help="Thread timestamp to listen to replies instead of channel",
    )
    parser.add_argument(
        "--from",
        dest="from_user",
        type=str,
        help="Filter messages by sender (name, ID, or alias)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Exit after N seconds (default: infinite)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Poll interval in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--include-history",
        type=int,
        default=0,
        help="Include last N messages on start (default: 0)",
    )
    parser.add_argument(
        "--include-bots",
        action="store_true",
        help="Include bot messages (excluded by default)",
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Keep listening after receiving messages (default: exit after first)",
    )
    parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for NDJSON results (default: stdout)",
    )
    parser.add_argument(
        "--claude-exec-skill",
        type=str,
        help=(
            "Execute Claude Code with this skill for each message "
            "(skill name or path to SKILL.md)"
        ),
    )
    parser.add_argument(
        "--claude-cwd",
        type=str,
        help="Working directory for Claude Code execution (default: current directory)",
    )
    parser.add_argument(
        "--claude-timeout",
        type=float,
        help="Timeout in seconds for Claude Code execution (default: no timeout)",
    )
    parser.set_defaults(func=handle_listen)

    return parser
