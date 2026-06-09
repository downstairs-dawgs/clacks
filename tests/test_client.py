"""Tests for ClacksWebClient's rate-limit translation at the api_call funnel."""

import unittest
from unittest.mock import patch

from slack_sdk.errors import SlackApiError
from slack_sdk.web.base_client import BaseClient
from slack_sdk.web.slack_response import SlackResponse

from slack_clacks.auth.client import ClacksWebClient, create_client
from slack_clacks.auth.constants import MODE_CLACKS, MODE_COOKIE
from slack_clacks.exceptions import ClacksRateLimited


def rate_limited_slack_error() -> SlackApiError:
    """A real SlackApiError shaped like a live-captured 429."""
    response = SlackResponse(
        client=None,
        http_verb="POST",
        api_url="https://slack.com/api/search.messages",
        req_args={},
        data={"ok": False, "error": "ratelimited"},
        headers={"Retry-After": "30"},
        status_code=429,
    )
    return SlackApiError("The request to the Slack API failed.", response)


class TestClacksWebClientRateLimitTranslation(unittest.TestCase):
    def test_method_helper_raises_clacks_rate_limited_on_429(self):
        """SDK method helpers funnel through api_call, so a 429 anywhere
        surfaces as ClacksRateLimited with the Retry-After hint attached."""
        original = rate_limited_slack_error()
        client = ClacksWebClient(token="xoxp-test")

        with patch.object(BaseClient, "api_call", side_effect=original):
            with self.assertRaises(ClacksRateLimited) as ctx:
                client.conversations_history(channel="C123456")

        self.assertEqual(ctx.exception.retry_after, 30)
        self.assertIs(ctx.exception.__cause__, original)

    def test_clacks_rate_limited_is_a_slack_api_error(self):
        """Existing `except SlackApiError` sites must keep catching it."""
        self.assertIsInstance(ClacksRateLimited(30), SlackApiError)

    def test_non_rate_limit_error_passes_through_unchanged(self):
        response = SlackResponse(
            client=None,
            http_verb="POST",
            api_url="https://slack.com/api/conversations.history",
            req_args={},
            data={"ok": False, "error": "channel_not_found"},
            headers={},
            status_code=200,
        )
        original = SlackApiError("The request to the Slack API failed.", response)
        client = ClacksWebClient(token="xoxp-test")

        with patch.object(BaseClient, "api_call", side_effect=original):
            with self.assertRaises(SlackApiError) as ctx:
                client.conversations_history(channel="C123456")

        self.assertIs(ctx.exception, original)
        self.assertNotIsInstance(ctx.exception, ClacksRateLimited)

    def test_successful_call_passes_through(self):
        sentinel = object()
        client = ClacksWebClient(token="xoxp-test")

        with patch.object(BaseClient, "api_call", return_value=sentinel):
            self.assertIs(client.api_call("auth.test"), sentinel)


class TestCreateClientType(unittest.TestCase):
    def test_default_mode_returns_clacks_web_client(self):
        self.assertIsInstance(create_client("xoxp-test", MODE_CLACKS), ClacksWebClient)

    def test_cookie_mode_returns_clacks_web_client(self):
        self.assertIsInstance(
            create_client("xoxc-test|d-cookie", MODE_COOKIE), ClacksWebClient
        )


if __name__ == "__main__":
    unittest.main()
