#!/bin/bash
# Test examples for slack-summarizer skill

SKILL_FILE="$(dirname "$0")/SKILL.md"

echo "Testing Slack Summarizer Skill"
echo "==============================="
echo
echo "Note: Using -p (print mode) with --system-prompt to load the skill"
echo

echo "Test 1: Simple question"
echo "-----------------------"
claude -p --system-prompt "$(cat "$SKILL_FILE")" '{
  "text": "Hey team, where did we put the API documentation?",
  "user": "U123456",
  "ts": "1234567890.123456",
  "channel": "C789012",
  "received_at": "2024-01-01T12:00:00Z"
}'
echo
echo

echo "Test 2: Urgent incident report"
echo "-------------------------------"
claude -p --system-prompt "$(cat "$SKILL_FILE")" '{
  "text": "URGENT: Production database is throwing connection errors. Users cannot log in. Error: Connection timeout after 30s. Need immediate help!",
  "user": "U234567",
  "ts": "1234567891.123456",
  "channel": "C789012",
  "received_at": "2024-01-01T12:05:00Z"
}'
echo
echo

echo "Test 3: PR review request with link"
echo "------------------------------------"
claude -p --system-prompt "$(cat "$SKILL_FILE")" '{
  "text": "Can someone review PR #456? It adds rate limiting to the API endpoints and includes comprehensive tests. Link: https://github.com/company/repo/pull/456",
  "user": "U345678",
  "ts": "1234567892.123456",
  "channel": "C789012",
  "received_at": "2024-01-01T12:10:00Z"
}'
echo
echo

echo "Test 4: Technical issue with code"
echo "----------------------------------"
claude -p --system-prompt "$(cat "$SKILL_FILE")" '{
  "text": "Getting a weird bug in the authentication flow. When users try to log in, the JWT token expires immediately. Here is the relevant code:\n\n```python\ntoken = jwt.encode({\"user_id\": user.id, \"exp\": datetime.now()}, SECRET_KEY)\n```\n\nAny ideas what could be wrong?",
  "user": "U456789",
  "ts": "1234567893.123456",
  "channel": "C789012",
  "received_at": "2024-01-01T12:15:00Z"
}'
echo
echo

echo "Test 5: Short informational message"
echo "------------------------------------"
claude -p --system-prompt "$(cat "$SKILL_FILE")" '{
  "text": "Deployment complete ✅",
  "user": "U567890",
  "ts": "1234567894.123456",
  "channel": "C789012",
  "received_at": "2024-01-01T12:20:00Z"
}'
echo
