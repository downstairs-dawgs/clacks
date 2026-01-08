"""
CLI for skill command.
"""

import argparse
import sys
from pathlib import Path

from slack_clacks.skill.content import SKILL_MD

# Mode -> path mapping
# Global paths use ~ expansion, project paths are relative to cwd
MODE_PATHS: dict[str, str] = {
    "claude": "~/.claude/skills/clacks/SKILL.md",
    "claude-global": "~/.claude/skills/clacks/SKILL.md",
    "claude-project": ".claude/skills/clacks/SKILL.md",
    "codex": "~/.codex/skills/clacks/SKILL.md",
    "codex-global": "~/.codex/skills/clacks/SKILL.md",
    "codex-project": ".codex/skills/clacks/SKILL.md",
    "universal": "~/.agent/skills/clacks/SKILL.md",
    "universal-global": "~/.agent/skills/clacks/SKILL.md",
    "universal-project": ".agent/skills/clacks/SKILL.md",
    "github": ".github/skills/clacks/SKILL.md",
}


def handle_skill(args: argparse.Namespace) -> None:
    """Handle skill command."""
    # Determine output path
    if args.outdir is not None:
        outdir = Path(args.outdir).expanduser()
        path = outdir / "SKILL.md"
    elif args.mode is not None:
        if args.mode not in MODE_PATHS:
            valid_modes = ", ".join(sorted(MODE_PATHS.keys()))
            print(f"Unknown mode: {args.mode}", file=sys.stderr)
            print(f"Valid modes: {valid_modes}", file=sys.stderr)
            sys.exit(1)
        path = Path(MODE_PATHS[args.mode]).expanduser()
    else:
        # Default: print to stdout
        print(SKILL_MD)
        return

    # Check if parent directory exists
    if not path.parent.exists():
        if not args.force:
            print(f"Directory does not exist: {path.parent}", file=sys.stderr)
            print("Use --force to create it", file=sys.stderr)
            sys.exit(1)
        path.parent.mkdir(parents=True, exist_ok=True)

    # Write SKILL.md
    path.write_text(SKILL_MD)
    print(f"Installed skill to: {path}")


def generate_cli() -> argparse.ArgumentParser:
    """Generate skill CLI parser."""
    parser = argparse.ArgumentParser(
        description="Output or install Agent Skills spec (agentskills.io) SKILL.md"
    )
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "-m",
        "--mode",
        type=str,
        choices=list(MODE_PATHS.keys()),
        default=None,
        help="Installation mode. Without this flag, prints SKILL.md to stdout.",
    )
    output_group.add_argument(
        "-o",
        "--outdir",
        type=str,
        default=None,
        help="Output directory for SKILL.md (writes SKILL.md to this path).",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Create parent directories if they don't exist.",
    )
    parser.set_defaults(func=handle_skill)
    return parser
