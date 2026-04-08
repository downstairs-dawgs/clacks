import unittest
from datetime import datetime as real_datetime
from datetime import timedelta, timezone
from unittest.mock import patch

from slack_clacks.messaging.operations import (
    parse_schedule_time,
    parse_timestamp,
    resolve_message_timestamp,
)


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


class TestParseScheduleTime(unittest.TestCase):
    # --- Raw Unix timestamp ---
    @patch("slack_clacks.messaging.operations.time")
    def test_unix_timestamp(self, mock_time):
        mock_time.time.return_value = 1000000.0
        result = parse_schedule_time("2000000")
        self.assertEqual(result, 2000000)

    @patch("slack_clacks.messaging.operations.time")
    def test_unix_timestamp_in_past_raises(self, mock_time):
        mock_time.time.return_value = 2000000.0
        with self.assertRaises(ValueError) as ctx:
            parse_schedule_time("1000000")
        self.assertIn("past", str(ctx.exception))

    @patch("slack_clacks.messaging.operations.time")
    def test_unix_timestamp_equal_to_now_raises(self, mock_time):
        mock_time.time.return_value = 1000000.0
        with self.assertRaises(ValueError) as ctx:
            parse_schedule_time("1000000")
        self.assertIn("past", str(ctx.exception))

    # --- Relative future ---
    @patch("slack_clacks.messaging.operations.time")
    def test_relative_minutes(self, mock_time):
        mock_time.time.return_value = 1000000.0
        result = parse_schedule_time("in 30 minutes")
        self.assertEqual(result, 1001800)

    @patch("slack_clacks.messaging.operations.time")
    def test_relative_hours(self, mock_time):
        mock_time.time.return_value = 1000000.0
        result = parse_schedule_time("in 2 hours")
        self.assertEqual(result, 1007200)

    @patch("slack_clacks.messaging.operations.time")
    def test_relative_days(self, mock_time):
        mock_time.time.return_value = 1000000.0
        result = parse_schedule_time("in 1 day")
        self.assertEqual(result, 1086400)

    # --- ISO 8601 ---
    @patch("slack_clacks.messaging.operations.time")
    def test_iso_with_timezone(self, mock_time):
        mock_time.time.return_value = 0.0
        result = parse_schedule_time("2026-03-12T21:00:00+01:00")
        self.assertEqual(result, 1773345600)

    @patch("slack_clacks.messaging.operations.time")
    def test_iso_naive_assumes_utc(self, mock_time):
        mock_time.time.return_value = 0.0
        result = parse_schedule_time("2026-03-12T21:00:00")
        self.assertEqual(result, 1773349200)

    @patch("slack_clacks.messaging.operations.time")
    def test_iso_in_past_raises(self, mock_time):
        mock_time.time.return_value = 2000000000.0
        with self.assertRaises(ValueError) as ctx:
            parse_schedule_time("2020-01-01T00:00:00+00:00")
        self.assertIn("past", str(ctx.exception))

    # --- Time of day with timezone (deterministic) ---
    @patch("slack_clacks.messaging.operations.datetime")
    def test_cet_fixed_offset(self, mock_dt):
        # 2026-03-12 10:00 CET (UTC+1) -> now is 09:00 UTC
        # Schedule for 21:00 CET -> 20:00 UTC same day
        cet = timezone(timedelta(hours=1))
        fake_now = real_datetime(2026, 3, 12, 10, 0, 0, tzinfo=cet)
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *a, **kw: real_datetime(*a, **kw)
        mock_dt.fromisoformat = real_datetime.fromisoformat

        result = parse_schedule_time("9pm CET")
        # 2026-03-12 21:00 CET = 2026-03-12 20:00 UTC
        expected = int(real_datetime(2026, 3, 12, 21, 0, 0, tzinfo=cet).timestamp())
        self.assertEqual(result, expected)

    @patch("slack_clacks.messaging.operations.datetime")
    def test_24h_format_utc(self, mock_dt):
        utc = timezone.utc
        fake_now = real_datetime(2026, 3, 12, 10, 0, 0, tzinfo=utc)
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *a, **kw: real_datetime(*a, **kw)
        mock_dt.fromisoformat = real_datetime.fromisoformat

        result = parse_schedule_time("21:00 UTC")
        expected = int(real_datetime(2026, 3, 12, 21, 0, 0, tzinfo=utc).timestamp())
        self.assertEqual(result, expected)

    @patch("slack_clacks.messaging.operations.datetime")
    def test_rollover_to_next_day(self, mock_dt):
        utc = timezone.utc
        # It's 23:00 UTC, schedule for 9am UTC -> should be tomorrow
        fake_now = real_datetime(2026, 3, 12, 23, 0, 0, tzinfo=utc)
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *a, **kw: real_datetime(*a, **kw)
        mock_dt.fromisoformat = real_datetime.fromisoformat

        result = parse_schedule_time("9am UTC")
        expected = int(real_datetime(2026, 3, 13, 9, 0, 0, tzinfo=utc).timestamp())
        self.assertEqual(result, expected)

    @patch("slack_clacks.messaging.operations.datetime")
    def test_noon_pm(self, mock_dt):
        utc = timezone.utc
        fake_now = real_datetime(2026, 3, 12, 10, 0, 0, tzinfo=utc)
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *a, **kw: real_datetime(*a, **kw)
        mock_dt.fromisoformat = real_datetime.fromisoformat

        result = parse_schedule_time("12pm UTC")
        # 12pm = noon = hour 12
        expected = int(real_datetime(2026, 3, 12, 12, 0, 0, tzinfo=utc).timestamp())
        self.assertEqual(result, expected)

    @patch("slack_clacks.messaging.operations.datetime")
    def test_midnight_am(self, mock_dt):
        utc = timezone.utc
        fake_now = real_datetime(2026, 3, 12, 10, 0, 0, tzinfo=utc)
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *a, **kw: real_datetime(*a, **kw)
        mock_dt.fromisoformat = real_datetime.fromisoformat

        result = parse_schedule_time("12am UTC")
        # 12am = midnight = hour 0, rolls to next day
        expected = int(real_datetime(2026, 3, 13, 0, 0, 0, tzinfo=utc).timestamp())
        self.assertEqual(result, expected)

    def test_invalid_hour_12h_zero(self):
        with self.assertRaises(ValueError) as ctx:
            parse_schedule_time("0pm UTC")
        self.assertIn("Invalid hour", str(ctx.exception))

    def test_invalid_hour_24h(self):
        with self.assertRaises(ValueError) as ctx:
            parse_schedule_time("25:00 UTC")
        self.assertIn("Invalid hour", str(ctx.exception))

    def test_invalid_minute(self):
        with self.assertRaises(ValueError) as ctx:
            parse_schedule_time("9:60pm UTC")
        self.assertIn("Invalid minute", str(ctx.exception))

    def test_unknown_timezone(self):
        with self.assertRaises(ValueError) as ctx:
            parse_schedule_time("9pm XYZTZ")
        self.assertIn("Unknown timezone", str(ctx.exception))

    def test_iana_timezone_directly(self):
        result = parse_schedule_time("9pm America/New_York")
        self.assertIsInstance(result, int)

    # --- Error cases ---
    def test_empty_string(self):
        with self.assertRaises(ValueError) as ctx:
            parse_schedule_time("")
        self.assertIn("Empty", str(ctx.exception))

    def test_unrecognized_format(self):
        with self.assertRaises(ValueError) as ctx:
            parse_schedule_time("next tuesday")
        self.assertIn("Unrecognized", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
