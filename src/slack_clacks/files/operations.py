"""
Core file operations using Slack Web API.
"""

import re
import sys
import urllib.request
from pathlib import Path

from slack_sdk import WebClient

from slack_clacks.auth.constants import MODE_COOKIE

_CHUNK_SIZE = 8192


def get_file_info(client: WebClient, file_id: str) -> dict | bytes:
    """Get file metadata from Slack."""
    response = client.files_info(file=file_id)
    return response.data


def list_files(
    client: WebClient,
    channel: str | None = None,
    user: str | None = None,
    limit: int = 20,
) -> dict | bytes:
    """List files, optionally filtered by channel and/or user."""
    kwargs: dict = {"count": limit}
    if channel:
        kwargs["channel"] = channel
    if user:
        kwargs["user"] = user
    response = client.files_list(**kwargs)
    return response.data


def extract_file_id_from_permalink(url: str) -> str:
    """
    Extract a Slack file ID from a permalink URL.

    Supports formats like:
    - https://workspace.slack.com/files/U.../F2147483862/filename.txt
    - https://files.slack.com/files-pri/T.../F2147483862/filename.txt
    """
    match = re.search(r"/(F[A-Z0-9]+)", url)
    if not match:
        raise ValueError(f"Could not extract file ID from URL: {url}")
    return match.group(1)


def _build_download_headers(access_token: str, app_type: str) -> dict[str, str]:
    """Build HTTP headers for downloading a private Slack file."""
    if app_type == MODE_COOKIE:
        if "|" in access_token:
            token, cookie = access_token.split("|", 1)
            return {
                "Authorization": f"Bearer {token}",
                "Cookie": f"d={cookie}",
            }
        else:
            raise ValueError(
                "Cookie mode requires token in format: xoxc-token|d-cookie-value"
            )
    return {"Authorization": f"Bearer {access_token}"}


def download_file_to_path(
    url: str, access_token: str, app_type: str, output_path: Path
) -> int:
    """
    Download a file from Slack to a local path.
    Returns the number of bytes written.
    """
    headers = _build_download_headers(access_token, app_type)
    req = urllib.request.Request(url, headers=headers)
    total = 0
    with urllib.request.urlopen(req) as resp, open(output_path, "wb") as f:
        while True:
            chunk = resp.read(_CHUNK_SIZE)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
    return total


def download_file_to_stdout(url: str, access_token: str, app_type: str) -> int:
    """
    Download a file from Slack and write it to stdout.
    Returns the number of bytes written.
    """
    headers = _build_download_headers(access_token, app_type)
    req = urllib.request.Request(url, headers=headers)
    total = 0
    with urllib.request.urlopen(req) as resp:
        while True:
            chunk = resp.read(_CHUNK_SIZE)
            if not chunk:
                break
            sys.stdout.buffer.write(chunk)
            total += len(chunk)
    return total
