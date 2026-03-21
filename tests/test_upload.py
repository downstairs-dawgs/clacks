import argparse
import io
import sys
import unittest
from unittest.mock import MagicMock, patch

from slack_clacks.auth.validation import ClacksInsufficientPermissions
from slack_clacks.upload.cli import handle_snippet, handle_upload
from slack_clacks.upload.operations import infer_filetype


class TestInferFiletype(unittest.TestCase):
    def test_python(self):
        self.assertEqual(infer_filetype("script.py"), "python")

    def test_javascript(self):
        self.assertEqual(infer_filetype("app.js"), "javascript")

    def test_typescript(self):
        self.assertEqual(infer_filetype("index.ts"), "typescript")

    def test_go(self):
        self.assertEqual(infer_filetype("main.go"), "go")

    def test_shell(self):
        self.assertEqual(infer_filetype("deploy.sh"), "shell")

    def test_yaml(self):
        self.assertEqual(infer_filetype("config.yaml"), "yaml")
        self.assertEqual(infer_filetype("config.yml"), "yaml")

    def test_unknown_extension(self):
        self.assertEqual(infer_filetype("data.xyz"), "text")

    def test_no_extension(self):
        self.assertEqual(infer_filetype("README"), "text")

    def test_dockerfile(self):
        self.assertEqual(infer_filetype("Dockerfile"), "dockerfile")

    def test_makefile(self):
        self.assertEqual(infer_filetype("Makefile"), "makefile")

    def test_case_insensitive_extension(self):
        self.assertEqual(infer_filetype("script.PY"), "python")

    def test_nested_path(self):
        self.assertEqual(infer_filetype("/some/path/to/file.rs"), "rust")


class TestHandleUploadWithFile(unittest.TestCase):
    @patch("slack_clacks.upload.cli.ensure_db_updated")
    @patch("slack_clacks.upload.cli.get_session")
    @patch("slack_clacks.upload.cli.create_client")
    @patch("slack_clacks.upload.cli.upload_file")
    @patch("slack_clacks.upload.cli.resolve_channel_id")
    def test_upload_file_to_channel(
        self,
        mock_resolve_channel,
        mock_upload_file,
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

        ctx_patch = patch(
            "slack_clacks.upload.cli.get_current_context",
            return_value=mock_context,
        )
        with ctx_patch:
            mock_resolve_channel.return_value = "C12345"
            mock_upload_file.return_value = {
                "ok": True,
                "file": {"permalink": "https://x.com/f"},
            }

            outfile = io.StringIO()
            args = argparse.Namespace(
                config_dir=None,
                channel="general",
                user=None,
                file="/tmp/test.py",
                filename=None,
                filetype=None,
                title="Test upload",
                comment="Here is the file",
                thread=None,
                outfile=outfile,
            )

            handle_upload(args)

            mock_upload_file.assert_called_once_with(
                mock_create_client.return_value,
                file_path="/tmp/test.py",
                filename="test.py",
                filetype="python",
                title="Test upload",
                comment="Here is the file",
                channel_id="C12345",
                thread_ts=None,
            )


class TestHandleUploadWithStdin(unittest.TestCase):
    @patch("slack_clacks.upload.cli.ensure_db_updated")
    @patch("slack_clacks.upload.cli.get_session")
    @patch("slack_clacks.upload.cli.create_client")
    @patch("slack_clacks.upload.cli.upload_content")
    @patch("slack_clacks.upload.cli.resolve_channel_id")
    def test_upload_stdin_to_channel(
        self,
        mock_resolve_channel,
        mock_upload_content,
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

        ctx_patch = patch(
            "slack_clacks.upload.cli.get_current_context",
            return_value=mock_context,
        )
        with ctx_patch:
            mock_resolve_channel.return_value = "C12345"
            mock_upload_content.return_value = {
                "ok": True,
                "file": {"permalink": "https://x.com/f"},
            }

            outfile = io.StringIO()
            args = argparse.Namespace(
                config_dir=None,
                channel="ops",
                user=None,
                file=None,
                filename="pod-logs.txt",
                filetype="text",
                title=None,
                comment=None,
                thread=None,
                outfile=outfile,
            )

            with patch.object(sys, "stdin", io.StringIO("log line 1\nlog line 2\n")):
                handle_upload(args)

            mock_upload_content.assert_called_once_with(
                mock_create_client.return_value,
                content="log line 1\nlog line 2\n",
                filename="pod-logs.txt",
                filetype="text",
                title=None,
                comment=None,
                channel_id="C12345",
                thread_ts=None,
            )


class TestHandleUploadScopeValidation(unittest.TestCase):
    @patch("slack_clacks.upload.cli.ensure_db_updated")
    @patch("slack_clacks.upload.cli.get_session")
    def test_rejects_clacks_lite(self, mock_get_session, mock_ensure_db):
        mock_context = MagicMock()
        mock_context.access_token = "xoxp-test"
        mock_context.app_type = "clacks-lite"
        mock_context.name = "test-context"

        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        ctx_patch = patch(
            "slack_clacks.upload.cli.get_current_context",
            return_value=mock_context,
        )
        with ctx_patch:
            args = argparse.Namespace(
                config_dir=None,
                channel="general",
                user=None,
                file="/tmp/test.py",
                filename=None,
                filetype=None,
                title=None,
                comment=None,
                thread=None,
                outfile=io.StringIO(),
            )

            with self.assertRaises(ClacksInsufficientPermissions):
                handle_upload(args)


class TestHandleUploadDefaultFilename(unittest.TestCase):
    @patch("slack_clacks.upload.cli.ensure_db_updated")
    @patch("slack_clacks.upload.cli.get_session")
    @patch("slack_clacks.upload.cli.create_client")
    @patch("slack_clacks.upload.cli.upload_content")
    def test_default_filename_with_filetype(
        self,
        mock_upload_content,
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

        ctx_patch = patch(
            "slack_clacks.upload.cli.get_current_context",
            return_value=mock_context,
        )
        with ctx_patch:
            mock_upload_content.return_value = {"ok": True}

            outfile = io.StringIO()
            args = argparse.Namespace(
                config_dir=None,
                channel=None,
                user=None,
                file=None,
                filename=None,
                filetype="python",
                title=None,
                comment=None,
                thread=None,
                outfile=outfile,
            )

            with patch.object(sys, "stdin", io.StringIO("print('hello')\n")):
                handle_upload(args)

            call_kwargs = mock_upload_content.call_args
            self.assertEqual(call_kwargs.kwargs["filename"], "snippet.py")


class TestHandleSnippet(unittest.TestCase):
    @patch("slack_clacks.upload.cli.ensure_db_updated")
    @patch("slack_clacks.upload.cli.get_session")
    @patch("slack_clacks.upload.cli.create_client")
    @patch("slack_clacks.upload.cli.upload_content")
    @patch("slack_clacks.upload.cli.open_dm_channel")
    @patch("slack_clacks.upload.cli._copy_to_clipboard")
    def test_uploads_stdin_to_self_dm(
        self,
        mock_copy_to_clipboard,
        mock_open_dm_channel,
        mock_upload_content,
        mock_create_client,
        mock_get_session,
        mock_ensure_db,
    ):
        mock_context = MagicMock()
        mock_context.access_token = "xoxp-test"
        mock_context.app_type = "clacks"
        mock_context.name = "test-context"
        mock_context.user_id = "USELF123"

        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_open_dm_channel.return_value = "DSELF123"
        mock_upload_content.return_value = {
            "ok": True,
            "file": {
                "permalink": "https://x.com/f",
                "shares": {
                    "private": {
                        "DSELF123": [{"ts": "1234567891.000001"}],
                    }
                },
            },
        }
        mock_create_client.return_value.chat_getPermalink.return_value.data = {
            "ok": True,
            "permalink": "https://workspace.slack.com/archives/DSELF123/p1234567891000001",
        }

        with patch(
            "slack_clacks.upload.cli.get_current_context",
            return_value=mock_context,
        ):
            args = argparse.Namespace(
                config_dir=None,
                filename="build.log",
                filetype="text",
                title="Build log",
                comment="nightly run",
                thread="1234567890.123456",
                outfile=io.StringIO(),
            )

            captured = io.StringIO()
            with patch.object(sys, "stdin", io.StringIO("log line 1\nlog line 2\n")):
                with patch.object(sys, "stdout", captured):
                    handle_snippet(args)

        mock_open_dm_channel.assert_called_once_with(
            mock_create_client.return_value,
            "USELF123",
        )
        mock_create_client.return_value.chat_getPermalink.assert_called_once_with(
            channel="DSELF123",
            message_ts="1234567891.000001",
        )
        mock_upload_content.assert_called_once_with(
            mock_create_client.return_value,
            content="log line 1\nlog line 2\n",
            filename="build.log",
            filetype="text",
            title="Build log",
            comment="nightly run",
            channel_id="DSELF123",
            thread_ts="1234567890.123456",
        )
        mock_copy_to_clipboard.assert_called_once_with(
            "https://workspace.slack.com/archives/DSELF123/p1234567891000001"
        )
        self.assertEqual(
            captured.getvalue(),
            "https://workspace.slack.com/archives/DSELF123/p1234567891000001\n",
        )

    @patch("slack_clacks.upload.cli.ensure_db_updated")
    @patch("slack_clacks.upload.cli.get_session")
    @patch("slack_clacks.upload.cli.create_client")
    @patch("slack_clacks.upload.cli.upload_content")
    @patch("slack_clacks.upload.cli.open_dm_channel")
    @patch("slack_clacks.upload.cli.get_file_info")
    @patch("slack_clacks.upload.cli._copy_to_clipboard")
    def test_resolves_permalink_from_file_info_when_upload_has_no_shares(
        self,
        mock_copy_to_clipboard,
        mock_get_file_info,
        mock_open_dm_channel,
        mock_upload_content,
        mock_create_client,
        mock_get_session,
        mock_ensure_db,
    ):
        mock_context = MagicMock()
        mock_context.access_token = "xoxp-test"
        mock_context.app_type = "clacks"
        mock_context.name = "test-context"
        mock_context.user_id = "USELF123"

        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_open_dm_channel.return_value = "DSELF123"
        mock_upload_content.return_value = {
            "ok": True,
            "file": {
                "id": "F123",
                "permalink": "https://x.com/f",
                "shares": {},
            },
        }
        mock_get_file_info.return_value = {
            "ok": True,
            "file": {
                "id": "F123",
                "shares": {
                    "private": {
                        "DSELF123": [{"ts": "1234567891.000001"}],
                    }
                },
            },
        }
        mock_create_client.return_value.chat_getPermalink.return_value.data = {
            "ok": True,
            "permalink": "https://workspace.slack.com/archives/DSELF123/p1234567891000001",
        }

        with patch(
            "slack_clacks.upload.cli.get_current_context",
            return_value=mock_context,
        ):
            args = argparse.Namespace(
                config_dir=None,
                filename="build.log",
                filetype="text",
                title=None,
                comment=None,
                thread=None,
                outfile=None,
            )

            captured = io.StringIO()
            with patch(
                "slack_clacks.upload.cli._MESSAGE_LINK_RESOLUTION_DELAYS",
                (0.0,),
            ):
                with patch.object(sys, "stdin", io.StringIO("log line 1\n")):
                    with patch.object(sys, "stdout", captured):
                        handle_snippet(args)

        mock_get_file_info.assert_called_once_with(
            mock_create_client.return_value, "F123"
        )
        mock_create_client.return_value.chat_getPermalink.assert_called_once_with(
            channel="DSELF123",
            message_ts="1234567891.000001",
        )
        mock_copy_to_clipboard.assert_called_once_with(
            "https://workspace.slack.com/archives/DSELF123/p1234567891000001"
        )
        self.assertEqual(
            captured.getvalue(),
            "https://workspace.slack.com/archives/DSELF123/p1234567891000001\n",
        )

    @patch("slack_clacks.upload.cli.ensure_db_updated")
    @patch("slack_clacks.upload.cli.get_session")
    @patch("slack_clacks.upload.cli.create_client")
    @patch("slack_clacks.upload.cli.open_dm_channel")
    @patch("slack_clacks.upload.cli.upload_content")
    def test_rejects_stdout_as_json_outfile(
        self,
        mock_upload_content,
        mock_open_dm_channel,
        mock_create_client,
        mock_get_session,
        mock_ensure_db,
    ):
        mock_context = MagicMock()
        mock_context.access_token = "xoxp-test"
        mock_context.app_type = "clacks"
        mock_context.name = "test-context"
        mock_context.user_id = "USELF123"

        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        with patch(
            "slack_clacks.upload.cli.get_current_context",
            return_value=mock_context,
        ):
            args = argparse.Namespace(
                config_dir=None,
                filename=None,
                filetype="text",
                title=None,
                comment=None,
                thread=None,
                outfile=sys.stdout,
            )

            with self.assertRaises(ValueError) as ctx:
                handle_snippet(args)

        self.assertIn(
            "stdout is reserved for the message permalink", str(ctx.exception)
        )
        mock_create_client.assert_not_called()
        mock_open_dm_channel.assert_not_called()
        mock_upload_content.assert_not_called()

    @patch("slack_clacks.upload.cli.ensure_db_updated")
    @patch("slack_clacks.upload.cli.get_session")
    def test_rejects_clacks_lite(self, mock_get_session, mock_ensure_db):
        mock_context = MagicMock()
        mock_context.access_token = "xoxp-test"
        mock_context.app_type = "clacks-lite"
        mock_context.name = "test-context"
        mock_context.user_id = "USELF123"

        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        with patch(
            "slack_clacks.upload.cli.get_current_context",
            return_value=mock_context,
        ):
            args = argparse.Namespace(
                config_dir=None,
                filename=None,
                filetype=None,
                title=None,
                comment=None,
                thread=None,
                outfile=io.StringIO(),
            )

            with self.assertRaises(ClacksInsufficientPermissions):
                handle_snippet(args)

    @patch("slack_clacks.upload.cli.ensure_db_updated")
    @patch("slack_clacks.upload.cli.get_session")
    @patch("slack_clacks.upload.cli.create_client")
    @patch("slack_clacks.upload.cli.open_dm_channel")
    def test_requires_stdin(
        self,
        mock_open_dm_channel,
        mock_create_client,
        mock_get_session,
        mock_ensure_db,
    ):
        mock_context = MagicMock()
        mock_context.access_token = "xoxp-test"
        mock_context.app_type = "clacks"
        mock_context.name = "test-context"
        mock_context.user_id = "USELF123"

        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_open_dm_channel.return_value = "DSELF123"

        with patch(
            "slack_clacks.upload.cli.get_current_context",
            return_value=mock_context,
        ):
            args = argparse.Namespace(
                config_dir=None,
                filename=None,
                filetype="python",
                title=None,
                comment=None,
                thread=None,
                outfile=io.StringIO(),
            )

            with patch.object(sys, "stdin", io.StringIO("")):
                with self.assertRaises(ValueError) as ctx:
                    handle_snippet(args)

        self.assertIn("pipe snippet content to stdin", str(ctx.exception))

    @patch("slack_clacks.upload.cli.ensure_db_updated")
    @patch("slack_clacks.upload.cli.get_session")
    @patch("slack_clacks.upload.cli.create_client")
    @patch("slack_clacks.upload.cli.upload_content")
    @patch("slack_clacks.upload.cli.open_dm_channel")
    @patch("slack_clacks.upload.cli.get_file_info")
    def test_requires_message_permalink(
        self,
        mock_get_file_info,
        mock_open_dm_channel,
        mock_upload_content,
        mock_create_client,
        mock_get_session,
        mock_ensure_db,
    ):
        mock_context = MagicMock()
        mock_context.access_token = "xoxp-test"
        mock_context.app_type = "clacks"
        mock_context.name = "test-context"
        mock_context.user_id = "USELF123"

        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_open_dm_channel.return_value = "DSELF123"
        mock_upload_content.return_value = {
            "ok": True,
            "file": {"permalink": "https://x.com/f"},
        }

        with patch(
            "slack_clacks.upload.cli.get_current_context",
            return_value=mock_context,
        ):
            args = argparse.Namespace(
                config_dir=None,
                filename=None,
                filetype="text",
                title=None,
                comment=None,
                thread=None,
                outfile=None,
            )

            with patch(
                "slack_clacks.upload.cli._MESSAGE_LINK_RESOLUTION_DELAYS",
                (0.0,),
            ):
                with patch.object(sys, "stdin", io.StringIO("hello\n")):
                    with self.assertRaises(ValueError) as ctx:
                        handle_snippet(args)

        self.assertIn("resolve a permalink", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
