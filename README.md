# clacks
the default mode of degenerate communication.

## Installation

**Recommended** - run directly without installation:
```bash
uvx --from slack-clacks clacks
```

**Alternative** - install globally with uv:
```bash
uv tool install slack-clacks
```

**Alternative** - works with pip, poetry, or any package manager:
```bash
pip install slack-clacks
```

All examples below use `uvx --from slack-clacks clacks`. If installed globally, replace with just `clacks`.

## Authentication

Authenticate via OAuth:
```bash
uvx --from slack-clacks clacks auth login -c <context-name>
```

### Modes

clacks supports three authentication modes:

#### clacks mode (default)

Full workspace access via OAuth.

```bash
uvx --from slack-clacks clacks auth login --mode clacks
```

Permissions: channels, groups, DMs, MPIMs, files, search

#### clacks-lite mode

Secure, DM-focused access via OAuth. Use for security-conscious environments where channel access isn't needed.

```bash
uvx --from slack-clacks clacks auth login --mode clacks-lite
```

Permissions: DMs, MPIMs, reactions only

#### cookie mode

Browser session authentication. Use for quick testing or when OAuth is impractical.

```bash
uvx --from slack-clacks clacks auth login --mode cookie
```

Extract xoxc token and d cookie from browser. No OAuth app needed. See [docs/cookie-auth.md](docs/cookie-auth.md) for extraction instructions.

**Warning**: Cookie mode is known to cause logout issues on Slack Enterprise workspaces and may trigger security warnings about your account.

### Scopes

Operations requiring unavailable scopes will fail with a clear error message and re-authentication instructions.

### Certificate

OAuth requires HTTPS. clacks includes a bundled self-signed certificate, so no setup is required.

To generate your own certificate:
```bash
uvx --from slack-clacks clacks auth cert generate
```

### Account Management

View current authentication status:
```bash
uvx --from slack-clacks clacks auth status
```

Revoke authentication:
```bash
uvx --from slack-clacks clacks auth logout
```

## Configuration

Multiple authentication contexts supported. Initialize configuration:
```bash
uvx --from slack-clacks clacks config init
```

List available contexts:
```bash
uvx --from slack-clacks clacks config contexts
```

Switch between contexts:
```bash
uvx --from slack-clacks clacks config switch -C <context-name>
```

View current configuration:
```bash
uvx --from slack-clacks clacks config info
```

## Messaging

### Send

Send to channel:
```bash
uvx --from slack-clacks clacks send -c "#general" -m "message text"
uvx --from slack-clacks clacks send -c "C123456" -m "message text"
```

Send direct message:
```bash
uvx --from slack-clacks clacks send -u "@username" -m "message text"
uvx --from slack-clacks clacks send -u "U123456" -m "message text"
```

Reply to thread:
```bash
uvx --from slack-clacks clacks send -c "#general" -m "reply text" -t "1234567890.123456"
```

### Read

Read messages from channel:
```bash
uvx --from slack-clacks clacks read -c "#general"
uvx --from slack-clacks clacks read -c "#general" -l 50
```

Read direct messages:
```bash
uvx --from slack-clacks clacks read -u "@username"
```

Read thread:
```bash
uvx --from slack-clacks clacks read -c "#general" -t "1234567890.123456"
```

Read specific message:
```bash
uvx --from slack-clacks clacks read -c "#general" -m "1234567890.123456"
```

### Recent

View recent messages across all conversations:
```bash
uvx --from slack-clacks clacks recent
uvx --from slack-clacks clacks recent -l 50
```

## Rolodex

Manage aliases for users and channels. Aliases resolve to platform-specific IDs (e.g., Slack user IDs).

Sync from Slack API:
```bash
uvx --from slack-clacks clacks rolodex sync
```

Add alias manually:
```bash
uvx --from slack-clacks clacks rolodex add <alias> -t <target-id> -T <target-type>
uvx --from slack-clacks clacks rolodex add kartik -t U03QPJ2KMJ6 -T user
uvx --from slack-clacks clacks rolodex add dev-channel -t C08740LGAE6 -T channel
```

List aliases:
```bash
uvx --from slack-clacks clacks rolodex list
uvx --from slack-clacks clacks rolodex list -T user
uvx --from slack-clacks clacks rolodex list -p slack
```

Remove alias:
```bash
uvx --from slack-clacks clacks rolodex remove <alias> -T <target-type>
```

Show valid target types for a platform:
```bash
uvx --from slack-clacks clacks rolodex platforminfo -p slack
uvx --from slack-clacks clacks rolodex platforminfo -p github
```

## Agent Skills

clacks supports the [Agent Skills](https://agentskills.io) open standard for AI coding assistants.

Print SKILL.md to stdout:
```bash
uvx --from slack-clacks clacks skill
```

Install for Claude Code (global):
```bash
uvx --from slack-clacks clacks skill --mode claude
```

Install for OpenAI Codex (global):
```bash
uvx --from slack-clacks clacks skill --mode codex
```

Install for Cursor/Windsurf/Aider (global):
```bash
uvx --from slack-clacks clacks skill --mode universal
```

Install for VS Code Copilot (project):
```bash
uvx --from slack-clacks clacks skill --mode github
```

All modes support `-global` and `-project` suffixes (e.g., `claude-project`, `codex-global`).

## Output

All commands output JSON to stdout. Redirect to file:
```bash
uvx --from slack-clacks clacks auth status -o output.json
```

## Requirements

- Python >= 3.13
- Slack workspace admin approval for OAuth app installation
