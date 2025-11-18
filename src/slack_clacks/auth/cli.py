import argparse

from slack_clacks.configuration.database import (
    add_context,
    ensure_db_updated,
    get_context,
    get_session,
    set_current_context,
    update_context,
)

from .cert import generate_self_signed_cert, get_cert_info
from .oauth import start_oauth_flow


def handle_login(args: argparse.Namespace) -> None:
    try:
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
                    print(f"Context '{context_name}' already exists.")
                    print("Use --overwrite to replace it.")
                    raise SystemExit(1)

                update_context(
                    session,
                    name=context_name,
                    access_token=credentials["access_token"],
                    user_id=credentials["user_id"],
                    workspace_id=credentials["workspace_id"],
                )
                print(f"Updated context: {context_name}")
            else:
                add_context(
                    session,
                    name=context_name,
                    access_token=credentials["access_token"],
                    user_id=credentials["user_id"],
                    workspace_id=credentials["workspace_id"],
                )
                print(f"Created context: {context_name}")

            set_current_context(session, context_name)

        print(f"Successfully authenticated and set current context: {context_name}")

    except Exception as e:
        print(f"Authentication failed: {e}")
        raise SystemExit(1)


def handle_cert_generate(args: argparse.Namespace) -> None:
    try:
        cert_path, key_path = generate_self_signed_cert(args.config_dir)
        print("Generated new self-signed certificate:")
        print(f"  Certificate: {cert_path}")
        print(f"  Private key: {key_path}")
    except Exception as e:
        print(f"Failed to generate certificate: {e}")
        raise SystemExit(1)


def handle_cert_info(args: argparse.Namespace) -> None:
    cert_info = get_cert_info(args.config_dir)
    if cert_info is None:
        print("No certificate found. Generate one with: clacks auth cert generate")
        raise SystemExit(1)

    print("Certificate information:")
    print(f"  Subject: {cert_info['subject']}")
    print(f"  Valid from: {cert_info['not_valid_before']}")
    print(f"  Valid until: {cert_info['not_valid_after']}")
    print(f"  Certificate: {cert_info['cert_path']}")
    print(f"  Private key: {cert_info['key_path']}")


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
    cert_info_parser.set_defaults(func=handle_cert_info)

    return parser
