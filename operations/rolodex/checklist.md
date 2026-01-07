# Rolodex Implementation Checklist

## Phase 1: Database Foundation

- [x] Create `src/slack_clacks/rolodex/` directory
- [x] Create `src/slack_clacks/rolodex/__init__.py`
- [x] Create `src/slack_clacks/rolodex/models.py` with RolodexUser and RolodexChannel models
- [x] Create Alembic migration for rolodex tables
- [x] Run migration and verify tables created
- [ ] Add tests for models

## Phase 2: Database Operations

- [x] Create `src/slack_clacks/rolodex/operations.py`
- [x] Implement `add_user()` - add/update user in rolodex
- [x] Implement `add_channel()` - add/update channel in rolodex
- [x] Implement `get_user()` - lookup by user_id, username, or email
- [x] Implement `get_channel()` - lookup by channel_id or channel_name
- [x] Implement `list_users()` - list all users for workspace
- [x] Implement `list_channels()` - list all channels for workspace
- [x] Implement `search_users()` - search by username/real_name/email
- [x] Implement `search_channels()` - search by channel_name
- [x] Implement `remove_user()` - delete user from rolodex
- [x] Implement `remove_channel()` - delete channel from rolodex
- [x] Implement `clear_rolodex()` - clear all entries for workspace
- [x] Implement `sync_users()` - fetch all users from Slack API and cache
- [x] Implement `sync_channels()` - fetch all channels from Slack API and cache
- [ ] Add tests for operations

## Phase 3: CLI Commands

- [x] Create `src/slack_clacks/rolodex/cli.py`
- [x] Implement `clacks rolodex add-user` command
- [x] Implement `clacks rolodex add-channel` command
- [x] Implement `clacks rolodex list-users` command
- [x] Implement `clacks rolodex list-channels` command
- [x] Implement `clacks rolodex search-users` command
- [x] Implement `clacks rolodex search-channels` command
- [x] Implement `clacks rolodex sync` command (users/channels/all)
- [x] Implement `clacks rolodex remove-user` command
- [x] Implement `clacks rolodex remove-channel` command
- [x] Implement `clacks rolodex clear` command
- [x] Register rolodex subparser in main `cli.py`
- [x] Test all CLI commands manually

## Phase 4: Integration with Existing Resolution

- [x] Update `resolve_user_id()` to check rolodex first
- [x] Update `resolve_user_id()` to cache successful API resolutions
- [x] Update `resolve_channel_id()` to check rolodex first
- [x] Update `resolve_channel_id()` to cache successful API resolutions
- [ ] Add tests for cache-first resolution behavior

## Phase 5: Finalization

- [x] Bump version to 0.4.0
- [x] Run all checks (ruff, mypy, tests)
- [x] Update this checklist - mark all items complete
- [ ] Create PR closing #38, #50
