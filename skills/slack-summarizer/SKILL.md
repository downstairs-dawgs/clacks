---
name: slack-summarizer
description: >-
  Summarize Slack messages and reply in thread using clacks.
---

# Slack Message Summarizer

Receive a Slack message JSON from `clacks listen`, summarize it, and reply back to the thread.

## Task

1. Parse the input JSON to extract `text`, `channel`, and `ts`
2. Summarize the message in 1-2 sentences
3. Reply to the thread using Bash tool:

```bash
clacks send -c "<channel>" -t "<ts>" -m "📊 [Your summary]"
```

## Example

Input:
```json
{"text": "Can someone help debug API 500 errors on /users?", "channel": "C123", "ts": "1234567890.123456"}
```

Action:
```bash
clacks send -c "C123" -t "1234567890.123456" -m "📊 Request for help debugging 500 errors on /users endpoint"
```

Keep it concise. Preserve technical details. Flag urgency if present.
