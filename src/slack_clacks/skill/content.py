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

Install clacks and authenticate:
```bash
uv tool install slack-clacks
clacks auth login -c <context-name>
```

## Sending Messages

Send to channel:
```bash
clacks send -c "#general" -m "Hello world"
clacks send -c "C123456" -m "Hello world"
```

Send direct message:
```bash
clacks send -u "@username" -m "Hello"
clacks send -u "U123456" -m "Hello"
```

Reply to thread:
```bash
clacks send -c "#general" -m "Reply text" -t "1234567890.123456"
```

## Reading Messages

Read from channel:
```bash
clacks read -c "#general"
clacks read -c "#general" -l 50
```

Read DMs:
```bash
clacks read -u "@username"
```

Read thread:
```bash
clacks read -c "#general" -t "1234567890.123456"
```

## Recent Activity

View recent messages across all conversations:
```bash
clacks recent
clacks recent -l 50
```

## Reactions

Add emoji reaction:
```bash
clacks react -c "#general" -m "1234567890.123456" -e ":thumbsup:"
```

Remove reaction:
```bash
clacks react -c "#general" -m "1234567890.123456" -e ":thumbsup:" --remove
```

## Delete Messages

Delete a message (your own messages only):
```bash
clacks delete -c "#general" -m "1234567890.123456"
```

## Rolodex (Aliases)

Sync users and channels from Slack:
```bash
clacks rolodex sync
```

List aliases:
```bash
clacks rolodex list
clacks rolodex list -T user
clacks rolodex list -T channel
```

## Context Management

List available contexts:
```bash
clacks config contexts
```

Switch context:
```bash
clacks config switch -C <context-name>
```

View current config:
```bash
clacks config info
```

## Output

All commands output JSON to stdout.
"""
