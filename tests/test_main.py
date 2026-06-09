import argparse
import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from slack_sdk.errors import SlackApiError
from slack_sdk.web.slack_response import SlackResponse

from slack_clacks import main
from slack_clacks.exceptions import RATE_LIMIT_EXIT_CODE, ClacksRateLimited
from slack_clacks.skill.status import SkillInstallStatus


def _system_exit_code(exc: SystemExit) -> int:
    code = exc.code
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    return int(code)


class TestMainSkillWarnings(unittest.TestCase):
    def _run_main(
        self,
        argv: list[str],
        status: SkillInstallStatus | None = None,
        exit_code: int | None = None,
    ) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()

        def handler(_: argparse.Namespace) -> None:
            print('{"ok": true}')
            if exit_code is not None:
                raise SystemExit(exit_code)

        parser = MagicMock()
        parser.parse_args.return_value = argparse.Namespace(func=handler)

        with (
            redirect_stdout(stdout),
            redirect_stderr(stderr),
            patch("slack_clacks.generate_cli", return_value=parser),
            patch("slack_clacks.check_skill_install_status", return_value=status),
        ):
            try:
                main(argv)
            except SystemExit as exc:
                return _system_exit_code(exc), stdout.getvalue(), stderr.getvalue()

        return 0, stdout.getvalue(), stderr.getvalue()

    def test_warning_is_emitted_to_stderr_only(self):
        status = SkillInstallStatus(
            path=Path("/tmp/clacks-skill"),
            mode="codex",
            reinstall_command="clacks skill --mode codex --force",
            is_outdated=True,
        )

        code, stdout, stderr = self._run_main(["recent"], status=status)

        self.assertEqual(code, 0)
        self.assertEqual(stdout, '{"ok": true}\n')
        self.assertIn("Warning: installed clacks skill is outdated", stderr)
        self.assertIn("/tmp/clacks-skill", stderr)
        self.assertIn("clacks skill --mode codex --force", stderr)

    def test_warning_does_not_change_exit_status(self):
        status = SkillInstallStatus(
            path=Path("/tmp/clacks-skill"),
            mode="codex",
            reinstall_command="clacks skill --mode codex --force",
            is_outdated=True,
        )

        code, stdout, stderr = self._run_main(
            ["recent"],
            status=status,
            exit_code=7,
        )

        self.assertEqual(code, 7)
        self.assertEqual(stdout, '{"ok": true}\n')
        self.assertIn("clacks skill --mode codex --force", stderr)

    def test_help_invocations_skip_skill_warning_checks(self):
        with patch("slack_clacks.check_skill_install_status") as mock_status:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exc:
                    main(["--help"])

        self.assertEqual(int(exc.exception.code), 0)
        mock_status.assert_not_called()

    def test_version_invocations_skip_skill_warning_checks(self):
        with patch("slack_clacks.check_skill_install_status") as mock_status:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exc:
                    main(["--version"])

        self.assertEqual(int(exc.exception.code), 0)
        mock_status.assert_not_called()


def slack_api_error(
    status_code: int,
    data: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> SlackApiError:
    """Build a SlackApiError carrying a real SlackResponse, fully offline."""
    response = SlackResponse(
        client=None,
        http_verb="POST",
        api_url="https://slack.com/api/chat.postMessage",
        req_args={},
        data=data,
        headers=headers or {},
        status_code=status_code,
    )
    return SlackApiError("The request to the Slack API failed.", response)


class TestMainRateLimitSeam(unittest.TestCase):
    def run_main_with_error(self, error: Exception) -> tuple[int, str, str]:
        """Run main() with a stub handler that raises error.

        Returns (exit code, stdout, stderr). Exceptions other than SystemExit
        propagate to the caller.
        """
        stdout = io.StringIO()
        stderr = io.StringIO()

        def handler(_: argparse.Namespace) -> None:
            raise error

        parser = MagicMock()
        parser.parse_args.return_value = argparse.Namespace(func=handler)

        with (
            redirect_stdout(stdout),
            redirect_stderr(stderr),
            patch("slack_clacks.generate_cli", return_value=parser),
            patch("slack_clacks.check_skill_install_status", return_value=None),
        ):
            try:
                main(["send"])
            except SystemExit as exc:
                return _system_exit_code(exc), stdout.getvalue(), stderr.getvalue()

        return 0, stdout.getvalue(), stderr.getvalue()

    def test_rate_limited_error_exits_75_with_stderr_message(self):
        error = slack_api_error(
            status_code=429,
            data={"ok": False, "error": "ratelimited"},
            headers={"Retry-After": "30"},
        )

        code, stdout, stderr = self.run_main_with_error(error)

        self.assertEqual(code, 75)
        self.assertEqual(code, RATE_LIMIT_EXIT_CODE)
        self.assertEqual(stderr, "rate limited: retry in 30s\n")
        self.assertEqual(stdout, "")

    def test_non_rate_limited_slack_error_propagates(self):
        error = slack_api_error(
            status_code=200,
            data={"ok": False, "error": "channel_not_found"},
        )

        with self.assertRaises(SlackApiError) as ctx:
            self.run_main_with_error(error)

        self.assertIs(ctx.exception, error)

    def test_clacks_rate_limited_from_client_exits_75(self):
        """The production path: ClacksWebClient raises ClacksRateLimited
        directly; the seam must handle it identically to a raw 429."""
        code, stdout, stderr = self.run_main_with_error(ClacksRateLimited(30))

        self.assertEqual(code, RATE_LIMIT_EXIT_CODE)
        self.assertEqual(stderr, "rate limited: retry in 30s\n")
        self.assertEqual(stdout, "")
