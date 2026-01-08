# clacks
the default mode of degenerate communication.

## Installation

Choose your preferred method:

**With uv** (no installation required):
```bash
uvx --from slack-clacks clacks
```

**With uv** (permanent installation):
```bash
uv tool install slack-clacks
```

**With pip/pipx/poetry**:
```bash
pip install slack-clacks
# or: pipx install slack-clacks
```

Examples below use `clacks` directly. If using `uvx`, prefix commands with `uvx --from slack-clacks`.

## Updating

**With uvx**: Updates happen automatically (always runs latest version).

**With uv tool**:
```bash
uv tool upgrade slack-clacks
```

**With pip**:
```bash
pip install --upgrade slack-clacks
```

## Authentication

Authenticate via OAuth:
```bash
clacks auth login -c <context-name>
```

### Modes

clacks supports three authentication modes:

#### clacks mode (default)

Full workspace access via OAuth.

```bash
clacks auth login --mode clacks
```

Permissions: channels, groups, DMs, MPIMs, files, search

#### clacks-lite mode

Secure, DM-focused access via OAuth. Use for security-conscious environments where channel access isn't needed.

```bash
clacks auth login --mode clacks-lite
```

Permissions: DMs, MPIMs, reactions only

#### cookie mode

Browser session authentication. Use for quick testing or when OAuth is impractical.

```bash
clacks auth login --mode cookie
```

Extract xoxc token and d cookie from browser. No OAuth app needed. See [docs/cookie-auth.md](docs/cookie-auth.md) for extraction instructions.

**Warning**: Cookie mode is known to cause logout issues on Slack Enterprise workspaces and may trigger security warnings about your account.

### Scopes

Operations requiring unavailable scopes will fail with a clear error message and re-authentication instructions.

### Certificate

OAuth requires HTTPS. clacks includes a bundled self-signed certificate, so no setup is required.

To generate your own certificate:
```bash
clacks auth cert generate
```

### Account Management

View current authentication status:
```bash
clacks auth status
```

Revoke authentication:
```bash
clacks auth logout
```

## Configuration

Multiple authentication contexts supported. Initialize configuration:
```bash
clacks config init
```

List available contexts:
```bash
clacks config contexts
```

Switch between contexts:
```bash
clacks config switch -C <context-name>
```

View current configuration:
```bash
clacks config info
```

## Messaging

### Send

Send to channel:
```bash
clacks send -c "#general" -m "message text"
clacks send -c "C123456" -m "message text"
```

Send direct message:
```bash
clacks send -u "@username" -m "message text"
clacks send -u "U123456" -m "message text"
```

Reply to thread:
```bash
clacks send -c "#general" -m "reply text" -t "1234567890.123456"
```

### Read

Read messages from channel:
```bash
clacks read -c "#general"
clacks read -c "#general" -l 50
```

Read direct messages:
```bash
clacks read -u "@username"
```

Read thread:
```bash
clacks read -c "#general" -t "1234567890.123456"
```

Read specific message:
```bash
clacks read -c "#general" -m "1234567890.123456"
```

### Recent

View recent messages across all conversations:
```bash
clacks recent
clacks recent -l 50
```

## Rolodex

Manage aliases for users and channels. Aliases resolve to platform-specific IDs (e.g., Slack user IDs).

Sync from Slack API:
```bash
clacks rolodex sync
```

Add alias manually:
```bash
clacks rolodex add <alias> -t <target-id> -T <target-type>
clacks rolodex add kartik -t U03QPJ2KMJ6 -T user
clacks rolodex add dev-channel -t C08740LGAE6 -T channel
```

List aliases:
```bash
clacks rolodex list
clacks rolodex list -T user
clacks rolodex list -p slack
```

Remove alias:
```bash
clacks rolodex remove <alias> -T <target-type>
```

Show valid target types for a platform:
```bash
clacks rolodex platforminfo -p slack
clacks rolodex platforminfo -p github
```

## Agent Skills

clacks supports the [Agent Skills](https://agentskills.io) open standard for AI coding assistants.

Print SKILL.md to stdout:
```bash
clacks skill
```

Install for Claude Code (global):
```bash
clacks skill --mode claude
```

Install for OpenAI Codex (global):
```bash
clacks skill --mode codex
```

Install for Cursor/Windsurf/Aider (global):
```bash
clacks skill --mode universal
```

Install for VS Code Copilot (project):
```bash
clacks skill --mode github
```

All modes support `-global` and `-project` suffixes (e.g., `claude-project`, `codex-global`).

## Output

All commands output JSON to stdout. Redirect to file:
```bash
clacks auth status -o output.json
```

## Requirements

- Python >= 3.13
- Slack workspace admin approval for OAuth app installation
