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
    "claude": "~/.claude/skills/slack/SKILL.md",
    "claude-global": "~/.claude/skills/slack/SKILL.md",
    "claude-project": ".claude/skills/slack/SKILL.md",
    "codex": "~/.codex/skills/slack/SKILL.md",
    "codex-global": "~/.codex/skills/slack/SKILL.md",
    "codex-project": ".codex/skills/slack/SKILL.md",
    "universal": "~/.agent/skills/slack/SKILL.md",
    "universal-global": "~/.agent/skills/slack/SKILL.md",
    "universal-project": ".agent/skills/slack/SKILL.md",
    "github": ".github/skills/slack/SKILL.md",
}


def handle_skill(args: argparse.Namespace) -> None:
    """Handle skill command."""
    if args.mode is None:
        # Default: print to stdout
        print(SKILL_MD)
        return

    if args.mode not in MODE_PATHS:
        valid_modes = ", ".join(sorted(MODE_PATHS.keys()))
        print(f"Unknown mode: {args.mode}", file=sys.stderr)
        print(f"Valid modes: {valid_modes}", file=sys.stderr)
        sys.exit(1)

    path_str = MODE_PATHS[args.mode]
    path = Path(path_str).expanduser()

    # Create parent directories
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write SKILL.md
    path.write_text(SKILL_MD)
    print(f"Installed skill to: {path}")


def generate_cli() -> argparse.ArgumentParser:
    """Generate skill CLI parser."""
    parser = argparse.ArgumentParser(
        description="Output or install Agent Skills spec (agentskills.io) SKILL.md"
    )
    parser.add_argument(
        "-m",
        "--mode",
        type=str,
        choices=list(MODE_PATHS.keys()),
        default=None,
        help="Installation mode. Without this flag, prints SKILL.md to stdout.",
    )
    parser.set_defaults(func=handle_skill)
    return parser
