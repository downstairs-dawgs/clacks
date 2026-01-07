import unittest

from slack_clacks.messaging.operations import resolve_message_timestamp


class TestResolveMessageTimestamp(unittest.TestCase):
    def test_raw_timestamp(self):
        result = resolve_message_timestamp("1767795445.338939")
        self.assertEqual(result, "1767795445.338939")

    def test_message_link(self):
        link = "https://workspace.slack.com/archives/C08740LGAE6/p1767795445338939"
        result = resolve_message_timestamp(link)
        self.assertEqual(result, "1767795445.338939")

    def test_message_link_different_workspace(self):
        link = "https://mycompany.slack.com/archives/C12345678/p1234567890123456"
        result = resolve_message_timestamp(link)
        self.assertEqual(result, "1234567890.123456")

    def test_message_link_with_query_params(self):
        link = "https://workspace.slack.com/archives/C08740LGAE6/p1767795445338939?thread_ts=1767795445.338939&cid=C08740LGAE6"
        result = resolve_message_timestamp(link)
        self.assertEqual(result, "1767795445.338939")

    def test_message_link_with_fragment(self):
        link = "https://workspace.slack.com/archives/C08740LGAE6/p1767795445338939#something"
        result = resolve_message_timestamp(link)
        self.assertEqual(result, "1767795445.338939")

    def test_invalid_link_no_timestamp(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_message_timestamp(
                "https://workspace.slack.com/archives/C08740LGAE6"
            )
        self.assertIn("Invalid Slack message link", str(ctx.exception))

    def test_invalid_link_bad_format(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_message_timestamp(
                "https://workspace.slack.com/archives/C08740LGAE6/notvalid"
            )
        self.assertIn("Invalid Slack message link", str(ctx.exception))

    def test_invalid_timestamp_no_decimal(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_message_timestamp("1767795445338939")
        self.assertIn("missing decimal", str(ctx.exception))

    def test_invalid_timestamp_garbage_no_decimal(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_message_timestamp("not-a-timestamp")
        self.assertIn("missing decimal", str(ctx.exception))

    def test_invalid_timestamp_garbage_not_a_number(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_message_timestamp("not.a.timestamp")
        self.assertIn("Invalid message identifier", str(ctx.exception))

    def test_short_timestamp_in_link(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_message_timestamp(
                "https://workspace.slack.com/archives/C123/p12345"
            )
        self.assertIn("Invalid timestamp in link", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
