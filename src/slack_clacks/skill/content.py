"""
Skill bundle content for clacks.
"""

import hashlib
import json
from importlib.metadata import PackageNotFoundError, version

SKILL_MD = """\
---
name: clacks
description: >-
  Send and read Slack messages using clacks CLI. Use when user asks to send
  Slack messages, read channels, wait for responses, or interact with Slack.
---

# Slack Integration via Clacks

Use the `clacks` CLI to interact with Slack workspaces.

## Rolodex Sync (Do This First)

The rolodex maps `@display-names` to Slack user/channel IDs.
**Always use the rolodex to resolve @-mentions** —
never guess or hardcode Slack IDs.

At the start of any conversation that uses clacks, check when
the rolodex was last synced by reading
`~/.claude/skills/clacks/.rolodex-last-sync`. If the file
doesn't exist or the timestamp is older than 7 days,
**ask the user** if they'd like to sync the rolodex before
proceeding. Do not sync automatically — always ask first.

After syncing, write the current ISO 8601 timestamp to
`~/.claude/skills/clacks/.rolodex-last-sync`.

```bash
# Sync the rolodex
uvx --from slack-clacks clacks rolodex sync

# Then look up users/channels before sending
uvx --from slack-clacks clacks rolodex list
uvx --from slack-clacks clacks rolodex list -T user
uvx --from slack-clacks clacks rolodex list -T channel
```

When composing messages that mention people or target specific
users/channels, **always look up the rolodex first** to resolve
names to the correct Slack IDs.

## Slack Markdown

Slack uses its own markup syntax — it is **not** standard Markdown. Key differences:
- Bold: `*bold*` (not `**bold**`)
- Italic: `_italic_` (not `*italic*`)
- Strikethrough: `~struck~` (not `~~struck~~`)
- Code: `` `code` `` (same)
- Code block: ` ```code``` ` (same, but no language hint)
- Links: `<https://example.com|link text>` (not `[text](url)`)
- User mentions: `<@U123456>` (use rolodex to get the ID)
- Channel mentions: `<#C123456>` (use rolodex to get the ID)
- Bullet lists: use plain `- item` or `• item`
- Ordered lists: not natively supported; use `1. item` as plain text
- Block quotes: `>` at the start of a line (same)

**Always use Slack's markup syntax** when composing messages,
not GitHub-flavored or standard Markdown.

## Prerequisites

Authenticate with your Slack workspace (requires uv):
```bash
uvx --from slack-clacks clacks auth login -c <context-name>
```

Using `uvx` ensures you always run the latest version. If clacks is installed globally
via `uv tool install slack-clacks` or `pip install slack-clacks`, use `clacks` directly.

If `clacks` warns that the installed skill is outdated, reinstall the matching skill
bundle with `clacks skill --mode <current-mode> --force` or
`uvx --from slack-clacks clacks skill --mode <current-mode> --force`.
Use `-project` modes for project-local installs.

## Sending Messages

Send to channel:
```bash
uvx --from slack-clacks clacks send -c "#general" -m "Hello world"
uvx --from slack-clacks clacks send -c "C123456" -m "Hello world"
```

Send direct message:
```bash
uvx --from slack-clacks clacks send -u "@username" -m "Hello"
uvx --from slack-clacks clacks send -u "U123456" -m "Hello"
```

Reply to thread:
```bash
uvx --from slack-clacks clacks send -c "#general" -m "Reply text" -t "1234567890.123456"
```

## Scheduling Messages

Schedule a message for future delivery:
```bash
uvx --from slack-clacks clacks schedule -c "#general" \\
  -m "Reminder: standup" --at "9:45am UTC"
uvx --from slack-clacks clacks schedule -u "@username" \\
  -m "Don't forget!" --at "in 2 hours"
uvx --from slack-clacks clacks schedule -c "#general" \\
  -m "Weekly reminder" --at "2026-03-15T09:00:00+01:00"
```

Supported time formats for `--at`:
- Time with timezone: `9pm CET`, `21:00 EST`, `2:30pm UTC`
- Relative: `in 30 minutes`, `in 2 hours`, `in 1 day`
- ISO 8601: `2026-03-15T09:00:00+01:00`
- Unix timestamp: `1773500000`

Note: Slack limits scheduling to 120 days in the future.

## Reading Messages

Read from channel:
```bash
uvx --from slack-clacks clacks read -c "#general"
uvx --from slack-clacks clacks read -c "#general" -l 50
```

Read DMs:
```bash
uvx --from slack-clacks clacks read -u "@username"
```

Read thread:
```bash
uvx --from slack-clacks clacks read -c "#general" -t "1234567890.123456"
```

## Recent Activity

View recent messages across all conversations:
```bash
uvx --from slack-clacks clacks recent
uvx --from slack-clacks clacks recent -l 50
```

## Reactions

Add emoji reaction:
```bash
uvx --from slack-clacks clacks react -c "#general" -m "123456.123" -e ":+1:"
```

Remove reaction:
```bash
uvx --from slack-clacks clacks react -c "#general" -m "123456.123" -e ":+1:" --remove
```

## Delete Messages

Delete a message (your own messages only):
```bash
uvx --from slack-clacks clacks delete -c "#general" -m "1234567890.123456"
```

## Uploading Files and Snippets

Upload a file to a channel:
```bash
uvx --from slack-clacks clacks upload -c "#general" -f /path/to/file.py
```

Pipe command output as a snippet:
```bash
cat script.py | uvx --from slack-clacks clacks upload -c "#ops" -t python
```

Private upload (returns permalink, not shared to any channel):
```bash
echo "print('hello')" | uvx --from slack-clacks clacks upload -t python
```

## Listening for Messages

Listen for new messages in a channel (outputs NDJSON, one message per line):
```bash
uvx --from slack-clacks clacks listen "#general"
```

Listen with history (fetch last N messages first):
```bash
uvx --from slack-clacks clacks listen "#general" --include-history 5
```

Listen to thread replies:
```bash
uvx --from slack-clacks clacks listen "#general" --thread "1234567890.123456"
```

Filter by sender (wait for response from specific user):
```bash
uvx --from slack-clacks clacks listen "#general" --from "@username"
```

Set timeout (exit after N seconds):
```bash
uvx --from slack-clacks clacks listen "#general" --timeout 300
```

Options:
- `--interval SECONDS` - Poll interval (default: 2.0)
- `--include-bots` - Include bot messages (excluded by default)
- `-o FILE` - Write to file instead of stdout

### When to Use Listen

Use `clacks listen` when:
- Waiting for a response from someone after sending a message
- Monitoring a channel for new activity
- Waiting for a specific user to reply in a thread

Example workflow - send message and wait for reply:
```bash
# Send a message
uvx --from slack-clacks clacks send -c "#general" -m "Question for @alice"

# Wait for alice's response (timeout after 5 minutes)
uvx --from slack-clacks clacks listen "#general" --from "@alice" --timeout 300
```

## Context Management

List available contexts:
```bash
uvx --from slack-clacks clacks config contexts
```

Switch context:
```bash
uvx --from slack-clacks clacks config switch -C <context-name>
```

View current config:
```bash
uvx --from slack-clacks clacks config info
```

## Output

All commands output JSON to stdout.
The `listen` command outputs NDJSON (one JSON object per line).
"""

OPENAI_YAML = """\
interface:
  display_name: "Clacks"
  short_description: "Send and read Slack messages in Codex"
  default_prompt: "Use $clacks to send, read, and monitor Slack messages for this task."
"""

LICENSE_TXT = """\
MIT License

Copyright (c) 2025 Neeraj Kashyap

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

BUNDLE_FILE_PATHS: tuple[str, ...] = (
    "SKILL.md",
    "agents/openai.yaml",
    "LICENSE.txt",
)

MANIFEST_FILENAME = ".clacks-skill-manifest.json"
MANIFEST_VERSION = 1


def _get_package_version() -> str:
    """Return the installed slack-clacks version when available."""
    try:
        return version("slack-clacks")
    except PackageNotFoundError:
        return "unknown"


def _get_resource_contents() -> dict[str, str]:
    """Return the static bundle files shipped with the package."""
    return {
        "SKILL.md": SKILL_MD,
        "agents/openai.yaml": OPENAI_YAML,
        "LICENSE.txt": LICENSE_TXT,
    }


def _get_bundle_hash(bundle_contents: dict[str, str]) -> str:
    """Return a deterministic hash for the shipped bundle contents."""
    payload = json.dumps(
        bundle_contents,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_manifest(bundle_contents: dict[str, str]) -> dict[str, object]:
    """Build the manifest describing the shipped bundle."""
    return {
        "bundle_files": sorted(bundle_contents),
        "bundle_hash": _get_bundle_hash(bundle_contents),
        "manifest_version": MANIFEST_VERSION,
        "package_version": _get_package_version(),
    }


def get_bundle_manifest() -> dict[str, object]:
    """Return the manifest for the shipped bundle."""
    return _build_manifest(_get_resource_contents())


def get_bundle_contents() -> dict[str, str]:
    """Return bundled skill files keyed by relative path."""
    bundle_contents = _get_resource_contents()
    bundle_contents[MANIFEST_FILENAME] = (
        json.dumps(_build_manifest(bundle_contents), indent=2, sort_keys=True) + "\n"
    )
    return bundle_contents


def get_skill_md() -> str:
    """Return SKILL.md from the bundled resources."""
    return SKILL_MD
