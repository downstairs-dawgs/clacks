import argparse
import json
import os
import shutil
import subprocess
import sys

from slack_clacks.auth.client import create_client
from slack_clacks.auth.validation import get_scopes_for_mode, validate
from slack_clacks.configuration.database import (
    ensure_db_updated,
    get_current_context,
    get_session,
)
from slack_clacks.messaging.operations import (
    open_dm_channel,
    resolve_channel_id,
    resolve_user_id,
)
from slack_clacks.upload.operations import (
    filetype_to_extension,
    infer_filetype,
    upload_content,
    upload_file,
)

_CLIPBOARD_COMMANDS = ["pbcopy", "xclip", "xsel"]


def _copy_to_clipboard(text: str) -> None:
    """Copy text to clipboard if a supported tool is available."""
    for cmd in _CLIPBOARD_COMMANDS:
        if shutil.which(cmd):
            args = [cmd]
            if cmd == "xclip":
                args += ["-selection", "clipboard"]
            elif cmd == "xsel":
                args += ["--clipboard", "--input"]
            subprocess.run(args, input=text.encode(), check=True)
            print("(copied to clipboard)", file=sys.stderr)
            return
    print(
        "(not copied to clipboard — no clipboard tool found)",
        file=sys.stderr,
    )


def _extract_permalink(response: dict | bytes) -> str:
    """Extract a permalink from a files_upload_v2 response payload."""
    file_data = _extract_primary_file_data(response)
    if isinstance(file_data, dict):
        return file_data.get("permalink", "")
    return ""


def _extract_primary_file_data(response: dict | bytes) -> dict | None:
    """Extract the first file payload from a files_upload_v2 response."""
    if not isinstance(response, dict):
        return None

    file_data = response.get("file")
    if not file_data:
        files = response.get("files", [])
        if files:
            file_data = files[0]

    if isinstance(file_data, dict):
        return file_data

    return None


def _extract_shared_message_ts(response: dict | bytes, channel_id: str) -> str | None:
    """Extract the message timestamp for a freshly shared file/snippet."""
    file_data = _extract_primary_file_data(response)
    if file_data is None:
        return None

    shares = file_data.get("shares", {})
    if not isinstance(shares, dict):
        return None

    for visibility in ("private", "public"):
        visibility_shares = shares.get(visibility, {})
        if not isinstance(visibility_shares, dict):
            continue
        channel_shares = visibility_shares.get(channel_id, [])
        if not isinstance(channel_shares, list):
            continue
        for share in channel_shares:
            if isinstance(share, dict):
                ts = share.get("ts")
                if isinstance(ts, str) and ts:
                    return ts

    return None


def _extract_response_data(response: object) -> dict | None:
    """Normalize Slack SDK responses and bare dicts to a plain dict."""
    if isinstance(response, dict):
        return response

    data = getattr(response, "data", None)
    if isinstance(data, dict):
        return data

    return None


def _resolve_message_permalink(
    client, upload_response: dict | bytes, channel_id: str
) -> str | None:
    """Resolve a permalink for the newly posted message that shared the snippet."""
    message_ts = _extract_shared_message_ts(upload_response, channel_id)
    if message_ts is None:
        return None

    permalink_response = client.chat_getPermalink(
        channel=channel_id,
        message_ts=message_ts,
    )
    data = _extract_response_data(permalink_response)
    if data is None:
        return None

    permalink = data.get("permalink")
    if isinstance(permalink, str) and permalink:
        return permalink

    return None


def handle_upload(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        scopes = get_scopes_for_mode(context.app_type)
        validate("files:write", scopes, raise_on_error=True)

        client = create_client(context.access_token, context.app_type)

        channel_id = None
        if args.channel:
            channel_id = resolve_channel_id(client, args.channel, session, context.name)
        elif args.user:
            user_id = resolve_user_id(client, args.user, session, context.name)
            channel_id = open_dm_channel(client, user_id)
            if channel_id is None:
                raise ValueError(f"Failed to open DM with user '{args.user}'.")

        # Determine filename and filetype
        if args.file:
            filename = args.filename or os.path.basename(args.file)
        elif args.filename:
            filename = args.filename
        else:
            ext = filetype_to_extension(args.filetype) if args.filetype else ".txt"
            filename = f"snippet{ext}"

        filetype = args.filetype or infer_filetype(filename)

        thread_ts = args.thread

        if args.file:
            response = upload_file(
                client,
                file_path=args.file,
                filename=filename,
                filetype=filetype,
                title=args.title,
                comment=args.comment,
                channel_id=channel_id,
                thread_ts=thread_ts,
            )
        else:
            content = sys.stdin.read()
            if not content:
                raise ValueError("No input: provide -f/--file or pipe to stdin.")
            response = upload_content(
                client,
                content=content,
                filename=filename,
                filetype=filetype,
                title=args.title,
                comment=args.comment,
                channel_id=channel_id,
                thread_ts=thread_ts,
            )

        permalink = _extract_permalink(response)

        with args.outfile as ofp:
            json.dump(response, ofp)

        if channel_id:
            print(f"Shared: {permalink}", file=sys.stderr)
        else:
            print(permalink, file=sys.stderr)

        if permalink:
            _copy_to_clipboard(permalink)


def handle_snippet(args: argparse.Namespace) -> None:
    ensure_db_updated(config_dir=args.config_dir)
    with get_session(args.config_dir) as session:
        context = get_current_context(session)
        if context is None:
            raise ValueError(
                "No active authentication context. Authenticate with: clacks auth login"
            )

        scopes = get_scopes_for_mode(context.app_type)
        validate("files:write", scopes, raise_on_error=True)

        if args.outfile is sys.stdout:
            raise ValueError(
                "For clacks snippet, --outfile cannot be stdout because stdout is reserved for the message permalink."
            )

        client = create_client(context.access_token, context.app_type)

        channel_id = open_dm_channel(client, context.user_id)
        if channel_id is None:
            raise ValueError("Failed to open DM with the authenticated user.")

        if args.filename:
            filename = args.filename
        else:
            ext = filetype_to_extension(args.filetype) if args.filetype else ".txt"
            filename = f"snippet{ext}"

        filetype = args.filetype or infer_filetype(filename)

        content = sys.stdin.read()
        if not content:
            raise ValueError("No input: pipe snippet content to stdin.")

        response = upload_content(
            client,
            content=content,
            filename=filename,
            filetype=filetype,
            title=args.title,
            comment=args.comment,
            channel_id=channel_id,
            thread_ts=args.thread,
        )

        message_permalink = _resolve_message_permalink(client, response, channel_id)
        if message_permalink is None:
            raise ValueError("Failed to resolve a permalink for the posted snippet message.")

        if args.outfile is not None:
            with args.outfile as ofp:
                json.dump(response, ofp)

        print(message_permalink)
        print(f"Shared: {message_permalink}", file=sys.stderr)

        _copy_to_clipboard(message_permalink)


def generate_upload_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Upload a file or snippet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        help="Configuration directory (default: platform-specific user config dir)",
    )

    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument(
        "-c",
        "--channel",
        type=str,
        help="Channel to share to (e.g., #general, C123456)",
    )
    target_group.add_argument(
        "-u",
        "--user",
        type=str,
        help="User to DM the file to (e.g., @username, U123456)",
    )

    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="File path to upload (if omitted, reads stdin)",
    )
    parser.add_argument(
        "-n",
        "--filename",
        type=str,
        help="Display filename in Slack (default: inferred from -f or snippet.<ext>)",
    )
    parser.add_argument(
        "-t",
        "--filetype",
        type=str,
        help="Syntax highlighting type: python, go, javascript, shell, etc.",
    )
    parser.add_argument(
        "--title",
        type=str,
        help="Snippet title in Slack",
    )
    parser.add_argument(
        "-m",
        "--comment",
        type=str,
        help="Initial comment posted with the snippet",
    )
    parser.add_argument(
        "--thread",
        type=str,
        help="Thread timestamp to reply in a thread",
    )
    parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=sys.stdout,
        help="Output file for JSON results (default: stdout)",
    )

    parser.set_defaults(func=handle_upload)

    return parser


def generate_snippet_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a snippet from stdin in a DM to yourself",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-D",
        "--config-dir",
        type=str,
        help="Configuration directory (default: platform-specific user config dir)",
    )
    parser.add_argument(
        "-n",
        "--filename",
        type=str,
        help="Display filename in Slack (default: snippet.<ext>)",
    )
    parser.add_argument(
        "-t",
        "--filetype",
        type=str,
        help="Syntax highlighting type: python, go, javascript, shell, etc.",
    )
    parser.add_argument(
        "--title",
        type=str,
        help="Snippet title in Slack",
    )
    parser.add_argument(
        "-m",
        "--comment",
        type=str,
        help="Initial comment posted with the snippet",
    )
    parser.add_argument(
        "--thread",
        type=str,
        help="Thread timestamp in your self-DM to reply in a thread",
    )
    parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("a"),
        default=None,
        help="Optional output file for JSON results (stdout prints the message permalink)",
    )

    parser.set_defaults(func=handle_snippet)

    return parser
