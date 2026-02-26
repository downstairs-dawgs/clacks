"""
Skill bundle content loader for clacks.
"""

from importlib.resources import files

BUNDLE_ROOT = files("slack_clacks.skill").joinpath("bundle")

BUNDLE_PATHS: tuple[str, ...] = (
    "SKILL.md",
    "agents/openai.yaml",
    "LICENSE.txt",
)


def get_bundle_contents() -> dict[str, str]:
    """Return bundled skill files keyed by relative path."""
    return {
        relative_path: BUNDLE_ROOT.joinpath(relative_path).read_text(encoding="utf-8")
        for relative_path in BUNDLE_PATHS
    }


def get_skill_md() -> str:
    """Return SKILL.md from the bundled resources."""
    return BUNDLE_ROOT.joinpath("SKILL.md").read_text(encoding="utf-8")
