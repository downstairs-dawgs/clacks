# Rolodex Implementation Checklist

## Phase 1: Database Foundation

- [ ] Create `src/slack_clacks/rolodex/` directory
- [ ] Create `src/slack_clacks/rolodex/__init__.py`
- [ ] Create `src/slack_clacks/rolodex/models.py` with RolodexUser and RolodexChannel models
- [ ] Create Alembic migration for rolodex tables
- [ ] Run migration and verify tables created
- [ ] Add tests for models

## Phase 2: Database Operations

- [ ] Create `src/slack_clacks/rolodex/operations.py`
- [ ] Implement `add_user()` - add/update user in rolodex
- [ ] Implement `add_channel()` - add/update channel in rolodex
- [ ] Implement `get_user()` - lookup by user_id, username, or email
- [ ] Implement `get_channel()` - lookup by channel_id or channel_name
- [ ] Implement `list_users()` - list all users for workspace
- [ ] Implement `list_channels()` - list all channels for workspace
- [ ] Implement `search_users()` - search by username/real_name/email
- [ ] Implement `search_channels()` - search by channel_name
- [ ] Implement `remove_user()` - delete user from rolodex
- [ ] Implement `remove_channel()` - delete channel from rolodex
- [ ] Implement `clear_rolodex()` - clear all entries for workspace
- [ ] Implement `sync_users()` - fetch all users from Slack API and cache
- [ ] Implement `sync_channels()` - fetch all channels from Slack API and cache
- [ ] Add tests for operations

## Phase 3: CLI Commands

- [ ] Create `src/slack_clacks/rolodex/cli.py`
- [ ] Implement `clacks rolodex add user` command
- [ ] Implement `clacks rolodex add channel` command
- [ ] Implement `clacks rolodex list users` command
- [ ] Implement `clacks rolodex list channels` command
- [ ] Implement `clacks rolodex search users` command
- [ ] Implement `clacks rolodex search channels` command
- [ ] Implement `clacks rolodex sync` command (users/channels/all)
- [ ] Implement `clacks rolodex remove user` command
- [ ] Implement `clacks rolodex remove channel` command
- [ ] Implement `clacks rolodex clear` command
- [ ] Register rolodex subparser in main `cli.py`
- [ ] Test all CLI commands manually

## Phase 4: Integration with Existing Resolution

- [ ] Update `resolve_user_id()` to check rolodex first
- [ ] Update `resolve_user_id()` to cache successful API resolutions
- [ ] Update `resolve_channel_id()` to check rolodex first
- [ ] Update `resolve_channel_id()` to cache successful API resolutions
- [ ] Add tests for cache-first resolution behavior

## Phase 5: Finalization

- [ ] Bump version to 0.4.0
- [ ] Run all checks (ruff, mypy, tests)
- [ ] Update this checklist - mark all items complete
- [ ] Create PR closing #38, #50
