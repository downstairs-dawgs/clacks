import argparse
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from slack_clacks.messaging.cli import generate_edit_parser, handle_edit
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


class TestEditParser(unittest.TestCase):
    def test_requires_message(self):
        parser = generate_edit_parser()
        with self.assertRaises(SystemExit) as ctx:
            parser.parse_args(["-c", "#general", "--text", "updated"])
        self.assertEqual(ctx.exception.code, 2)

    def test_requires_target(self):
        parser = generate_edit_parser()
        with self.assertRaises(SystemExit) as ctx:
            parser.parse_args(["-m", "1767795445.338939", "--text", "updated"])
        self.assertEqual(ctx.exception.code, 2)

    def test_requires_text_source(self):
        parser = generate_edit_parser()
        with self.assertRaises(SystemExit) as ctx:
            parser.parse_args(["-c", "#general", "-m", "1767795445.338939"])
        self.assertEqual(ctx.exception.code, 2)

    def test_rejects_both_text_and_stdin(self):
        parser = generate_edit_parser()
        with self.assertRaises(SystemExit) as ctx:
            parser.parse_args(
                [
                    "-c",
                    "#general",
                    "-m",
                    "1767795445.338939",
                    "--text",
                    "updated",
                    "--stdin",
                ]
            )
        self.assertEqual(ctx.exception.code, 2)


class TestHandleEdit(unittest.TestCase):
    def _configure_context(self, mock_get_session: MagicMock) -> MagicMock:
        mock_context = MagicMock()
        mock_context.access_token = "xoxp-test"
        mock_context.app_type = "clacks"
        mock_context.name = "test-context"

        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        return mock_context

    def test_channel_path_edits_message_with_normalized_timestamp(self):
        link = "https://workspace.slack.com/archives/C08740LGAE6/p1767795445338939"
        with tempfile.TemporaryDirectory() as tmpdir:
            outfile_path = Path(tmpdir) / "edit_output.json"
            outfile = open(outfile_path, "a", encoding="utf-8")
            args = argparse.Namespace(
                config_dir=None,
                channel="#general",
                user=None,
                message=link,
                text="updated message",
                stdin=False,
                outfile=outfile,
            )

            with (
                patch("slack_clacks.messaging.cli.ensure_db_updated"),
                patch("slack_clacks.messaging.cli.get_session") as mock_get_session,
                patch(
                    "slack_clacks.messaging.cli.get_current_context"
                ) as mock_get_context,
                patch("slack_clacks.messaging.cli.create_client") as mock_create_client,
                patch(
                    "slack_clacks.messaging.cli.resolve_channel_id"
                ) as mock_resolve_channel,
                patch("slack_clacks.messaging.cli.edit_message") as mock_edit_message,
            ):
                mock_context = self._configure_context(mock_get_session)
                mock_get_context.return_value = mock_context
                mock_resolve_channel.return_value = "C12345"

                mock_response = MagicMock()
                mock_response.data = {"ok": True}
                mock_edit_message.return_value = mock_response

                handle_edit(args)

                mock_edit_message.assert_called_once_with(
                    mock_create_client.return_value,
                    "C12345",
                    "1767795445.338939",
                    "updated message",
                )

            with open(outfile_path, encoding="utf-8") as ifp:
                self.assertEqual(ifp.read(), '{"ok": true}')

    def test_dm_path_resolves_user_and_channel(self):
        outfile = io.StringIO()
        args = argparse.Namespace(
            config_dir=None,
            channel=None,
            user="@alice",
            message="1767795445.338939",
            text="dm update",
            stdin=False,
            outfile=outfile,
        )

        with (
            patch("slack_clacks.messaging.cli.ensure_db_updated"),
            patch("slack_clacks.messaging.cli.get_session") as mock_get_session,
            patch("slack_clacks.messaging.cli.get_current_context") as mock_get_context,
            patch("slack_clacks.messaging.cli.create_client") as mock_create_client,
            patch("slack_clacks.messaging.cli.resolve_user_id") as mock_resolve_user,
            patch("slack_clacks.messaging.cli.open_dm_channel") as mock_open_dm,
            patch("slack_clacks.messaging.cli.edit_message") as mock_edit_message,
        ):
            mock_context = self._configure_context(mock_get_session)
            mock_get_context.return_value = mock_context
            mock_resolve_user.return_value = "U123"
            mock_open_dm.return_value = "D999"

            mock_response = MagicMock()
            mock_response.data = {"ok": True}
            mock_edit_message.return_value = mock_response

            handle_edit(args)

            mock_edit_message.assert_called_once_with(
                mock_create_client.return_value,
                "D999",
                "1767795445.338939",
                "dm update",
            )

    def test_reads_text_from_stdin_with_flag(self):
        outfile = io.StringIO()
        args = argparse.Namespace(
            config_dir=None,
            channel="#general",
            user=None,
            message="1767795445.338939",
            text=None,
            stdin=True,
            outfile=outfile,
        )

        with (
            patch("slack_clacks.messaging.cli.ensure_db_updated"),
            patch("slack_clacks.messaging.cli.get_session") as mock_get_session,
            patch("slack_clacks.messaging.cli.get_current_context") as mock_get_context,
            patch("slack_clacks.messaging.cli.create_client") as mock_create_client,
            patch(
                "slack_clacks.messaging.cli.resolve_channel_id"
            ) as mock_resolve_channel,
            patch("slack_clacks.messaging.cli.edit_message") as mock_edit_message,
            patch.object(sys, "stdin", io.StringIO("from stdin\n")),
        ):
            mock_context = self._configure_context(mock_get_session)
            mock_get_context.return_value = mock_context
            mock_resolve_channel.return_value = "C12345"

            mock_response = MagicMock()
            mock_response.data = {"ok": True}
            mock_edit_message.return_value = mock_response

            handle_edit(args)

            mock_edit_message.assert_called_once_with(
                mock_create_client.return_value,
                "C12345",
                "1767795445.338939",
                "from stdin\n",
            )

    def test_stdin_flag_requires_piped_input(self):
        outfile = io.StringIO()
        args = argparse.Namespace(
            config_dir=None,
            channel="#general",
            user=None,
            message="1767795445.338939",
            text=None,
            stdin=True,
            outfile=outfile,
        )

        tty_stdin = MagicMock()
        tty_stdin.isatty.return_value = True

        with (
            patch("slack_clacks.messaging.cli.ensure_db_updated"),
            patch("slack_clacks.messaging.cli.get_session") as mock_get_session,
            patch("slack_clacks.messaging.cli.get_current_context") as mock_get_context,
            patch("slack_clacks.messaging.cli.create_client"),
            patch("slack_clacks.messaging.cli.resolve_channel_id"),
            patch("slack_clacks.messaging.cli.edit_message") as mock_edit_message,
            patch.object(sys, "stdin", tty_stdin),
        ):
            mock_context = self._configure_context(mock_get_session)
            mock_get_context.return_value = mock_context

            with self.assertRaises(ValueError) as ctx:
                handle_edit(args)

            self.assertEqual(str(ctx.exception), "--stdin requires piped input")
            mock_edit_message.assert_not_called()

    def test_empty_text_fails_before_edit_call(self):
        outfile = io.StringIO()
        args = argparse.Namespace(
            config_dir=None,
            channel="#general",
            user=None,
            message="1767795445.338939",
            text="   ",
            stdin=False,
            outfile=outfile,
        )

        with (
            patch("slack_clacks.messaging.cli.ensure_db_updated"),
            patch("slack_clacks.messaging.cli.get_session") as mock_get_session,
            patch("slack_clacks.messaging.cli.get_current_context") as mock_get_context,
            patch("slack_clacks.messaging.cli.create_client"),
            patch("slack_clacks.messaging.cli.resolve_channel_id"),
            patch(
                "slack_clacks.messaging.cli.resolve_message_timestamp"
            ) as mock_resolve_ts,
            patch("slack_clacks.messaging.cli.edit_message") as mock_edit_message,
        ):
            mock_context = self._configure_context(mock_get_session)
            mock_get_context.return_value = mock_context

            with self.assertRaises(ValueError) as ctx:
                handle_edit(args)

            self.assertEqual(str(ctx.exception), "Updated message text cannot be empty")
            mock_resolve_ts.assert_not_called()
            mock_edit_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
