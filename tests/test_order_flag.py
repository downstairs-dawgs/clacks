"""Tests for the shared ``sort_messages_by_ts`` helper used by the
``--order {asc,desc}`` flag on ``read``, ``recent``, and ``search``.
"""

import unittest

from slack_clacks.messaging.cli import sort_messages_by_ts


class TestSortMessagesByTs(unittest.TestCase):
    def setUp(self):
        # Deliberately out of order.
        self.messages = [
            {"ts": "1767795445.000002", "text": "middle"},
            {"ts": "1767795445.000003", "text": "newest"},
            {"ts": "1767795445.000001", "text": "oldest"},
        ]

    def test_asc(self):
        ordered = sort_messages_by_ts(self.messages, "asc")
        self.assertEqual([m["text"] for m in ordered], ["oldest", "middle", "newest"])

    def test_desc(self):
        ordered = sort_messages_by_ts(self.messages, "desc")
        self.assertEqual([m["text"] for m in ordered], ["newest", "middle", "oldest"])

    def test_missing_ts_sorts_as_zero(self):
        msgs = [
            {"ts": "1.0", "text": "a"},
            {"text": "no-ts"},
            {"ts": "2.0", "text": "b"},
        ]
        ordered = sort_messages_by_ts(msgs, "asc")
        self.assertEqual([m["text"] for m in ordered], ["no-ts", "a", "b"])

    def test_unparseable_ts_sorts_as_zero(self):
        msgs = [
            {"ts": "1.0", "text": "a"},
            {"ts": "garbage", "text": "bad"},
            {"ts": "2.0", "text": "b"},
        ]
        ordered = sort_messages_by_ts(msgs, "asc")
        self.assertEqual([m["text"] for m in ordered], ["bad", "a", "b"])

    def test_does_not_mutate_input(self):
        snapshot = [dict(m) for m in self.messages]
        sort_messages_by_ts(self.messages, "asc")
        self.assertEqual(self.messages, snapshot)


if __name__ == "__main__":
    unittest.main()
