import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import text

from slack_clacks.configuration.database import (
    ensure_db_updated,
    get_config_dir,
    get_current_context,
    get_db_path,
    get_session,
    list_contexts,
    set_current_context,
)


def handle_init(args: argparse.Namespace) -> None:
    config_dir = args.config_dir
    ensure_db_updated(config_dir=config_dir)
    actual_dir = get_config_dir(config_dir)

    output = {"status": "initialized", "config_dir": str(actual_dir)}
    with args.outfile as ofp:
        json.dump(output, ofp)


def handle_info(args: argparse.Namespace) -> None:
    config_dir_path = get_config_dir(args.config_dir)
    db_path = get_db_path(args.config_dir)

    output = {
        "config_dir": str(config_dir_path),
        "database": str(db_path),
        "current_context": None,
        "user_id": None,
        "workspace_id": None,
        "app_type": None,
    }

    try:
        with get_session(args.config_dir) as session:
            result = session.execute(
                text(
                    "SELECT context_name FROM current_context "
                    "ORDER BY timestamp DESC LIMIT 1"
                )
            ).fetchone()

            if result:
                current_context = result[0]
                output["current_context"] = current_context

                context_result = session.execute(
                    text(
                        "SELECT user_id, workspace_id, app_type "
                        "FROM contexts WHERE name = :name"
                    ),
                    {"name": current_context},
                ).fetchone()

                if context_result:
                    output["user_id"] = context_result[0]
                    output["workspace_id"] = context_result[1]
                    output["app_type"] = context_result[2]
    except Exception:
        pass

    with args.outfile as ofp:
        json.dump(output, ofp)


def handle_contexts(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        contexts = list_contexts(session, limit=args.limit, offset=args.offset)
        current = get_current_context(session)
        current_name = current.name if current else None

        output = {
            "current_context": current_name,
            "contexts": [
                {
                    "name": ctx.name,
                    "user_id": ctx.user_id,
                    "workspace_id": ctx.workspace_id,
                    "is_current": ctx.name == current_name,
                }
                for ctx in contexts
            ],
        }
        with args.outfile as ofp:
            json.dump(output, ofp)


def handle_switch(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        from slack_clacks.configuration.database import get_context

        context = get_context(session, args.context)
        if context is None:
            raise ValueError(f"Context '{args.context}' does not exist")

        set_current_context(session, args.context)

    output = {"status": "success", "context": args.context}
    with args.outfile as ofp:
        json.dump(output, ofp)


def generate_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage clacks configuration")
    parser.set_defaults(func=lambda _: parser.print_help())

    subparsers = parser.add_subparsers(dest="config_command")

    init_parser = subparsers.add_parser(
        "init", help="Initialize configuration database"
    )
    init_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Directory in which to store the configuration database",
    )
    init_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    init_parser.set_defaults(func=handle_init)

    info_parser = subparsers.add_parser("info", help="Show current configuration")
    info_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory (default: platform-specific user config dir)",
    )
    info_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    info_parser.set_defaults(func=handle_info)

    contexts_parser = subparsers.add_parser("contexts", help="List all contexts")
    contexts_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory (default: platform-specific user config dir)",
    )
    contexts_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of contexts to display (default: 100)",
    )
    contexts_parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Number of contexts to skip (default: 0)",
    )
    contexts_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    contexts_parser.set_defaults(func=handle_contexts)

    switch_parser = subparsers.add_parser("switch", help="Switch current context")
    switch_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory (default: platform-specific user config dir)",
    )
    switch_parser.add_argument(
        "-C",
        "--context",
        type=str,
        required=True,
        help="Context name to switch to",
    )
    switch_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    switch_parser.set_defaults(func=handle_switch)

    return parser
