"""
Platform and target type definitions for rolodex.
"""

# Platforms
SLACK = "slack"
GITHUB = "github"

# Target types
USER = "user"
CHANNEL = "channel"
REPO = "repo"
ORG = "org"

# Platform -> valid target types mapping
PLATFORM_TARGET_TYPES: dict[str, list[str]] = {
    SLACK: [USER, CHANNEL],
    GITHUB: [USER, REPO, ORG],
}

# All known platforms
PLATFORMS: list[str] = list(PLATFORM_TARGET_TYPES.keys())

# All known target types
TARGET_TYPES: list[str] = list(
    {t for types in PLATFORM_TARGET_TYPES.values() for t in types}
)
