import unittest
from typing import Any

from slack_sdk.errors import SlackApiError
from slack_sdk.web.slack_response import SlackResponse

from slack_clacks.exceptions import ClacksRateLimited, rate_limit_retry_after


def slack_response(
    status_code: int,
    data: dict[str, Any] | bytes | None = None,
    headers: dict[str, str] | None = None,
) -> SlackResponse:
    """Build a real SlackResponse offline (no client, no HTTP)."""
    if data is None:
        data = {"ok": False, "error": "ratelimited"}
    return SlackResponse(
        client=None,
        http_verb="POST",
        api_url="https://slack.com/api/conversations.list",
        req_args={},
        data=data,
        headers=headers or {},
        status_code=status_code,
    )


def rate_limited_error(
    status_code: int = 429,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> SlackApiError:
    response = slack_response(status_code, data=data, headers=headers)
    return SlackApiError("The request to the Slack API failed.", response)


class TestRateLimitRetryAfter(unittest.TestCase):
    def test_capitalized_header(self):
        error = rate_limited_error(headers={"Retry-After": "30"})
        self.assertEqual(rate_limit_retry_after(error), 30)

    def test_lowercase_header(self):
        error = rate_limited_error(headers={"retry-after": "12"})
        self.assertEqual(rate_limit_retry_after(error), 12)

    def test_missing_header(self):
        error = rate_limited_error(headers={"x-slack-failure": "ratelimited"})
        self.assertIsNone(rate_limit_retry_after(error))

    def test_malformed_header_value(self):
        error = rate_limited_error(headers={"Retry-After": "soon"})
        self.assertIsNone(rate_limit_retry_after(error))

    def test_negative_header_value(self):
        error = rate_limited_error(headers={"Retry-After": "-5"})
        self.assertIsNone(rate_limit_retry_after(error))

    def test_malformed_value_falls_back_to_valid_duplicate(self):
        error = rate_limited_error(headers={"Retry-After": "soon", "retry-after": "30"})
        self.assertEqual(rate_limit_retry_after(error), 30)


class TestClacksRateLimitedFromSlackError(unittest.TestCase):
    def test_status_429_with_retry_after(self):
        error = rate_limited_error(headers={"Retry-After": "30"})
        translated = ClacksRateLimited.from_slack_error(error)
        self.assertIsNotNone(translated)
        self.assertEqual(translated.retry_after, 30)
        self.assertEqual(str(translated), "rate limited: retry in 30s")

    def test_ratelimited_error_without_429_status(self):
        error = rate_limited_error(status_code=200, headers={"retry-after": "5"})
        translated = ClacksRateLimited.from_slack_error(error)
        self.assertIsNotNone(translated)
        self.assertEqual(translated.retry_after, 5)

    def test_429_without_ratelimited_payload(self):
        error = rate_limited_error(data={"ok": False}, headers={"Retry-After": "9"})
        translated = ClacksRateLimited.from_slack_error(error)
        self.assertIsNotNone(translated)
        self.assertEqual(translated.retry_after, 9)

    def test_missing_retry_after_header(self):
        error = rate_limited_error()
        translated = ClacksRateLimited.from_slack_error(error)
        self.assertIsNotNone(translated)
        self.assertIsNone(translated.retry_after)
        self.assertEqual(str(translated), "rate limited: retry later")

    def test_non_rate_limited_error_returns_none(self):
        error = rate_limited_error(
            status_code=200, data={"ok": False, "error": "channel_not_found"}
        )
        self.assertIsNone(ClacksRateLimited.from_slack_error(error))

    def test_bytes_response_data_returns_none(self):
        # SlackResponse.get raises ValueError on bytes data; from_slack_error
        # must tolerate it instead of crashing. SlackApiError's constructor
        # str()s the response (which also rejects bytes), so attach the bytes
        # response after construction.
        error = SlackApiError("boom", None)
        error.response = slack_response(200, data=b"not json")
        self.assertIsNone(ClacksRateLimited.from_slack_error(error))

    def test_error_without_response_returns_none(self):
        # Deliberately degenerate case: SlackApiError carrying no response at
        # all, which a real SlackResponse cannot represent.
        error = SlackApiError("boom", None)
        self.assertIsNone(ClacksRateLimited.from_slack_error(error))


if __name__ == "__main__":
    unittest.main()
