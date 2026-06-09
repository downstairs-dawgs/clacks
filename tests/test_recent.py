import unittest
from unittest.mock import MagicMock

from slack_clacks.messaging.operations import get_recent_activity


class TestGetRecentActivity(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()

    def test_paginates_until_cursor_exhausted(self):
        """Conversations from every page are considered, not just the first."""
        self.client.users_conversations.side_effect = [
            {
                "channels": [{"id": "C1", "name": "one"}, {"id": "C2", "name": "two"}],
                "response_metadata": {"next_cursor": "cursor-2"},
            },
            {
                "channels": [{"id": "C3", "name": "three"}],
                "response_metadata": {"next_cursor": ""},
            },
        ]
        ts_by_channel = {"C1": "100.000001", "C2": "200.000001", "C3": "300.000001"}
        self.client.conversations_history.side_effect = lambda channel, limit: {
            "messages": [{"ts": ts_by_channel[channel], "text": f"in {channel}"}]
        }

        messages = get_recent_activity(self.client)

        self.assertEqual(
            {m["channel_id"] for m in messages},
            {"C1", "C2", "C3"},
        )
        self.assertEqual(self.client.users_conversations.call_count, 2)
        cursors = [
            call.kwargs["cursor"]
            for call in self.client.users_conversations.call_args_list
        ]
        self.assertEqual(cursors, [None, "cursor-2"])

    def test_terminates_when_response_metadata_missing(self):
        """A response without response_metadata ends the loop after one page."""
        self.client.users_conversations.side_effect = [
            {"channels": [{"id": "C1", "name": "one"}]},
        ]
        self.client.conversations_history.return_value = {
            "messages": [{"ts": "100.000001", "text": "hi"}]
        }

        messages = get_recent_activity(self.client)

        self.assertEqual([m["channel_id"] for m in messages], ["C1"])
        self.assertEqual(self.client.users_conversations.call_count, 1)


if __name__ == "__main__":
    unittest.main()
