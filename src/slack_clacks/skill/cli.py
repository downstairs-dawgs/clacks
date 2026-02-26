"""
CLI for skill command.
"""

import argparse
import shutil
import sys
from pathlib import Path

from slack_clacks.skill.content import get_bundle_contents, get_skill_md

# Mode -> directory mapping
# Global paths use ~ expansion, project paths are relative to cwd
MODE_DIRS: dict[str, str] = {
    "claude": "~/.claude/skills/clacks",
    "claude-global": "~/.claude/skills/clacks",
    "claude-project": ".claude/skills/clacks",
    "codex": "~/.codex/skills/clacks",
    "codex-global": "~/.codex/skills/clacks",
    "codex-project": ".codex/skills/clacks",
    "universal": "~/.agent/skills/clacks",
    "universal-global": "~/.agent/skills/clacks",
    "universal-project": ".agent/skills/clacks",
    "github": ".github/skills/clacks",
}


def _resolve_install_dir(args: argparse.Namespace) -> Path | None:
    """Resolve the destination directory for bundle installation."""
    if args.outdir is not None:
        return Path(args.outdir).expanduser()
    if args.mode is not None:
        if args.mode not in MODE_DIRS:
            valid_modes = ", ".join(sorted(MODE_DIRS.keys()))
            print(f"Unknown mode: {args.mode}", file=sys.stderr)
            print(f"Valid modes: {valid_modes}", file=sys.stderr)
            sys.exit(1)
        return Path(MODE_DIRS[args.mode]).expanduser()
    return None


def _install_bundle(path: Path, force: bool) -> None:
    """Install the bundled skill files to a target directory."""
    if path.exists():
        if not force:
            print(f"Skill directory already exists: {path}", file=sys.stderr)
            print("Use --force to overwrite it", file=sys.stderr)
            sys.exit(1)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    path.mkdir(parents=True, exist_ok=True)
    for relative_path, content in get_bundle_contents().items():
        destination = path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")


def handle_skill(args: argparse.Namespace) -> None:
    """Handle skill command."""
    install_dir = _resolve_install_dir(args)
    if install_dir is None:
        # Default: print SKILL.md to stdout
        print(get_skill_md())
        return

    if not install_dir.parent.exists():
        # Create top-level parent directory chain when needed.
        install_dir.parent.mkdir(parents=True, exist_ok=True)

    _install_bundle(install_dir, args.force)
    print(f"Installed skill bundle to: {install_dir}")


def generate_cli() -> argparse.ArgumentParser:
    """Generate skill CLI parser."""
    parser = argparse.ArgumentParser(
        description="Output or install Agent Skills spec (agentskills.io) bundle."
    )
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "-m",
        "--mode",
        type=str,
        choices=list(MODE_DIRS.keys()),
        default=None,
        help="Installation mode. Without this flag, prints SKILL.md to stdout.",
    )
    output_group.add_argument(
        "-o",
        "--outdir",
        type=str,
        default=None,
        help="Output directory for skill bundle (writes SKILL.md and support files).",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite existing skill directory.",
    )
    parser.set_defaults(func=handle_skill)
    return parser
