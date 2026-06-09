"""
Client-wide exceptions for clacks.
"""

from typing import Any

from slack_sdk.errors import SlackApiError

RATE_LIMIT_EXIT_CODE = 75  # EX_TEMPFAIL: caller should wait and retry.


def rate_limit_retry_after(error: SlackApiError) -> int | None:
    """Extract the Retry-After value (seconds) from a SlackApiError.

    Reads response headers case-insensitively and tolerates missing or
    malformed values by returning None. Non-positive values are treated as
    missing: a 0 hint would otherwise drive zero-delay hot retries in
    call_with_backoff and useless "retry in 0s" advice from the CLI.
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
        if seconds <= 0:
            continue
        return seconds
    return None


class ClacksRateLimited(SlackApiError):
    """A Slack rate limit (HTTP 429 / "ratelimited"), raised by ClacksWebClient.

    Subclasses SlackApiError so existing ``except SlackApiError`` sites
    (retry loops, best-effort swallows) keep working unchanged; carries the
    Retry-After hint and renders the user-facing message.
    """

    def __init__(self, retry_after: int | None = None, response: Any = None) -> None:
        self.retry_after = retry_after
        self.response = response
        if retry_after is None:
            self.rate_limit_message = "rate limited: retry later"
        else:
            self.rate_limit_message = f"rate limited: retry in {retry_after}s"
        # Bypass SlackApiError.__init__: it str-formats the response into its
        # message, which can itself raise for unusual bodies (e.g. bytes) —
        # unacceptable inside the error path.
        Exception.__init__(self, self.rate_limit_message)

    def __str__(self) -> str:
        return self.rate_limit_message

    @classmethod
    def from_slack_error(cls, error: SlackApiError) -> "ClacksRateLimited | None":
        """Translate a SlackApiError into ClacksRateLimited.

        Returns the error itself when it is already a ClacksRateLimited, and
        None when it is not a rate limit. Detection accepts either HTTP status
        429 or the "ratelimited" error payload.
        """
        if isinstance(error, ClacksRateLimited):
            return error
        response = error.response
        if response is None:
            return None
        if getattr(response, "status_code", None) == 429:
            return cls(retry_after=rate_limit_retry_after(error), response=response)
        try:
            error_code = response.get("error")
        except (AttributeError, TypeError, ValueError):
            return None
        if error_code == "ratelimited":
            return cls(retry_after=rate_limit_retry_after(error), response=response)
        return None
