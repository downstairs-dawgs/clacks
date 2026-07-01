"""Tests for `clacks auth instructions`."""

import argparse
import io
import unittest
from contextlib import redirect_stdout

from slack_clacks.auth import cli as auth_cli
from slack_clacks.auth.constants import (
    DEFAULT_USER_SCOPES,
    LITE_USER_SCOPES,
    MODE_CLACKS,
    MODE_CLACKS_LITE,
    MODE_COOKIE,
)
from slack_clacks.auth.instructions import (
    COOKIE_DOC_URL,
    available_modes,
    get_instructions,
    get_overview,
)


class TestInstructionsContent(unittest.TestCase):
    def test_available_modes_are_the_existing_modes(self):
        self.assertEqual(
            available_modes(), [MODE_CLACKS, MODE_CLACKS_LITE, MODE_COOKIE]
        )

    def test_overview_lists_every_mode(self):
        overview = get_overview()
        for mode in available_modes():
            self.assertIn(mode, overview)
        self.assertIn("--mode", overview)

    def test_clacks_instructions_show_the_login_command_and_scopes(self):
        text = get_instructions(MODE_CLACKS)
        self.assertIn("clacks auth login --mode clacks", text)
        # Scopes are rendered from constants, so a representative full-mode
        # scope must be present.
        self.assertIn("search:read", text)

    def test_lite_instructions_use_the_reduced_scope_set(self):
        text = get_instructions(MODE_CLACKS_LITE)
        self.assertIn("clacks auth login --mode clacks-lite", text)
        # search:read is a full-mode scope only; it must not appear for lite.
        self.assertNotIn("search:read", text)
        self.assertNotIn("search:read", LITE_USER_SCOPES)
        self.assertIn("search:read", DEFAULT_USER_SCOPES)

    def test_cookie_instructions_reference_the_doc_not_duplicate_it(self):
        text = get_instructions(MODE_COOKIE)
        self.assertIn("xoxc", text)
        self.assertIn(COOKIE_DOC_URL, text)

    def test_cookie_instructions_do_not_advertise_secret_flags(self):
        # Secrets must not be shown as argv (shell history / process listings);
        # the prompt-based flow is the only documented path.
        text = get_instructions(MODE_COOKIE)
        self.assertNotIn("--token", text)
        self.assertNotIn("--cookie", text)

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            get_instructions("bot")


class TestInstructionsCli(unittest.TestCase):
    def _run(self, mode: str | None) -> str:
        args = argparse.Namespace(mode=mode)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            auth_cli.handle_instructions(args)
        return stdout.getvalue()

    def test_no_mode_prints_overview(self):
        out = self._run(None)
        self.assertIn("clacks authentication modes:", out)
        for mode in available_modes():
            self.assertIn(mode, out)

    def test_mode_prints_that_modes_instructions(self):
        out = self._run(MODE_COOKIE)
        self.assertIn("browser session", out)
        self.assertIn(COOKIE_DOC_URL, out)

    def test_parser_registers_instructions_with_mode_choices(self):
        parser = auth_cli.generate_cli()
        parsed = parser.parse_args(["instructions", "--mode", MODE_CLACKS])
        self.assertEqual(parsed.func, auth_cli.handle_instructions)
        self.assertEqual(parsed.mode, MODE_CLACKS)

    def test_parser_rejects_unknown_mode(self):
        parser = auth_cli.generate_cli()
        with self.assertRaises(SystemExit):
            parser.parse_args(["instructions", "--mode", "bot"])


if __name__ == "__main__":
    unittest.main()
