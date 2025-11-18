import argparse
from pathlib import Path

from sqlalchemy import text

from slack_clacks.configuration.database import (
    ensure_db_updated,
    get_config_dir,
    get_db_path,
    get_session,
)


def handle_init(args: argparse.Namespace) -> None:
    config_dir = args.config_dir
    ensure_db_updated(config_dir=config_dir)
    actual_dir = get_config_dir(config_dir)
    print(f"Initialized configuration database at {actual_dir}")


def handle_info(args: argparse.Namespace) -> None:
    config_dir_path = get_config_dir(args.config_dir)
    db_path = get_db_path(args.config_dir)

    print(f"Configuration directory: {config_dir_path}")
    print(f"Database: {db_path}")

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
                print(f"Current context: {current_context}")

                context_result = session.execute(
                    text(
                        "SELECT user_id, workspace_id FROM contexts WHERE name = :name"
                    ),
                    {"name": current_context},
                ).fetchone()

                if context_result:
                    print(f"  User ID: {context_result[0]}")
                    print(f"  Workspace ID: {context_result[1]}")
            else:
                print("Current context: (none)")
    except Exception as e:
        print(f"No configuration database found or error: {e}")


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
    init_parser.set_defaults(func=handle_init)

    info_parser = subparsers.add_parser("info", help="Show current configuration")
    info_parser.add_argument(
        "-D",
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory (default: platform-specific user config dir)",
    )
    info_parser.set_defaults(func=handle_info)

    return parser
