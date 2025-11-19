"""
Scope validation for OAuth operations.
"""

from slack_clacks.auth.constants import (
    DEFAULT_USER_SCOPES,
    LITE_USER_SCOPES,
    MODE_CLACKS_LITE,
)


class ClacksInsufficientPermissions(Exception):
    """Raised when an operation requires scopes not available in current mode."""

    pass


def validate(
    required_scope: str,
    available_scopes: list[str],
    raise_on_error: bool = False,
) -> bool:
    """
    Validate that a required scope is available.

    Args:
        required_scope: The scope required for the operation
        available_scopes: List of scopes available to the current context
        raise_on_error: If True, raise ClacksInsufficientPermissions
            instead of returning False

    Returns:
        True if scope is available, False otherwise

    Raises:
        ClacksInsufficientPermissions: If scope is missing and raise_on_error is True
    """
    if required_scope not in available_scopes:
        if raise_on_error:
            raise ClacksInsufficientPermissions(
                f"Operation requires '{required_scope}' scope which is not available. "
                f"Your current context may be using 'clacks-lite' mode. "
                f"Re-authenticate with: clacks auth login --mode clacks"
            )
        return False
    return True


def get_scopes_for_mode(mode: str) -> list[str]:
    """
    Get the list of OAuth scopes for a given mode.

    Args:
        mode: The app mode (MODE_CLACKS or MODE_CLACKS_LITE)

    Returns:
        List of OAuth scopes available in that mode
    """
    if mode == MODE_CLACKS_LITE:
        return LITE_USER_SCOPES
    return DEFAULT_USER_SCOPES
