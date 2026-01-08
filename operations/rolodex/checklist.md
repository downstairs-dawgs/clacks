# Rolodex Implementation Checklist

## Schema

Single table: `aliases`

```
aliases:
  alias        String      PK
  context      String      PK
  target_type  String      PK
  platform     String
  target_id    String
```

Unique per (alias, context, target_type).

## CLI Commands

- [x] `clacks rolodex add` - add an alias
- [x] `clacks rolodex list` - list aliases with filters (-p platform, -T target_type, -t target_id)
- [x] `clacks rolodex remove` - remove an alias
- [x] `clacks rolodex sync` - sync from Slack API
- [x] `clacks rolodex platforminfo` - show valid target types for a platform

## Operations

- [x] `add_alias()` - add or update an alias
- [x] `get_alias()` - lookup by (alias, context, target_type)
- [x] `list_aliases()` - list with filters
- [x] `remove_alias()` - delete an alias
- [x] `resolve_alias()` - resolve identifier in context
- [x] `sync_from_slack()` - sync users and channels from Slack API
- [x] `validate_platform_target_type()` - validate platform/target_type combinations
- [x] `get_platform_target_types()` - get valid target types for platform

## Resolution

- [x] `resolve_user_id()` checks aliases first, then falls back to Slack API
- [x] `resolve_channel_id()` checks aliases first, then falls back to Slack API

## Finalization

- [x] Run all checks (ruff, mypy, tests)
- [x] Commit and update PR
