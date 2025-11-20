"""
Custom exceptions for messaging operations.
"""


class ClacksUserNotFoundError(Exception):
    """Raised when a user lookup fails."""

    pass


class ClacksChannelNotFoundError(Exception):
    """Raised when a channel lookup fails."""

    pass
