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

        # Extract permalink from response
        # files_upload_v2 returns "file" (single) or "files" (list)
        permalink = ""
        if isinstance(response, dict):
            file_data = response.get("file")
            if not file_data:
                files = response.get("files", [])
                if files:
                    file_data = files[0]
            if isinstance(file_data, dict):
                permalink = file_data.get("permalink", "")

        if args.outfile is not sys.stdout:
            with args.outfile as ofp:
                json.dump(response, ofp)

        if channel_id:
            print(f"Shared: {permalink}")
        else:
            print(permalink)

        if permalink:
            _copy_to_clipboard(permalink)


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
