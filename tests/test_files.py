import argparse
import io
import json
import sys
import unittest
from unittest.mock import MagicMock, patch

from slack_clacks.auth.validation import ClacksInsufficientPermissions
from slack_clacks.files.cli import handle_download, handle_info, handle_list
from slack_clacks.files.operations import (
    _build_download_headers,
    extract_file_id_from_permalink,
)


class TestExtractFileIdFromPermalink(unittest.TestCase):
    def test_workspace_permalink(self):
        url = "https://myteam.slack.com/files/U123ABC/F2147483862/report.pdf"
        self.assertEqual(extract_file_id_from_permalink(url), "F2147483862")

    def test_files_pri_url(self):
        url = "https://files.slack.com/files-pri/T0001/F9876ABCDE/image.png"
        self.assertEqual(extract_file_id_from_permalink(url), "F9876ABCDE")

    def test_invalid_url_raises(self):
        with self.assertRaises(ValueError):
            extract_file_id_from_permalink("https://example.com/no-file-id")

    def test_no_f_prefix_raises(self):
        with self.assertRaises(ValueError):
            extract_file_id_from_permalink("https://slack.com/files/U123/not-a-file")


class TestBuildDownloadHeaders(unittest.TestCase):
    def test_normal_mode(self):
        headers = _build_download_headers("xoxp-abc123", "clacks")
        self.assertEqual(headers, {"Authorization": "Bearer xoxp-abc123"})

    def test_cookie_mode(self):
        headers = _build_download_headers("xoxc-token|d-cookie-val", "cookie")
        self.assertEqual(
            headers,
            {
                "Authorization": "Bearer xoxc-token",
                "Cookie": "d=d-cookie-val",
            },
        )

    def test_cookie_mode_malformed(self):
        with self.assertRaises(ValueError):
            _build_download_headers("xoxc-no-pipe", "cookie")


class TestHandleDownloadScopeValidation(unittest.TestCase):
    @patch("slack_clacks.files.cli.ensure_db_updated")
    @patch("slack_clacks.files.cli.get_session")
    def test_rejects_clacks_lite(self, mock_get_session, mock_ensure_db):
        mock_context = MagicMock()
        mock_context.access_token = "xoxp-test"
        mock_context.app_type = "clacks-lite"
        mock_context.name = "test-context"

        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        with patch(
            "slack_clacks.files.cli.get_current_context",
            return_value=mock_context,
        ):
            args = argparse.Namespace(
                config_dir=None,
                file_id="F123",
                permalink=None,
                write=None,
                force=False,
            )

            with self.assertRaises(ClacksInsufficientPermissions):
                handle_download(args)


class TestHandleInfo(unittest.TestCase):
    @patch("slack_clacks.files.cli.ensure_db_updated")
    @patch("slack_clacks.files.cli.get_session")
    @patch("slack_clacks.files.cli.create_client")
    @patch("slack_clacks.files.cli.get_file_info")
    def test_outputs_json(
        self, mock_get_info, mock_create_client, mock_get_session, mock_ensure_db
    ):
        mock_context = MagicMock()
        mock_context.access_token = "xoxp-test"
        mock_context.app_type = "clacks"
        mock_context.name = "test-context"

        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_get_info.return_value = {
            "ok": True,
            "file": {"id": "F123", "name": "test.txt"},
        }

        with patch(
            "slack_clacks.files.cli.get_current_context",
            return_value=mock_context,
        ):
            args = argparse.Namespace(
                config_dir=None,
                file_id="F123",
            )

            captured = io.StringIO()
            with patch.object(sys, "stdout", captured):
                handle_info(args)

            output = json.loads(captured.getvalue())
            self.assertTrue(output["ok"])
            self.assertEqual(output["file"]["id"], "F123")


class TestHandleList(unittest.TestCase):
    @patch("slack_clacks.files.cli.ensure_db_updated")
    @patch("slack_clacks.files.cli.get_session")
    @patch("slack_clacks.files.cli.create_client")
    @patch("slack_clacks.files.cli.list_files")
    def test_list_no_filters(
        self, mock_list_files, mock_create_client, mock_get_session, mock_ensure_db
    ):
        mock_context = MagicMock()
        mock_context.access_token = "xoxp-test"
        mock_context.app_type = "clacks"
        mock_context.name = "test-context"

        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_list_files.return_value = {
            "ok": True,
            "files": [{"id": "F1", "name": "a.txt"}],
        }

        with patch(
            "slack_clacks.files.cli.get_current_context",
            return_value=mock_context,
        ):
            args = argparse.Namespace(
                config_dir=None,
                channel=None,
                user=None,
                limit=20,
                page=1,
            )

            captured = io.StringIO()
            with patch.object(sys, "stdout", captured):
                handle_list(args)

            output = json.loads(captured.getvalue())
            self.assertTrue(output["ok"])
            self.assertEqual(len(output["files"]), 1)
            mock_list_files.assert_called_once_with(
                mock_create_client.return_value,
                channel=None,
                user=None,
                limit=20,
                page=1,
            )

    @patch("slack_clacks.files.cli.ensure_db_updated")
    @patch("slack_clacks.files.cli.get_session")
    @patch("slack_clacks.files.cli.create_client")
    @patch("slack_clacks.files.cli.list_files")
    @patch("slack_clacks.files.cli.resolve_channel_id")
    @patch("slack_clacks.files.cli.resolve_user_id")
    def test_list_with_channel_and_user(
        self,
        mock_resolve_user,
        mock_resolve_channel,
        mock_list_files,
        mock_create_client,
        mock_get_session,
        mock_ensure_db,
    ):
        mock_context = MagicMock()
        mock_context.access_token = "xoxp-test"
        mock_context.app_type = "clacks"
        mock_context.name = "test-context"

        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_resolve_channel.return_value = "C12345"
        mock_resolve_user.return_value = "U67890"
        mock_list_files.return_value = {"ok": True, "files": []}

        with patch(
            "slack_clacks.files.cli.get_current_context",
            return_value=mock_context,
        ):
            args = argparse.Namespace(
                config_dir=None,
                channel="general",
                user="@alice",
                limit=5,
                page=2,
            )

            captured = io.StringIO()
            with patch.object(sys, "stdout", captured):
                handle_list(args)

            mock_list_files.assert_called_once_with(
                mock_create_client.return_value,
                channel="C12345",
                user="U67890",
                limit=5,
                page=2,
            )


if __name__ == "__main__":
    unittest.main()
