"""Tests for ``read``'s ``--cursor`` pagination passthrough.

``-l/--limit`` caps a single Slack API request; ``--cursor`` fetches the next
page using a prior response's ``response_metadata.next_cursor``. Cursors are
never followed automatically. The same opaque cursor works for both channel
reads (``conversations.history``) and thread reads (``conversations.replies``).
"""

import argparse
import unittest
from unittest.mock import MagicMock

from slack_clacks.messaging.cli import generate_read_parser, handle_read
from slack_clacks.messaging.operations import read_messages, read_thread


class TestReadParserCursor(unittest.TestCase):
    def setUp(self):
        self.parser = generate_read_parser()

    def test_cursor_defaults_to_none(self):
        args = self.parser.parse_args(["-c", "#general"])
        self.assertIsNone(args.cursor)

    def test_cursor_parsed(self):
        args = self.parser.parse_args(["-c", "#general", "--cursor", "abc123"])
        self.assertEqual(args.cursor, "abc123")


class TestOperationsCursorPassthrough(unittest.TestCase):
    def test_read_messages_forwards_cursor(self):
        client = MagicMock()
        read_messages(client, "C123", limit=50, cursor="CUR")
        client.conversations_history.assert_called_once_with(
            channel="C123",
            limit=50,
            latest=None,
            oldest=None,
            inclusive=True,
            cursor="CUR",
        )

    def test_read_messages_defaults_cursor_none(self):
        client = MagicMock()
        read_messages(client, "C123")
        self.assertIsNone(client.conversations_history.call_args.kwargs["cursor"])

    def test_read_thread_forwards_cursor(self):
        client = MagicMock()
        read_thread(client, "C123", "111.222", limit=50, cursor="CUR")
        client.conversations_replies.assert_called_once_with(
            channel="C123",
            ts="111.222",
            limit=50,
            oldest=None,
            latest=None,
            inclusive=True,
            cursor="CUR",
        )

    def test_read_thread_defaults_cursor_none(self):
        client = MagicMock()
        read_thread(client, "C123", "111.222")
        self.assertIsNone(client.conversations_replies.call_args.kwargs["cursor"])


class TestHandleReadCursorGuard(unittest.TestCase):
    def test_cursor_with_message_raises(self):
        # The guard fires before any DB/network access, so no mocking needed.
        args = argparse.Namespace(
            config_dir=None,
            cursor="CUR",
            message="111.222",
        )
        with self.assertRaises(ValueError):
            handle_read(args)


if __name__ == "__main__":
    unittest.main()
