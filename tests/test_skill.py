import argparse
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from slack_clacks.skill import cli as skill_cli
from slack_clacks.skill.content import get_bundle_contents, get_skill_md


class TestSkillCommand(unittest.TestCase):
    def _run_handle_skill(self, args: argparse.Namespace) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                skill_cli.handle_skill(args)
                return 0, stdout.getvalue(), stderr.getvalue()
            except SystemExit as exc:
                return int(exc.code), stdout.getvalue(), stderr.getvalue()

    def test_prints_skill_md_when_no_output_args(self):
        args = argparse.Namespace(mode=None, outdir=None, force=False)

        code, stdout, stderr = self._run_handle_skill(args)

        self.assertEqual(code, 0)
        self.assertEqual(stdout, f"{get_skill_md()}\n")
        self.assertEqual(stderr, "")

    def test_mode_install_creates_missing_directories_and_bundle_files(self):
        bundle = get_bundle_contents()
        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = Path(tmpdir) / "nested" / "codex" / "skills" / "clacks"
            with patch.dict(skill_cli.MODE_DIRS, {"codex": str(install_dir)}):
                args = argparse.Namespace(mode="codex", outdir=None, force=False)
                code, stdout, stderr = self._run_handle_skill(args)

            self.assertEqual(code, 0)
            self.assertEqual(stderr, "")
            self.assertIn("Installed skill bundle to:", stdout)
            self.assertTrue(install_dir.is_dir())
            for relative_path, expected_content in bundle.items():
                file_path = install_dir / relative_path
                self.assertTrue(file_path.exists())
                self.assertEqual(
                    file_path.read_text(encoding="utf-8"), expected_content
                )

    def test_mode_install_fails_if_target_exists_without_force(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = Path(tmpdir) / "skills" / "clacks"
            install_dir.mkdir(parents=True)
            with patch.dict(skill_cli.MODE_DIRS, {"codex": str(install_dir)}):
                args = argparse.Namespace(mode="codex", outdir=None, force=False)
                code, stdout, stderr = self._run_handle_skill(args)

        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Skill directory already exists", stderr)
        self.assertIn("Use --force to overwrite it", stderr)

    def test_mode_install_overwrites_existing_target_with_force(self):
        bundle = get_bundle_contents()
        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = Path(tmpdir) / "skills" / "clacks"
            install_dir.mkdir(parents=True)
            (install_dir / "SKILL.md").write_text("stale", encoding="utf-8")
            (install_dir / "stale.txt").write_text("remove me", encoding="utf-8")

            with patch.dict(skill_cli.MODE_DIRS, {"codex": str(install_dir)}):
                args = argparse.Namespace(mode="codex", outdir=None, force=True)
                code, stdout, stderr = self._run_handle_skill(args)

            self.assertEqual(code, 0)
            self.assertEqual(stderr, "")
            self.assertIn("Installed skill bundle to:", stdout)
            self.assertFalse((install_dir / "stale.txt").exists())
            for relative_path, expected_content in bundle.items():
                file_path = install_dir / relative_path
                self.assertTrue(file_path.exists())
                self.assertEqual(
                    file_path.read_text(encoding="utf-8"), expected_content
                )

    def test_outdir_install_and_overwrite_semantics_match_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = Path(tmpdir) / "outdir-skill"
            args = argparse.Namespace(mode=None, outdir=str(install_dir), force=False)
            first_code, _, first_stderr = self._run_handle_skill(args)
            second_code, _, second_stderr = self._run_handle_skill(args)

            force_args = argparse.Namespace(
                mode=None, outdir=str(install_dir), force=True
            )
            third_code, _, third_stderr = self._run_handle_skill(force_args)

        self.assertEqual(first_code, 0)
        self.assertEqual(first_stderr, "")
        self.assertEqual(second_code, 1)
        self.assertIn("Skill directory already exists", second_stderr)
        self.assertIn("Use --force to overwrite it", second_stderr)
        self.assertEqual(third_code, 0)
        self.assertEqual(third_stderr, "")

    def test_installed_openai_yaml_has_expected_interface_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = Path(tmpdir) / "skills" / "clacks"
            with patch.dict(skill_cli.MODE_DIRS, {"codex": str(install_dir)}):
                args = argparse.Namespace(mode="codex", outdir=None, force=False)
                code, _, stderr = self._run_handle_skill(args)

            self.assertEqual(code, 0)
            self.assertEqual(stderr, "")

            openai_yaml = (install_dir / "agents" / "openai.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn('display_name: "Clacks"', openai_yaml)
            self.assertIn(
                'short_description: "Send and read Slack messages in Codex"',
                openai_yaml,
            )
            self.assertIn("$clacks", openai_yaml)


if __name__ == "__main__":
    unittest.main()
