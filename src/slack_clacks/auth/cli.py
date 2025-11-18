import argparse
import json
import sys

from slack_clacks.configuration.database import (
    add_context,
    delete_context,
    ensure_db_updated,
    get_context,
    get_current_context,
    get_session,
    set_current_context,
    update_context,
)

from .cert import generate_self_signed_cert, get_cert_info
from .oauth import start_oauth_flow


def handle_login(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    credentials = start_oauth_flow(config_dir=args.config_dir)

    context_name = args.context
    if not context_name:
        context_name = input("Enter a name for this context: ").strip()
        if not context_name:
            raise ValueError("Context name cannot be empty")

    with get_session(args.config_dir) as session:
        existing_context = get_context(session, context_name)

        if existing_context:
            if not args.overwrite:
                raise ValueError(
                    f"Context '{context_name}' already exists. "
                    "Use --overwrite to replace it."
                )

            update_context(
                session,
                name=context_name,
                access_token=credentials["access_token"],
                user_id=credentials["user_id"],
                workspace_id=credentials["workspace_id"],
            )
            action = "updated"
        else:
            add_context(
                session,
                name=context_name,
                access_token=credentials["access_token"],
                user_id=credentials["user_id"],
                workspace_id=credentials["workspace_id"],
            )
            action = "created"

        set_current_context(session, context_name)

    output = {
        "context": context_name,
        "action": action,
        "user_id": credentials["user_id"],
        "workspace_id": credentials["workspace_id"],
    }
    with args.outfile as ofp:
        json.dump(output, ofp)


def handle_cert_generate(args: argparse.Namespace) -> None:
    cert_path, key_path = generate_self_signed_cert(args.config_dir)

    output = {"cert_path": str(cert_path), "key_path": str(key_path)}
    with args.outfile as ofp:
        json.dump(output, ofp)


def handle_cert_info(args: argparse.Namespace) -> None:
    cert_info = get_cert_info(args.config_dir)
    if cert_info is None:
        raise ValueError(
            "No certificate found. Generate one with: clacks auth cert generate"
        )

    output = {
        "subject": cert_info["subject"],
        "not_valid_before": str(cert_info["not_valid_before"]),
        "not_valid_after": str(cert_info["not_valid_after"]),
        "cert_path": str(cert_info["cert_path"]),
        "key_path": str(cert_info["key_path"]),
    }
    with args.outfile as ofp:
        json.dump(output, ofp)


def handle_status(args: argparse.Namespace) -> None:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        client = WebClient(token=context.access_token)

        user_name = None
        user_email = None
        try:
            user_response = client.users_info(user=context.user_id)
            user = user_response["user"]
            user_name = user.get("real_name")
            user_email = user.get("profile", {}).get("email")
        except SlackApiError:
            pass

        workspace_name = None
        try:
            team_response = client.team_info()
            team = team_response["team"]
            workspace_name = team.get("name")
        except SlackApiError:
            pass

        output = {
            "context": context.name,
            "user_name": user_name,
            "user_id": context.user_id,
            "user_email": user_email,
            "workspace_id": context.workspace_id,
            "workspace_name": workspace_name,
        }
        with args.outfile as ofp:
            json.dump(output, ofp)


def handle_logout(args: argparse.Namespace) -> None:
    from slack_sdk import WebClient

    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        if args.context:
            context = get_context(session, args.context)
            if context is None:
                raise ValueError(f"Context '{args.context}' not found.")
        else:
            context = get_current_context(session)
            if context is None:
                raise ValueError("No active authentication context.")

        client = WebClient(token=context.access_token)
        response = client.auth_revoke()

        delete_context(session, context.name)

    with args.outfile as ofp:
        json.dump(response.data, ofp)


def generate_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Slack authentication commands",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        help="Configuration directory (default: platform-specific user config dir)",
    )

    subparsers = parser.add_subparsers(dest="auth_command")

    login_parser = subparsers.add_parser(
        "login", help="Authenticate with Slack via OAuth"
    )
    login_parser.add_argument(
        "-c",
        "--context",
        type=str,
        help="Name for this authentication context",
    )
    login_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing context if it exists",
    )
    login_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    login_parser.set_defaults(func=handle_login)

    cert_parser = subparsers.add_parser("cert", help="Manage SSL certificates")
    cert_parser.set_defaults(func=lambda args: cert_parser.print_help())
    cert_subparsers = cert_parser.add_subparsers(dest="cert_command")

    cert_generate_parser = cert_subparsers.add_parser(
        "generate", help="Generate new self-signed certificate"
    )
    cert_generate_parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        default=None,
        help="Configuration directory (default: platform-specific user config dir)",
    )
    cert_generate_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    cert_generate_parser.set_defaults(func=handle_cert_generate)

    cert_info_parser = cert_subparsers.add_parser(
        "info", help="Show certificate information"
    )
    cert_info_parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        default=None,
        help="Configuration directory (default: platform-specific user config dir)",
    )
    cert_info_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    cert_info_parser.set_defaults(func=handle_cert_info)

    status_parser = subparsers.add_parser(
        "status", help="Show current authentication status"
    )
    status_parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        default=None,
        help="Configuration directory (default: platform-specific user config dir)",
    )
    status_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    status_parser.set_defaults(func=handle_status)

    logout_parser = subparsers.add_parser("logout", help="Log out and delete context")
    logout_parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        default=None,
        help="Configuration directory (default: platform-specific user config dir)",
    )
    logout_parser.add_argument(
        "-c",
        "--context",
        type=str,
        default=None,
        help="Context name to logout (default: current context)",
    )
    logout_parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )
    logout_parser.set_defaults(func=handle_logout)

    return parser
