import argparse
import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from slack_clacks import main
from slack_clacks.skill.status import SkillInstallStatus


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
                return int(exc.code), stdout.getvalue(), stderr.getvalue()

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
