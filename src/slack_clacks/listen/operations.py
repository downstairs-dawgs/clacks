"""
Core listen operations using Slack Web API.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def _call_with_backoff(
    func: Any,
    max_retries: int = 5,
    base_delay: float = 1.0,
    **kwargs: Any,
) -> Any:
    """Call a Slack API function with exponential backoff on rate limit."""
    for attempt in range(max_retries):
        try:
            return func(**kwargs)
        except SlackApiError as e:
            if e.response.get("error") == "ratelimited":
                if attempt == max_retries - 1:
                    raise
                # Get retry-after header or use exponential backoff
                retry_after = int(e.response.headers.get("Retry-After", 0))
                delay = max(retry_after, base_delay * (2**attempt))
                time.sleep(delay)
            else:
                raise
    return None  # Should never reach here


def listen_channel(
    client: WebClient,
    channel_id: str,
    thread_ts: str | None = None,
    interval: float = 2.0,
    timeout: float | None = None,
    include_history: int = 0,
    continuous: bool = False,
) -> Iterator[dict]:
    """
    Yield new messages as they appear in channel or thread.

    Args:
        client: Slack WebClient instance
        channel_id: Channel ID to listen to
        thread_ts: If provided, listen to thread replies instead of channel
        interval: Poll interval in seconds (default: 2.0)
        timeout: Exit after this many seconds (default: None = infinite)
        include_history: Include last N messages on start (default: 0)
        continuous: If False (default), exit after yielding first new message.
                   If True, keep listening indefinitely.

    Yields:
        Message dicts with 'received_at' ISO timestamp added
    """
    start_time = time.monotonic()
    latest_ts: str | None = None

    # Fetch history if requested
    if include_history > 0:
        messages: list[Any]
        if thread_ts:
            response = _call_with_backoff(
                client.conversations_replies,
                channel=channel_id,
                ts=thread_ts,
                limit=include_history,
            )
            messages = response.get("messages", [])
            # First message is parent, rest are replies
            if len(messages) > 1:
                messages = messages[1:]  # Skip parent
            else:
                messages = []
        else:
            response = _call_with_backoff(
                client.conversations_history,
                channel=channel_id,
                limit=include_history,
            )
            messages = response.get("messages", [])

        # Messages come in reverse chronological order, reverse to chronological
        messages = list(reversed(messages))

        for msg in messages:
            msg["received_at"] = datetime.now(timezone.utc).isoformat()
            yield msg
            # Track latest timestamp seen
            msg_ts = msg.get("ts")
            if msg_ts and (latest_ts is None or msg_ts > latest_ts):
                latest_ts = msg_ts

    # If no history fetched, start from now
    if latest_ts is None:
        latest_ts = str(time.time())

    # Poll for new messages
    while True:
        if timeout is not None:
            elapsed = time.monotonic() - start_time
            if elapsed >= timeout:
                break

        time.sleep(interval)

        # Add epsilon to make oldest exclusive (Slack's oldest is inclusive)
        exclusive_oldest = str(float(latest_ts) + 0.000001)

        if thread_ts:
            response = _call_with_backoff(
                client.conversations_replies,
                channel=channel_id,
                ts=thread_ts,
                oldest=exclusive_oldest,
            )
            messages = response.get("messages", [])
            # Filter out parent and already-seen messages
            messages = [
                m
                for m in messages
                if m.get("ts") != thread_ts and m.get("ts", "") > latest_ts
            ]
        else:
            response = _call_with_backoff(
                client.conversations_history,
                channel=channel_id,
                oldest=exclusive_oldest,
            )
            messages = response.get("messages", [])
            # Filter already-seen messages (defensive deduplication)
            messages = [m for m in messages if m.get("ts", "") > latest_ts]

        # Messages come in reverse chronological order, reverse to chronological
        messages = list(reversed(messages))

        for msg in messages:
            msg["received_at"] = datetime.now(timezone.utc).isoformat()
            yield msg
            # Track latest timestamp seen
            msg_ts = msg.get("ts")
            if msg_ts and (latest_ts is None or msg_ts > latest_ts):
                latest_ts = msg_ts

            # Exit after first message unless continuous mode
            if not continuous:
                return


def load_skill_content(skill_param: str) -> str:
    """
    Load skill content from file path or skill name.

    Args:
        skill_param: Path to SKILL.md file OR skill name (e.g., "slack-summarizer")

    Returns:
        Content of the skill file

    Raises:
        FileNotFoundError: If skill file doesn't exist
    """
    # First check if it's a real path that exists on disk
    if os.path.exists(skill_param):
        # It's a file path - use it directly
        abs_path = os.path.abspath(skill_param)
        with open(abs_path, "r") as f:
            return f.read()

    # Not a real path - treat as skill name
    # Try in ~/.claude/skills/
    home = os.path.expanduser("~")
    skill_path = os.path.join(home, ".claude", "skills", skill_param, "SKILL.md")

    if os.path.exists(skill_path):
        with open(skill_path, "r") as f:
            return f.read()

    # Try in .claude/skills/ (project local)
    local_skill_path = os.path.join(".claude", "skills", skill_param, "SKILL.md")

    if os.path.exists(local_skill_path):
        with open(local_skill_path, "r") as f:
            return f.read()

    # Not found anywhere
    raise FileNotFoundError(
        f"Skill not found: {skill_param}\n"
        f"Tried:\n"
        f"  - {skill_param} (as file path)\n"
        f"  - {skill_path} (global skills)\n"
        f"  - {local_skill_path} (project skills)"
    )


def spawn_claude_with_skill(
    message: dict,
    skill_param: str,
    cwd: str | None = None,
    timeout: float | None = None,
) -> int:
    """
    Spawn Claude Code instance with skill for processing message.

    Args:
        message: Full message dict (will be serialized to JSON)
        skill_param: Path to SKILL.md file or skill name (e.g., "slack-summarizer")
        cwd: Working directory for Claude (default: current directory)
        timeout: Timeout in seconds (default: None = no timeout)

    Returns:
        Exit code from Claude process (0 = success)

    Raises:
        FileNotFoundError: If claude command not found in PATH or skill file missing
    """
    # Check if claude command exists
    claude_path = shutil.which("claude")
    if not claude_path:
        raise FileNotFoundError(
            "claude command not found in PATH. "
            "Install Claude Code from https://claude.ai/download"
        )

    # Load skill content from file
    skill_content = load_skill_content(skill_param)

    # Serialize message to JSON
    message_json = json.dumps(message)

    # Construct command using -p (print mode) and --system-prompt
    cmd = ["claude", "-p", "--system-prompt", skill_content, message_json]

    # Determine working directory
    work_dir = cwd if cwd else None

    try:
        result = subprocess.run(
            cmd,
            cwd=work_dir,
            stdin=subprocess.DEVNULL,
            check=False,  # Don't raise on non-zero exit
            timeout=timeout,
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        print(
            f"Claude Code execution timed out after {timeout}s",
            file=sys.stderr,
        )
        return -1
    except Exception as e:
        print(
            f"Error executing Claude Code: {e}",
            file=sys.stderr,
        )
        return -1
