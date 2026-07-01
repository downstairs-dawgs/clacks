"""Tests for `clacks auth login` secret-handling safeguards."""

import argparse
import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from slack_clacks.auth import cli as auth_cli

_CREDS = {
    "access_token": "xoxc-x",
    "user_id": "U1",
    "workspace_id": "T1",
    "app_type": "cookie",
}


class TestLoginSecretFlagWarning(unittest.TestCase):
    def _login_args(self, token: str | None, cookie: str | None) -> argparse.Namespace:
        return argparse.Namespace(
            mode="cookie",
            token=token,
            cookie=cookie,
            context="ctx",
            overwrite=False,
            config_dir=None,
            outfile=io.StringIO(),
        )

    def _run(self, args: argparse.Namespace) -> str:
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            patch.object(auth_cli, "ensure_db_updated"),
            patch.object(auth_cli, "authenticate_with_cookie", return_value=_CREDS),
            patch.object(auth_cli, "get_session"),
            patch.object(auth_cli, "get_context", return_value=None),
            patch.object(auth_cli, "add_context"),
            patch.object(auth_cli, "set_current_context"),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            auth_cli.handle_login(args)
        return stderr.getvalue()

    def test_warns_when_secrets_passed_as_flags(self):
        stderr = self._run(self._login_args(token="xoxc-x", cookie="d-v"))
        self.assertIn("warning", stderr.lower())
        self.assertIn("--token/--cookie", stderr)

    def test_no_warning_when_prompted(self):
        with patch("getpass.getpass", side_effect=["xoxc-x", "d-v"]):
            stderr = self._run(self._login_args(token=None, cookie=None))
        self.assertNotIn("warning", stderr.lower())


if __name__ == "__main__":
    unittest.main()
