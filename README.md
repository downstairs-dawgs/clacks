# clacks
Control Slack from your command line

## Installation

**Recommended** - run directly with uv (no installation needed):
```bash
uvx slack-clacks
```

**Install globally** with uv:
```bash
uv tool install slack-clacks
```

**Alternative** - works with pip, poetry, or any package manager:
```bash
pip install slack-clacks
```

## Authentication

Authenticate via OAuth:
```bash
clacks auth login -c <context-name>
```

### Authentication Modes

clacks supports two OAuth modes:

**clacks mode (default)**: Full workspace access
```bash
clacks auth login --mode clacks
```
Permissions: channels, groups, DMs, MPIMs, files, search

**clacks-lite mode**: Secure, DM-focused access
```bash
clacks auth login --mode clacks-lite
```
Permissions: DMs, MPIMs, reactions only

Use clacks-lite for security-conscious environments where channel access isn't needed. Operations requiring unavailable scopes (e.g., reading channels in lite mode) will fail with a clear error message and re-authentication instructions.

OAuth requires HTTPS. Generate a self-signed certificate:
```bash
clacks auth cert generate
```

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

## Output

All commands output JSON to stdout. Redirect to file:
```bash
clacks auth status -o output.json
```

## Requirements

- Python >= 3.13
- Slack workspace admin approval for OAuth app installation
