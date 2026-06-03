"""Tests for the ``--order {asc,desc}`` flag added to ``read``, ``recent``,
and ``search`` subcommands, plus the shared ``_sort_messages_by_ts`` helper.
"""

import unittest

from slack_clacks.messaging.cli import (
    _sort_messages_by_ts,
    generate_read_parser,
    generate_recent_parser,
    generate_search_parser,
)


class TestSortMessagesByTs(unittest.TestCase):
    def setUp(self):
        # Deliberately out of order.
        self.messages = [
            {"ts": "1767795445.000002", "text": "middle"},
            {"ts": "1767795445.000003", "text": "newest"},
            {"ts": "1767795445.000001", "text": "oldest"},
        ]

    def test_asc(self):
        ordered = _sort_messages_by_ts(self.messages, "asc")
        self.assertEqual([m["text"] for m in ordered], ["oldest", "middle", "newest"])

    def test_desc(self):
        ordered = _sort_messages_by_ts(self.messages, "desc")
        self.assertEqual([m["text"] for m in ordered], ["newest", "middle", "oldest"])

    def test_missing_ts_sorts_as_zero(self):
        msgs = [
            {"ts": "1.0", "text": "a"},
            {"text": "no-ts"},
            {"ts": "2.0", "text": "b"},
        ]
        ordered = _sort_messages_by_ts(msgs, "asc")
        self.assertEqual([m["text"] for m in ordered], ["no-ts", "a", "b"])

    def test_unparseable_ts_sorts_as_zero(self):
        msgs = [
            {"ts": "1.0", "text": "a"},
            {"ts": "garbage", "text": "bad"},
            {"ts": "2.0", "text": "b"},
        ]
        ordered = _sort_messages_by_ts(msgs, "asc")
        self.assertEqual([m["text"] for m in ordered], ["bad", "a", "b"])

    def test_does_not_mutate_input(self):
        snapshot = [dict(m) for m in self.messages]
        _sort_messages_by_ts(self.messages, "asc")
        self.assertEqual(self.messages, snapshot)


class TestReadParserOrder(unittest.TestCase):
    def setUp(self):
        self.parser = generate_read_parser()

    def test_default_is_desc(self):
        args = self.parser.parse_args(["-c", "C1"])
        self.assertEqual(args.order, "desc")

    def test_asc(self):
        args = self.parser.parse_args(["-c", "C1", "--order", "asc"])
        self.assertEqual(args.order, "asc")

    def test_invalid_rejected(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["-c", "C1", "--order", "sideways"])


class TestRecentParserOrder(unittest.TestCase):
    def setUp(self):
        self.parser = generate_recent_parser()

    def test_default_is_desc(self):
        args = self.parser.parse_args([])
        self.assertEqual(args.order, "desc")

    def test_asc(self):
        args = self.parser.parse_args(["--order", "asc"])
        self.assertEqual(args.order, "asc")

    def test_invalid_rejected(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["--order", "sideways"])


class TestSearchParserOrder(unittest.TestCase):
    def setUp(self):
        self.parser = generate_search_parser()

    def test_default_is_desc(self):
        args = self.parser.parse_args(["-q", "test"])
        self.assertEqual(args.order, "desc")

    def test_asc(self):
        args = self.parser.parse_args(["-q", "test", "--order", "asc"])
        self.assertEqual(args.order, "asc")

    def test_invalid_rejected(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["-q", "test", "--order", "sideways"])

    def test_order_is_independent_of_sort_dir(self):
        # ``--order`` is a local post-fetch sort; ``--sort-dir`` controls
        # the upstream Slack API. They must not collide as argparse args.
        args = self.parser.parse_args(
            ["-q", "test", "--order", "asc", "--sort-dir", "desc"]
        )
        self.assertEqual(args.order, "asc")
        self.assertEqual(args.sort_dir, "desc")


if __name__ == "__main__":
    unittest.main()
