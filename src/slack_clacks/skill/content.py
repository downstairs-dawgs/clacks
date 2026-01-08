"""
SKILL.md content for clacks.
"""

SKILL_MD = """\
---
name: clacks
description: >-
  Send and read Slack messages using clacks CLI.
  Use when user asks to send Slack messages, read channels, or interact with Slack.
---

# Slack Integration via Clacks

Use the `clacks` CLI to interact with Slack workspaces.

## Prerequisites

Authenticate with your Slack workspace (requires uv):
```bash
uvx --from slack-clacks clacks auth login -c <context-name>
```

Using `uvx` ensures you always run the latest version. If clacks is installed globally
via `uv tool install slack-clacks` or `pip install slack-clacks`, use `clacks` directly.

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

## Rolodex (Aliases)

Sync users and channels from Slack:
```bash
uvx --from slack-clacks clacks rolodex sync
```

List aliases:
```bash
uvx --from slack-clacks clacks rolodex list
uvx --from slack-clacks clacks rolodex list -T user
uvx --from slack-clacks clacks rolodex list -T channel
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
"""
