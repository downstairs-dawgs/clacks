# Rolodex Implementation

## Overview

Local alias database for resolving human-friendly names to platform-specific IDs. Supports multiple platforms (Slack, GitHub) with platform-specific target types.

## Database Schema

Single table: `aliases`

| Column | Type | Notes |
|--------|------|-------|
| alias | String | Primary key (composite) |
| context | String | Primary key (composite) - auth context name |
| target_type | String | Primary key (composite) - e.g., user, channel |
| platform | String | Platform name (slack, github) |
| target_id | String | Platform-specific ID (e.g., U0876FVQ58C) |

Unique constraint: (alias, context, target_type)

## Platforms and Target Types

Defined in `rolodex/data.py`:

- **slack**: user, channel
- **github**: user, repo, org

## CLI Commands

```bash
clacks rolodex add <alias> -t <target-id> -T <target-type> [-p <platform>]
clacks rolodex list [-p <platform>] [-T <target-type>] [-t <target-id>]
clacks rolodex remove <alias> -T <target-type>
clacks rolodex sync
clacks rolodex platforminfo -p <platform>
```

## Resolution Flow

`resolve_user_id` and `resolve_channel_id` in `messaging/operations.py`:

1. Check if already a Slack ID (U..., C..., D..., G...)
2. Check rolodex aliases (filtered by platform)
3. Fall back to Slack API

## File Structure

```
src/slack_clacks/rolodex/
  __init__.py
  data.py        # Platform and target type constants
  models.py      # SQLAlchemy Alias model
  operations.py  # Database operations
  cli.py         # CLI commands
```

## Related Issues

- #38 - clacks rolodex (design doc)
- #50 - Add user and channel lookup commands
- #18 - Cache channel and user metadata in database
