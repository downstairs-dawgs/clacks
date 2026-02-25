"""
CLI commands for file operations.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import cast

from slack_clacks.auth.client import create_client
from slack_clacks.auth.validation import get_scopes_for_mode, validate
from slack_clacks.configuration.database import (
    ensure_db_updated,
    get_current_context,
    get_session,
)
from slack_clacks.files.operations import (
    download_file_to_path,
    download_file_to_stdout,
    extract_file_id_from_permalink,
    get_file_info,
    list_files,
)
from slack_clacks.messaging.operations import resolve_channel_id, resolve_user_id
from slack_clacks.upload.cli import generate_upload_parser


def handle_download(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        scopes = get_scopes_for_mode(context.app_type)
        validate("files:read", scopes, raise_on_error=True)

        client = create_client(context.access_token, context.app_type)

        # Resolve file ID
        if args.file_id:
            file_id = args.file_id
        else:
            file_id = extract_file_id_from_permalink(args.permalink)

        # Get file metadata
        info = cast(dict, get_file_info(client, file_id))
        file_data = info.get("file", {})
        filename = file_data.get("name", file_id)
        download_url = file_data.get("url_private_download") or file_data.get(
            "url_private"
        )

        if not download_url:
            raise ValueError(f"No download URL available for file {file_id}")

        # Download to stdout
        if args.write == "-":
            nbytes = download_file_to_stdout(
                download_url, context.access_token, context.app_type
            )
            print(f"{filename}: {nbytes} bytes", file=sys.stderr)
            return

        # Determine output path
        if args.write:
            output_path = Path(args.write)
        else:
            output_path = Path(filename)

        # Check for existing file
        if output_path.exists() and not args.force:
            raise FileExistsError(
                f"File already exists: {output_path}. Use --force to overwrite."
            )

        nbytes = download_file_to_path(
            download_url, context.access_token, context.app_type, output_path
        )
        print(f"{output_path}: {nbytes} bytes", file=sys.stderr)


def handle_list(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        scopes = get_scopes_for_mode(context.app_type)
        validate("files:read", scopes, raise_on_error=True)

        client = create_client(context.access_token, context.app_type)

        # Resolve channel/user identifiers to IDs
        channel_id = None
        if args.channel:
            channel_id = resolve_channel_id(client, args.channel, session, context.name)

        user_id = None
        if args.user:
            user_id = resolve_user_id(client, args.user, session, context.name)

        result = list_files(client, channel=channel_id, user=user_id, limit=args.limit)
        json.dump(result, sys.stdout)


def handle_info(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        scopes = get_scopes_for_mode(context.app_type)
        validate("files:read", scopes, raise_on_error=True)

        client = create_client(context.access_token, context.app_type)

        result = get_file_info(client, args.file_id)
        json.dump(result, sys.stdout)


def generate_files_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Upload, download, list, and inspect files"
    )
    parser.set_defaults(func=lambda _: parser.print_help())

    subparsers = parser.add_subparsers(dest="files_command")

    # --- download ---
    dl_parser = subparsers.add_parser("download", help="Download a file from Slack")
    dl_parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        default=None,
        help="Configuration directory",
    )
    id_group = dl_parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument(
        "-i",
        "--file-id",
        type=str,
        help="Slack file ID (e.g., F2147483862)",
    )
    id_group.add_argument(
        "--permalink",
        type=str,
        help="Slack file permalink URL",
    )
    dl_parser.add_argument(
        "-w",
        "--write",
        type=str,
        default=None,
        help="Output path (default: original filename in CWD, use - for stdout)",
    )
    dl_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing file without prompting",
    )
    dl_parser.set_defaults(func=handle_download)

    # --- list ---
    list_parser = subparsers.add_parser("list", help="List files")
    list_parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        default=None,
        help="Configuration directory",
    )
    list_parser.add_argument(
        "-c",
        "--channel",
        type=str,
        help="Filter by channel",
    )
    list_parser.add_argument(
        "-u",
        "--user",
        type=str,
        help="Filter by user",
    )
    list_parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=20,
        help="Max files to list (default: 20)",
    )
    list_parser.set_defaults(func=handle_list)

    # --- info ---
    info_parser = subparsers.add_parser("info", help="Show file metadata")
    info_parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        default=None,
        help="Configuration directory",
    )
    info_parser.add_argument(
        "-i",
        "--file-id",
        type=str,
        required=True,
        help="Slack file ID (e.g., F2147483862)",
    )
    info_parser.set_defaults(func=handle_info)

    # --- upload ---
    upload_parser = generate_upload_parser()
    subparsers.add_parser(
        "upload",
        parents=[upload_parser],
        add_help=False,
        help=upload_parser.description,
    )

    return parser
