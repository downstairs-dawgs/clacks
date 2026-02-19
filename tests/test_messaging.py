import unittest
from unittest.mock import patch

from slack_clacks.messaging.operations import parse_timestamp, resolve_message_timestamp


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


class TestParseTimestamp(unittest.TestCase):
    # Slack message links (delegates to resolve_message_timestamp)
    def test_slack_link(self):
        link = "https://workspace.slack.com/archives/C08740LGAE6/p1767795445338939"
        result = parse_timestamp(link)
        self.assertEqual(result, "1767795445.338939")

    # Raw timestamps
    def test_raw_timestamp_with_decimal(self):
        result = parse_timestamp("1770088169.782279")
        self.assertEqual(result, "1770088169.782279")

    def test_raw_timestamp_integer(self):
        result = parse_timestamp("1770088169")
        self.assertEqual(result, "1770088169")

    def test_raw_timestamp_with_whitespace(self):
        result = parse_timestamp("  1770088169.782279  ")
        self.assertEqual(result, "1770088169.782279")

    # ISO 8601 datetimes
    def test_iso_datetime_naive(self):
        result = parse_timestamp("2024-01-15T10:00:00")
        # Naive assumed UTC
        self.assertEqual(result, str(1705312800.0))

    def test_iso_datetime_with_timezone(self):
        result = parse_timestamp("2024-01-15T10:00:00+00:00")
        self.assertEqual(result, str(1705312800.0))

    def test_iso_date_only(self):
        result = parse_timestamp("2024-01-15")
        # Should parse as midnight UTC
        self.assertEqual(result, str(1705276800.0))

    # Relative times (mock time.time())
    @patch("slack_clacks.messaging.operations.time")
    def test_relative_seconds(self, mock_time):
        mock_time.time.return_value = 1000000.0
        result = parse_timestamp("30 seconds ago")
        self.assertEqual(result, str(1000000.0 - 30))

    @patch("slack_clacks.messaging.operations.time")
    def test_relative_minutes(self, mock_time):
        mock_time.time.return_value = 1000000.0
        result = parse_timestamp("5 minutes ago")
        self.assertEqual(result, str(1000000.0 - 300))

    @patch("slack_clacks.messaging.operations.time")
    def test_relative_hours(self, mock_time):
        mock_time.time.return_value = 1000000.0
        result = parse_timestamp("1 hour ago")
        self.assertEqual(result, str(1000000.0 - 3600))

    @patch("slack_clacks.messaging.operations.time")
    def test_relative_days(self, mock_time):
        mock_time.time.return_value = 1000000.0
        result = parse_timestamp("3 days ago")
        self.assertEqual(result, str(1000000.0 - 259200))

    @patch("slack_clacks.messaging.operations.time")
    def test_relative_weeks(self, mock_time):
        mock_time.time.return_value = 1000000.0
        result = parse_timestamp("2 weeks ago")
        self.assertEqual(result, str(1000000.0 - 1209600))

    @patch("slack_clacks.messaging.operations.time")
    def test_relative_singular_unit(self, mock_time):
        mock_time.time.return_value = 1000000.0
        result = parse_timestamp("1 minute ago")
        self.assertEqual(result, str(1000000.0 - 60))

    # Error cases
    def test_empty_string(self):
        with self.assertRaises(ValueError) as ctx:
            parse_timestamp("")
        self.assertIn("Empty", str(ctx.exception))

    def test_whitespace_only(self):
        with self.assertRaises(ValueError) as ctx:
            parse_timestamp("   ")
        self.assertIn("Empty", str(ctx.exception))

    def test_invalid_format(self):
        with self.assertRaises(ValueError) as ctx:
            parse_timestamp("not-a-timestamp-at-all")
        self.assertIn("Unrecognized", str(ctx.exception))

    def test_missing_ago(self):
        with self.assertRaises(ValueError) as ctx:
            parse_timestamp("5 minutes")
        self.assertIn("Unrecognized", str(ctx.exception))

    def test_bad_unit(self):
        with self.assertRaises(ValueError) as ctx:
            parse_timestamp("5 fortnights ago")
        self.assertIn("Unrecognized", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
