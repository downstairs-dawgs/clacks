import os
import time
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from slack_clacks.listen.operations import listen_channel


def make_ts(offset: float = 0) -> str:
    """Create a timestamp relative to now."""
    return str(time.time() + offset)


class TestListenChannel(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()

    def test_no_history_polls_for_new_messages(self):
        """When include_history=0, should immediately poll for new messages."""
        # Use a future timestamp so it passes the filter
        future_ts = make_ts(100)
        # Return a message on first poll, then empty for subsequent polls
        self.client.conversations_history.side_effect = [
            {"messages": [{"ts": future_ts, "text": "hello"}]},
        ] + [{"messages": []}] * 10

        gen = listen_channel(
            self.client,
            channel_id="C123",
            interval=0.01,
            timeout=0.05,
            include_history=0,
        )

        messages = list(gen)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["text"], "hello")
        self.assertIn("received_at", messages[0])

    def test_include_history_fetches_initial_messages(self):
        """When include_history > 0, should fetch and yield history first."""
        ts1 = make_ts(1)
        ts2 = make_ts(2)
        self.client.conversations_history.side_effect = [
            # History fetch - reverse chronological order
            {
                "messages": [
                    {"ts": ts2, "text": "second"},
                    {"ts": ts1, "text": "first"},
                ]
            },
        ] + [{"messages": []}] * 10

        gen = listen_channel(
            self.client,
            channel_id="C123",
            interval=0.01,
            timeout=0.02,
            include_history=5,
        )

        messages = list(gen)
        # History should be reversed to chronological order
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["text"], "first")
        self.assertEqual(messages[1]["text"], "second")

    def test_thread_mode_uses_conversations_replies(self):
        """When thread_ts is provided, should use conversations_replies."""
        parent_ts = make_ts(0)
        reply_ts = make_ts(1)
        # Thread replies - first message is parent
        self.client.conversations_replies.side_effect = [
            {
                "messages": [
                    {"ts": parent_ts, "text": "parent"},
                    {"ts": reply_ts, "text": "reply1"},
                ]
            },
        ] + [
            {
                "messages": [
                    {"ts": parent_ts, "text": "parent"},
                    {"ts": reply_ts, "text": "reply1"},
                ]
            }
        ] * 10

        gen = listen_channel(
            self.client,
            channel_id="C123",
            thread_ts=parent_ts,
            interval=0.01,
            timeout=0.02,
            include_history=5,
        )

        messages = list(gen)
        # Should only get reply, not parent
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["text"], "reply1")

    def test_timeout_exits_after_duration(self):
        """Should exit after timeout seconds."""
        self.client.conversations_history.return_value = {"messages": []}

        gen = listen_channel(
            self.client,
            channel_id="C123",
            interval=0.01,
            timeout=0.05,
            include_history=0,
        )

        # Should complete without hanging
        messages = list(gen)
        self.assertEqual(len(messages), 0)

    def test_received_at_is_iso_format(self):
        """The received_at timestamp should be ISO format."""
        ts = make_ts(1)
        self.client.conversations_history.side_effect = [
            {"messages": [{"ts": ts, "text": "hello"}]},
        ] + [{"messages": []}] * 10

        gen = listen_channel(
            self.client,
            channel_id="C123",
            interval=0.01,
            timeout=0.02,
            include_history=1,
        )

        messages = list(gen)
        self.assertEqual(len(messages), 1)
        # Should be parseable as ISO format
        received_at = messages[0]["received_at"]
        datetime.fromisoformat(received_at)

    def test_deduplication_of_messages(self):
        """Should not yield the same message twice."""
        ts = make_ts(1)
        # First history fetch, then poll returns same message
        self.client.conversations_history.side_effect = [
            {"messages": [{"ts": ts, "text": "first"}]},
            # Second poll returns same message (simulating overlap)
            {"messages": [{"ts": ts, "text": "first"}]},
        ] + [{"messages": []}] * 10

        gen = listen_channel(
            self.client,
            channel_id="C123",
            interval=0.01,
            timeout=0.03,
            include_history=1,
        )

        messages = list(gen)
        # Should only get one message despite it appearing twice
        self.assertEqual(len(messages), 1)


class TestListenChannelEdgeCases(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()

    def test_empty_thread_history(self):
        """Thread with only parent message should yield nothing for history."""
        parent_ts = make_ts(0)
        self.client.conversations_replies.side_effect = [
            # Only parent message
            {"messages": [{"ts": parent_ts, "text": "parent"}]},
        ] + [{"messages": [{"ts": parent_ts, "text": "parent"}]}] * 10

        gen = listen_channel(
            self.client,
            channel_id="C123",
            thread_ts=parent_ts,
            interval=0.01,
            timeout=0.02,
            include_history=5,
        )

        messages = list(gen)
        self.assertEqual(len(messages), 0)

    def test_new_thread_reply_detected(self):
        """Should detect new replies in a thread."""
        parent_ts = make_ts(0)
        reply_ts = make_ts(100)  # Future timestamp

        self.client.conversations_replies.side_effect = [
            # Initial history
            {"messages": [{"ts": parent_ts, "text": "parent"}]},
            # First poll - new reply
            {
                "messages": [
                    {"ts": parent_ts, "text": "parent"},
                    {"ts": reply_ts, "text": "new reply"},
                ]
            },
        ] + [
            {
                "messages": [
                    {"ts": parent_ts, "text": "parent"},
                    {"ts": reply_ts, "text": "new reply"},
                ]
            }
        ] * 10

        gen = listen_channel(
            self.client,
            channel_id="C123",
            thread_ts=parent_ts,
            interval=0.01,
            timeout=0.03,
            include_history=5,
        )

        messages = list(gen)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["text"], "new reply")


class TestContinuousMode(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()

    def test_default_exits_after_first_message(self):
        """Without continuous=True, should exit after first message."""
        ts1 = make_ts(100)
        ts2 = make_ts(200)
        self.client.conversations_history.side_effect = [
            {"messages": [{"ts": ts1, "text": "first"}]},
            {"messages": [{"ts": ts2, "text": "second"}]},
        ] + [{"messages": []}] * 10

        gen = listen_channel(
            self.client,
            channel_id="C123",
            interval=0.01,
            timeout=0.1,
            include_history=0,
            continuous=False,
        )

        messages = list(gen)
        # Should only get first message then exit
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["text"], "first")

    def test_continuous_keeps_running(self):
        """With continuous=True, should keep receiving messages."""
        ts1 = make_ts(100)
        ts2 = make_ts(200)
        self.client.conversations_history.side_effect = [
            {"messages": [{"ts": ts1, "text": "first"}]},
            {"messages": [{"ts": ts2, "text": "second"}]},
        ] + [{"messages": []}] * 10

        gen = listen_channel(
            self.client,
            channel_id="C123",
            interval=0.01,
            timeout=0.05,
            include_history=0,
            continuous=True,
        )

        messages = list(gen)
        # Should get both messages
        self.assertEqual(len(messages), 2)


class TestRateLimitHandling(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()

    def test_retries_on_rate_limit(self):
        """Should retry with backoff when rate limited."""
        from slack_sdk.errors import SlackApiError

        from slack_clacks.listen.operations import _call_with_backoff

        mock_response = MagicMock()
        mock_response.get.return_value = "ratelimited"
        mock_response.headers = {"Retry-After": "0"}

        call_count = 0

        def mock_func(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise SlackApiError("rate limited", mock_response)
            return {"messages": []}

        result = _call_with_backoff(mock_func, max_retries=5, base_delay=0.01)
        self.assertEqual(call_count, 3)
        self.assertEqual(result, {"messages": []})

    def test_raises_after_max_retries(self):
        """Should raise after max retries exhausted."""
        from slack_sdk.errors import SlackApiError

        from slack_clacks.listen.operations import _call_with_backoff

        mock_response = MagicMock()
        mock_response.get.return_value = "ratelimited"
        mock_response.headers = {"Retry-After": "0"}

        def mock_func(**kwargs):
            raise SlackApiError("rate limited", mock_response)

        with self.assertRaises(SlackApiError):
            _call_with_backoff(mock_func, max_retries=2, base_delay=0.01)


class TestLoadSkillContent(unittest.TestCase):
    def test_load_skill_content_from_file_path(self):
        """Should load content from an existing file path."""
        import tempfile

        from slack_clacks.listen.operations import load_skill_content

        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
            f.write("# Test Skill\nDo the thing.")
            f.flush()
            try:
                content = load_skill_content(f.name)
                self.assertEqual(content, "# Test Skill\nDo the thing.")
            finally:
                os.unlink(f.name)

    def test_load_skill_content_nonexistent_raises(self):
        """Should raise FileNotFoundError for a nonexistent skill name."""
        from slack_clacks.listen.operations import load_skill_content

        with self.assertRaises(FileNotFoundError) as ctx:
            load_skill_content("nonexistent-skill-abc123")

        self.assertIn("Skill not found", str(ctx.exception))

    def test_load_skill_content_home_dir(self):
        """Should find skill in ~/.claude/skills/<name>/SKILL.md."""
        from slack_clacks.listen.operations import load_skill_content

        home = os.path.expanduser("~")
        skill_dir = os.path.join(home, ".claude", "skills", "_test_clacks_skill")
        os.makedirs(skill_dir, exist_ok=True)
        skill_path = os.path.join(skill_dir, "SKILL.md")
        try:
            with open(skill_path, "w") as f:
                f.write("home skill content")
            content = load_skill_content("_test_clacks_skill")
            self.assertEqual(content, "home skill content")
        finally:
            os.unlink(skill_path)
            os.rmdir(skill_dir)


class TestSpawnClaudeWithSkill(unittest.TestCase):
    @patch("slack_clacks.listen.operations.subprocess.run")
    @patch("slack_clacks.listen.operations.shutil.which")
    def test_spawn_claude_with_skill_file(self, mock_which, mock_run):
        """Should construct correct command with -p and --system-prompt."""
        import tempfile

        from slack_clacks.listen.operations import spawn_claude_with_skill

        mock_which.return_value = "/usr/bin/claude"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
            f.write("# My Skill\nProcess messages.")
            f.flush()
            try:
                msg = {"text": "hello", "ts": "123.456"}
                exit_code = spawn_claude_with_skill(msg, f.name)

                self.assertEqual(exit_code, 0)
                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                self.assertEqual(args[0], "claude")
                self.assertEqual(args[1], "-p")
                self.assertEqual(args[2], "--allowedTools")
                self.assertEqual(args[3], "Bash(clacks:*)")
                self.assertEqual(args[4], "--system-prompt")
                self.assertEqual(args[5], "# My Skill\nProcess messages.")
                self.assertIn('"text": "hello"', args[6])
            finally:
                os.unlink(f.name)

    @patch("slack_clacks.listen.operations.subprocess.run")
    @patch("slack_clacks.listen.operations.shutil.which")
    @patch("slack_clacks.listen.operations.load_skill_content")
    def test_spawn_claude_with_skill_name(self, mock_load, mock_which, mock_run):
        """Should construct correct command for named skill."""
        from slack_clacks.listen.operations import spawn_claude_with_skill

        mock_which.return_value = "/usr/bin/claude"
        mock_load.return_value = "skill content from name"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        msg = {"text": "hello", "ts": "123.456"}
        exit_code = spawn_claude_with_skill(msg, "my-skill")

        self.assertEqual(exit_code, 0)
        mock_load.assert_called_once_with("my-skill", cwd=None)
        args = mock_run.call_args[0][0]
        self.assertEqual(args[1], "-p")
        self.assertEqual(args[4], "--system-prompt")
        self.assertEqual(args[5], "skill content from name")

    @patch("slack_clacks.listen.operations.shutil.which")
    def test_spawn_claude_command_not_found(self, mock_which):
        """Should raise FileNotFoundError if claude not in PATH."""
        from slack_clacks.listen.operations import spawn_claude_with_skill

        mock_which.return_value = None

        msg = {"text": "hello"}
        with self.assertRaises(FileNotFoundError) as ctx:
            spawn_claude_with_skill(msg, "clacks")

        self.assertIn("claude command not found", str(ctx.exception))

    @patch("slack_clacks.listen.operations.subprocess.run")
    @patch("slack_clacks.listen.operations.shutil.which")
    @patch("slack_clacks.listen.operations.load_skill_content")
    def test_spawn_claude_timeout(self, mock_load, mock_which, mock_run):
        """Should handle timeout gracefully."""
        import subprocess

        from slack_clacks.listen.operations import spawn_claude_with_skill

        mock_which.return_value = "/usr/bin/claude"
        mock_load.return_value = "skill content"
        mock_run.side_effect = subprocess.TimeoutExpired("claude", 5)

        msg = {"text": "hello"}
        exit_code = spawn_claude_with_skill(msg, "my-skill", timeout=5.0)

        self.assertEqual(exit_code, -1)

    @patch("slack_clacks.listen.operations.subprocess.run")
    @patch("slack_clacks.listen.operations.shutil.which")
    @patch("slack_clacks.listen.operations.load_skill_content")
    def test_spawn_claude_with_cwd(self, mock_load, mock_which, mock_run):
        """Should use specified working directory."""
        from slack_clacks.listen.operations import spawn_claude_with_skill

        mock_which.return_value = "/usr/bin/claude"
        mock_load.return_value = "skill content"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        msg = {"text": "hello"}
        spawn_claude_with_skill(msg, "my-skill", cwd="/tmp")

        self.assertEqual(mock_run.call_args.kwargs["cwd"], "/tmp")

    @patch("slack_clacks.listen.operations.subprocess.run")
    @patch("slack_clacks.listen.operations.shutil.which")
    @patch("slack_clacks.listen.operations.load_skill_content")
    def test_spawn_claude_json_serialization(self, mock_load, mock_which, mock_run):
        """Should serialize complex message objects correctly."""
        from slack_clacks.listen.operations import spawn_claude_with_skill

        mock_which.return_value = "/usr/bin/claude"
        mock_load.return_value = "skill content"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        msg = {
            "text": "hello world",
            "ts": "1234567890.123456",
            "user": "U123456",
            "channel": "C123456",
            "received_at": "2024-01-01T12:00:00Z",
        }
        spawn_claude_with_skill(msg, "my-skill")

        # Message JSON is the last argument (index 6)
        args = mock_run.call_args[0][0]
        message_json = args[6]
        import json

        parsed = json.loads(message_json)
        self.assertEqual(parsed["text"], "hello world")
        self.assertEqual(parsed["user"], "U123456")

    @patch("slack_clacks.listen.operations.subprocess.run")
    @patch("slack_clacks.listen.operations.shutil.which")
    @patch("slack_clacks.listen.operations.load_skill_content")
    def test_spawn_claude_subprocess_params(self, mock_load, mock_which, mock_run):
        """Should call subprocess with correct parameters."""
        import subprocess

        from slack_clacks.listen.operations import spawn_claude_with_skill

        mock_which.return_value = "/usr/bin/claude"
        mock_load.return_value = "skill content"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        msg = {"text": "hello"}
        spawn_claude_with_skill(msg, "my-skill", timeout=30.0)

        # Verify subprocess.run was called with correct parameters
        self.assertEqual(mock_run.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(mock_run.call_args.kwargs["check"], False)
        self.assertEqual(mock_run.call_args.kwargs["timeout"], 30.0)
        self.assertEqual(mock_run.call_args.kwargs["stdout"], subprocess.PIPE)
        self.assertEqual(mock_run.call_args.kwargs["stderr"], subprocess.PIPE)


if __name__ == "__main__":
    unittest.main()
