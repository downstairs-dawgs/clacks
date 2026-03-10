import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from slack_clacks.skill import cli as skill_cli
from slack_clacks.skill.content import (
    MANIFEST_FILENAME,
    get_bundle_contents,
    get_bundle_manifest,
    get_skill_md,
)
from slack_clacks.skill.status import check_skill_install_status


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

            manifest = json.loads(
                (install_dir / MANIFEST_FILENAME).read_text(encoding="utf-8")
            )
            self.assertEqual(manifest, get_bundle_manifest())


class TestSkillInstallStatus(unittest.TestCase):
    def _write_bundle(
        self, install_dir: Path, bundle_contents: dict[str, str] | None = None
    ) -> None:
        contents = bundle_contents or get_bundle_contents()
        for relative_path, content in contents.items():
            file_path = install_dir / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

    def test_no_installed_skill_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cwd = root / "workspace"
            home = root / "home"
            cwd.mkdir()
            home.mkdir()

            status = check_skill_install_status(cwd=cwd, home=home)

        self.assertIsNone(status)

    def test_matching_installed_skill_is_current(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cwd = root / "workspace"
            home = root / "home"
            cwd.mkdir()
            home.mkdir()
            install_dir = home / ".codex" / "skills" / "clacks"
            self._write_bundle(install_dir)

            status = check_skill_install_status(cwd=cwd, home=home)

        self.assertIsNotNone(status)
        assert status is not None
        self.assertFalse(status.is_outdated)
        self.assertEqual(status.mode, "codex")
        self.assertEqual(status.reinstall_command, "clacks skill --mode codex --force")

    def test_legacy_install_without_manifest_is_outdated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cwd = root / "workspace"
            home = root / "home"
            cwd.mkdir()
            home.mkdir()
            install_dir = home / ".codex" / "skills" / "clacks"
            install_dir.mkdir(parents=True)
            (install_dir / "SKILL.md").write_text(get_skill_md(), encoding="utf-8")

            status = check_skill_install_status(cwd=cwd, home=home)

        self.assertIsNotNone(status)
        assert status is not None
        self.assertTrue(status.is_outdated)
        self.assertEqual(status.mode, "codex")

    def test_stale_manifest_hash_is_outdated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cwd = root / "workspace"
            home = root / "home"
            cwd.mkdir()
            home.mkdir()
            install_dir = home / ".codex" / "skills" / "clacks"
            self._write_bundle(install_dir)

            manifest_path = install_dir / MANIFEST_FILENAME
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["bundle_hash"] = "stale"
            manifest_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            status = check_skill_install_status(cwd=cwd, home=home)

        self.assertIsNotNone(status)
        assert status is not None
        self.assertTrue(status.is_outdated)
        self.assertEqual(status.reason, "bundle hash mismatch")

    def test_project_local_install_beats_global_install(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cwd = root / "workspace"
            home = root / "home"
            cwd.mkdir()
            home.mkdir()

            local_install = cwd / ".codex" / "skills" / "clacks"
            global_install = home / ".codex" / "skills" / "clacks"
            local_install.mkdir(parents=True)
            (local_install / "SKILL.md").write_text(get_skill_md(), encoding="utf-8")
            self._write_bundle(global_install)

            status = check_skill_install_status(cwd=cwd, home=home)

        self.assertIsNotNone(status)
        assert status is not None
        self.assertTrue(status.is_outdated)
        self.assertEqual(status.mode, "codex-project")
        self.assertEqual(status.path, local_install.resolve())

    def test_later_stale_install_is_ignored_when_active_install_is_current(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cwd = root / "workspace"
            home = root / "home"
            cwd.mkdir()
            home.mkdir()

            local_install = cwd / ".codex" / "skills" / "clacks"
            global_install = home / ".codex" / "skills" / "clacks"
            self._write_bundle(local_install)
            global_install.mkdir(parents=True)
            (global_install / "SKILL.md").write_text(get_skill_md(), encoding="utf-8")

            status = check_skill_install_status(cwd=cwd, home=home)

        self.assertIsNotNone(status)
        assert status is not None
        self.assertFalse(status.is_outdated)
        self.assertEqual(status.mode, "codex-project")
        self.assertEqual(status.path, local_install.resolve())


if __name__ == "__main__":
    unittest.main()
