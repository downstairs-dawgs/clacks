import argparse

from slack_clacks.auth.cli import generate_cli as generate_auth_cli
from slack_clacks.configuration.cli import generate_cli as generate_config_cli
from slack_clacks.messaging.cli import generate_send_parser


def generate_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="clacks: Control Slack from your command line"
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

    return parser
