import argparse
from importlib.metadata import version

from slack_clacks.auth.cli import generate_cli as generate_auth_cli
from slack_clacks.configuration.cli import generate_cli as generate_config_cli
from slack_clacks.messaging.cli import (
    generate_react_parser,
    generate_read_parser,
    generate_recent_parser,
    generate_send_parser,
)


def generate_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="clacks: Control Slack from your command line"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=version("slack-clacks"),
    )
    parser.set_defaults(func=lambda _: parser.print_help())
    subparsers = parser.add_subparsers()

    config_parser = generate_config_cli()
    subparsers.add_parser(
        "config",
        parents=[config_parser],
        add_help=False,
        help=config_parser.description,
    )

    auth_parser = generate_auth_cli()
    subparsers.add_parser(
        "auth", parents=[auth_parser], add_help=False, help=auth_parser.description
    )

    send_parser = generate_send_parser()
    subparsers.add_parser(
        "send",
        parents=[send_parser],
        add_help=False,
        help=send_parser.description,
    )

    read_parser = generate_read_parser()
    subparsers.add_parser(
        "read",
        parents=[read_parser],
        add_help=False,
        help=read_parser.description,
    )

    recent_parser = generate_recent_parser()
    subparsers.add_parser(
        "recent",
        parents=[recent_parser],
        add_help=False,
        help=recent_parser.description,
    )

    react_parser = generate_react_parser()
    subparsers.add_parser(
        "react",
        parents=[react_parser],
        add_help=False,
        help=react_parser.description,
    )

    return parser
