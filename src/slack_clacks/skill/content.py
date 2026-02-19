"""
SKILL.md content for clacks.
"""

SKILL_MD = """\
---
name: clacks
description: >-
  Send and read Slack messages using clacks CLI. Use when user asks to send
  Slack messages, read channels, wait for responses, or interact with Slack.
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

## Uploading Files and Snippets

Upload a file to a channel:
```bash
uvx --from slack-clacks clacks upload -c "#general" -f /path/to/file.py
```

Pipe command output as a snippet:
```bash
cat script.py | uvx --from slack-clacks clacks upload -c "#ops" -t python
kubectl logs pod | uvx --from slack-clacks clacks upload -c "#ops" -n pod-logs.txt
```

Upload to a DM:
```bash
uvx --from slack-clacks clacks upload -u "@username" -f report.csv
```

Private upload (returns permalink, not shared to any channel):
```bash
echo "print('hello')" | uvx --from slack-clacks clacks upload -t python
```

Options:
- `-f FILE` - File path to upload (if omitted, reads stdin)
- `-n NAME` - Display filename in Slack
- `-t TYPE` - Syntax highlighting: python, go, javascript, shell, etc.
- `--title TITLE` - Snippet title
- `-m COMMENT` - Initial comment posted with the snippet
- `--thread TS` - Reply in a thread
- `-o FILE` - Write full JSON response to file

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

Most commands output JSON to stdout.
The `listen` command outputs NDJSON (one JSON object per line).
The `upload` command prints the permalink to stdout and copies it to the clipboard.
"""
