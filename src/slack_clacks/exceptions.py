"""
Client-wide exceptions for clacks.
"""

from typing import Any

from slack_sdk.errors import SlackApiError

RATE_LIMIT_EXIT_CODE = 75  # EX_TEMPFAIL: caller should wait and retry.


def rate_limit_retry_after(error: SlackApiError) -> int | None:
    """Extract the Retry-After value (seconds) from a SlackApiError.

    Reads response headers case-insensitively and tolerates missing or
    malformed values by returning None.
    """
    headers: Any = getattr(error.response, "headers", None)
    if not headers:
        return None
    for key, value in headers.items():
        if str(key).lower() != "retry-after":
            continue
        try:
            seconds = int(str(value).strip())
        except ValueError:
            continue
        if seconds < 0:
            continue
        return seconds
    return None


class ClacksRateLimited(Exception):
    """CLI-facing translation of a Slack rate limit (HTTP 429 / "ratelimited").

    Carries the Retry-After hint and renders the user-facing message; it is
    constructed from a SlackApiError rather than raised by API call sites.
    """

    def __init__(self, retry_after: int | None = None) -> None:
        self.retry_after = retry_after
        if retry_after is None:
            message = "rate limited: retry later"
        else:
            message = f"rate limited: retry in {retry_after}s"
        super().__init__(message)

    @classmethod
    def from_slack_error(cls, error: SlackApiError) -> "ClacksRateLimited | None":
        """Translate a SlackApiError into ClacksRateLimited.

        Returns None when the error is not a rate limit. Detection accepts
        either HTTP status 429 or the "ratelimited" error payload.
        """
        response = error.response
        if response is None:
            return None
        if getattr(response, "status_code", None) == 429:
            return cls(retry_after=rate_limit_retry_after(error))
        try:
            error_code = response.get("error")
        except (AttributeError, TypeError, ValueError):
            return None
        if error_code == "ratelimited":
            return cls(retry_after=rate_limit_retry_after(error))
        return None
