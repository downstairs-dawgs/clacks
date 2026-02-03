# Slack Message Summarizer Skill

A Claude Code skill that summarizes Slack messages received from `clacks listen`.

## Installation

### For Claude Code (Global)

```bash
# Install to global Claude Code skills directory
mkdir -p ~/.claude/skills/
cp -r slack-summarizer ~/.claude/skills/
```

### For Project Use

```bash
# Install to project .claude/skills directory
mkdir -p .claude/skills/
cp -r slack-summarizer .claude/skills/
```

## Usage

### With clacks listen

Process incoming Slack messages automatically:

```bash
# Summarize messages from a channel using the skill path
clacks listen "#general" \
    --claude-exec-skill ~/.claude/skills/slack-summarizer/SKILL.md \
    --continuous

# Or use the full path if installed locally
clacks listen "#general" \
    --claude-exec-skill /path/to/clacks/skills/slack-summarizer/SKILL.md \
    --continuous

# Summarize messages from a specific user in continuous mode
clacks listen "#support" \
    --from "@customer" \
    --claude-exec-skill ~/.claude/skills/slack-summarizer/SKILL.md \
    --continuous \
    --claude-timeout 30
```

### Manual Testing

Test the skill by passing JSON directly to Claude with the skill loaded:

```bash
# Using system prompt with the skill content
claude -p --system-prompt "$(cat ~/.claude/skills/slack-summarizer/SKILL.md)" \
  '{
  "text": "Hey team, our production server is down! Getting 503 errors on all endpoints. Need help ASAP!",
  "user": "U123456",
  "ts": "1234567890.123456",
  "channel": "C789012",
  "received_at": "2024-01-01T12:00:00Z"
}'
```

Alternatively, when using clacks listen with `--claude-exec-skill`, the skill is automatically loaded.

## Example Output

**Input message:**
```json
{
  "text": "Can someone review the PR #123? It adds authentication middleware and fixes the CORS issue. Tests are passing: https://github.com/company/repo/pull/123",
  "user": "U123456",
  "ts": "1234567890.123456"
}
```

**Claude's summary:**
```
SUMMARY: Request for PR review on authentication middleware that also resolves CORS issue, with passing tests.

KEY POINTS:
- Pull Request #123 needs review
- Adds authentication middleware
- Fixes CORS issue
- Tests passing

TYPE: Action (Review Requested)

NOTABLE ELEMENTS:
- GitHub PR link provided
```

## Use Cases

- **Support Channels**: Automatically summarize customer questions
- **Incident Channels**: Quick summaries of incident reports
- **Code Review Requests**: Extract PR details and action items
- **Team Updates**: Condense long messages into key points
- **Monitoring Alerts**: Identify urgent issues from alert messages

## Customization

Edit `SKILL.md` to customize:
- Summary length and format
- What to highlight (questions, actions, urgency)
- Output structure
- Special element detection (links, code, etc.)

## Tips

- Use `--claude-timeout 30` to prevent long processing times
- Combine with `--from` to filter specific users
- Use `--continuous` to process messages indefinitely
- Save output to file with `-o summaries.jsonl`

## Requirements

- Claude Code CLI installed
- clacks 0.6.0+ with `--claude-exec-skill` support
- Authenticated Slack workspace via `clacks auth login`
