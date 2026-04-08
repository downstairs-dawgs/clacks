"""
Helpers for detecting stale installed clacks skill bundles.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from slack_clacks.skill.content import (
    BUNDLE_FILE_PATHS,
    MANIFEST_FILENAME,
    get_bundle_manifest,
)


@dataclass(frozen=True)
class SkillInstallStatus:
    """Status for the active clacks skill install."""

    path: Path
    mode: str
    reinstall_command: str
    is_outdated: bool
    reason: str | None = None


def get_skill_install_candidates(
    cwd: Path | None = None, home: Path | None = None
) -> tuple[tuple[str, Path], ...]:
    """Return candidate skill install locations in precedence order."""
    current_dir = (cwd or Path.cwd()).resolve()
    home_dir = (home or Path.home()).expanduser()
    return (
        ("codex-project", current_dir / ".codex" / "skills" / "clacks"),
        ("claude-project", current_dir / ".claude" / "skills" / "clacks"),
        ("universal-project", current_dir / ".agent" / "skills" / "clacks"),
        ("github", current_dir / ".github" / "skills" / "clacks"),
        ("codex", home_dir / ".codex" / "skills" / "clacks"),
        ("claude", home_dir / ".claude" / "skills" / "clacks"),
        ("universal", home_dir / ".agent" / "skills" / "clacks"),
    )


def get_active_skill_install(
    cwd: Path | None = None, home: Path | None = None
) -> tuple[str, Path] | None:
    """Return the first installed clacks skill, if any."""
    for mode, path in get_skill_install_candidates(cwd=cwd, home=home):
        if path.exists():
            return mode, path
    return None


def _make_status(
    mode: str, path: Path, is_outdated: bool, reason: str | None = None
) -> SkillInstallStatus:
    """Build a status object for an installed skill."""
    return SkillInstallStatus(
        path=path,
        mode=mode,
        reinstall_command=f"clacks skill --mode {mode} --force",
        is_outdated=is_outdated,
        reason=reason,
    )


def check_skill_install_status(
    cwd: Path | None = None, home: Path | None = None
) -> SkillInstallStatus | None:
    """Return the active installed skill status, if any."""
    active_install = get_active_skill_install(cwd=cwd, home=home)
    if active_install is None:
        return None

    mode, path = active_install
    if not path.is_dir():
        return _make_status(mode, path, True, "install path is not a directory")

    for relative_path in BUNDLE_FILE_PATHS:
        if not (path / relative_path).is_file():
            return _make_status(
                mode,
                path,
                True,
                f"missing bundled file: {relative_path}",
            )

    manifest_path = path / MANIFEST_FILENAME
    try:
        manifest_text = manifest_path.read_text(encoding="utf-8")
        installed_manifest = json.loads(manifest_text)
    except FileNotFoundError:
        return _make_status(mode, path, True, "missing manifest")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _make_status(mode, path, True, "invalid manifest")

    if not isinstance(installed_manifest, dict):
        return _make_status(mode, path, True, "invalid manifest")

    expected_manifest = get_bundle_manifest()
    if installed_manifest.get("bundle_hash") != expected_manifest["bundle_hash"]:
        return _make_status(mode, path, True, "bundle hash mismatch")

    return _make_status(mode, path, False)
