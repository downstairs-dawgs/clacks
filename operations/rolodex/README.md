# Rolodex Implementation Plan

## Overview

Implement a local database cache (rolodex) for user and channel metadata, enabling fast offline-first resolution. This addresses issues #38, #50, #18, #26, #37.

## Database Schema

### Users table (`rolodex_users`)

| Column | Type | Notes |
|--------|------|-------|
| user_id | String | Primary key (e.g., U0876FVQ58C) |
| workspace_id | String | Foreign key to contexts.workspace_id, part of composite uniqueness |
| username | String | Indexed (e.g., "nkashy1") |
| real_name | String | Display name |
| email | String | Indexed |
| last_updated | DateTime | For staleness tracking |

Unique constraint: (user_id, workspace_id)

### Channels table (`rolodex_channels`)

| Column | Type | Notes |
|--------|------|-------|
| channel_id | String | Primary key (e.g., C08740LGAE6) |
| workspace_id | String | Foreign key to contexts.workspace_id, part of composite uniqueness |
| channel_name | String | Indexed (e.g., "general") |
| is_private | Boolean | Channel visibility |
| last_updated | DateTime | For staleness tracking |

Unique constraint: (channel_id, workspace_id)

## CLI Commands

All commands under `clacks rolodex`:

```bash
# Add entries manually
clacks rolodex add user <username> <user_id>
clacks rolodex add user --email <email> <user_id>
clacks rolodex add channel <channel_name> <channel_id>

# List entries
clacks rolodex list users
clacks rolodex list channels

# Search entries
clacks rolodex search users <query>
clacks rolodex search channels <query>

# Sync from Slack API (clacks mode - requires full scopes)
clacks rolodex sync users
clacks rolodex sync channels
clacks rolodex sync  # sync all

# Remove entries
clacks rolodex remove user <identifier>
clacks rolodex remove channel <identifier>

# Clear all cached data
clacks rolodex clear
```

## Resolution Flow Updates

Update `resolve_user_id` and `resolve_channel_id` in `messaging/operations.py`:

1. Check rolodex cache first (for current workspace)
2. On cache miss, attempt API call (existing behavior)
3. On successful API resolution, cache result in rolodex
4. Return resolution or error

## File Structure

```
src/slack_clacks/
  rolodex/
    __init__.py
    models.py      # SQLAlchemy models for rolodex tables
    operations.py  # Database operations (add, get, search, sync)
    cli.py         # CLI commands
  alembic/versions/
    xxxx_add_rolodex_tables.py  # Migration
```

## Implementation Checklist

See [checklist.md](./checklist.md) for detailed implementation steps.

## Version

This feature warrants a minor version bump: 0.3.3 -> 0.4.0

## Related Issues

- #38 - clacks rolodex (design doc)
- #50 - Add user and channel lookup commands
- #18 - Cache channel and user metadata in database
- #26 - User feedback: Difficulty finding channels/users
- #37 - User names are just text
