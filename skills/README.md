# Clacks Skills

Example skills for use with the `clacks listen --claude-exec-skill` feature.

## Available Skills

### slack-summarizer

Automatically summarize incoming Slack messages with key points, message type classification, and notable elements detection.

**Features:**
- Concise 1-2 sentence summaries
- Extracts key points and action items
- Identifies message type (Question, Action, Information, Urgent)
- Detects links, code blocks, and urgency indicators

**Use case:** Monitor support channels, incident reports, or team discussions and get instant summaries.

[View Documentation](./slack-summarizer/README.md)

## Installation

### Global Installation (Recommended)

Install to your Claude Code global skills directory:

```bash
# Install a specific skill
cp -r skills/slack-summarizer ~/.claude/skills/

# Or install all skills
cp -r skills/* ~/.claude/skills/
```

### Project Installation

Install to your project's local skills directory:

```bash
# Create project skills directory if it doesn't exist
mkdir -p .claude/skills/

# Install a specific skill
cp -r skills/slack-summarizer .claude/skills/
```

## Usage with clacks listen

Once installed, use the skill with `clacks listen`:

```bash
# Using global installation (full path to SKILL.md)
clacks listen "#general" \
    --claude-exec-skill ~/.claude/skills/slack-summarizer/SKILL.md \
    --continuous

# Using project installation
clacks listen "#general" \
    --claude-exec-skill .claude/skills/slack-summarizer/SKILL.md \
    --continuous

# With additional options
clacks listen "#support" \
    --from "@customer" \
    --claude-exec-skill ~/.claude/skills/slack-summarizer/SKILL.md \
    --claude-timeout 30 \
    --continuous
```

## Testing Skills

Each skill includes a test script. To test a skill manually:

```bash
# Change to skill directory
cd skills/slack-summarizer

# Run test examples
./test-examples.sh

# Or test with a specific message
claude -p --system-prompt "$(cat SKILL.md)" '{
  "text": "Your test message here",
  "user": "U123456",
  "ts": "1234567890.123456"
}'
```

## Creating Your Own Skills

1. Create a new directory in `skills/`
2. Add a `SKILL.md` file with the skill definition (see existing skills for format)
3. Add a `README.md` with documentation
4. Optionally add test scripts

### Skill Format

Skills are markdown files that Claude Code reads as system prompts. They should include:

```markdown
---
name: your-skill-name
description: >-
  Brief description of what the skill does
---

# Skill Title

## Input Format

Describe expected input (usually JSON from clacks listen)

## Task

Detailed instructions for Claude on how to process the input

## Output Format

Specify the expected output format

## Guidelines

Any additional guidelines or constraints
```

## Requirements

- clacks 0.6.0+ with `--claude-exec-skill` support
- Claude Code CLI installed
- Authenticated Slack workspace via `clacks auth login`

## Examples

### Support Channel Monitoring

```bash
# Monitor support channel and summarize customer questions
clacks listen "#customer-support" \
    --claude-exec-skill ~/.claude/skills/slack-summarizer/SKILL.md \
    --continuous \
    --claude-timeout 30
```

### Incident Response

```bash
# Monitor incidents channel for urgent issues
clacks listen "#incidents" \
    --claude-exec-skill ~/.claude/skills/slack-summarizer/SKILL.md \
    --include-bots \
    --continuous
```

### PR Review Requests

```bash
# Monitor dev channel for PR review requests
clacks listen "#dev" \
    --claude-exec-skill ~/.claude/skills/slack-summarizer/SKILL.md \
    --continuous
```

## Contributing

Have a useful skill? Submit a PR to add it to this collection!

1. Create your skill in a new directory under `skills/`
2. Include `SKILL.md`, `README.md`, and optionally test scripts
3. Update this README with your skill
4. Submit a PR

## License

MIT - See LICENSE file in the root of the repository.
