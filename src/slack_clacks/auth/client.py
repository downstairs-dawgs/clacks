"""
Slack WebClient setup for clacks: the rate-limit-aware ClacksWebClient class
and a factory for creating properly configured instances.
"""

from typing import Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.web import SlackResponse

from slack_clacks.auth.constants import MODE_COOKIE
from slack_clacks.exceptions import ClacksRateLimited


class ClacksWebClient(WebClient):
    """WebClient that raises ClacksRateLimited on Slack rate limits.

    SDK method helpers funnel through ``api_call``, so translating here makes
    rate limits surface as ClacksRateLimited (a SlackApiError subclass) from
    API calls, with the Retry-After hint attached. Two paths bypass this:
    SlackResponse cursor-iteration pagination raises raw SlackApiError (clacks
    never iterates responses, and main()'s seam still converts those), and
    ``files_upload_v2``'s file-bytes upload leg raises SlackRequestError,
    outside the SlackApiError domain entirely.
    """

    def api_call(self, *args: Any, **kwargs: Any) -> SlackResponse:
        try:
            return super().api_call(*args, **kwargs)
        except SlackApiError as error:
            rate_limited = ClacksRateLimited.from_slack_error(error)
            if rate_limited is not None and rate_limited is not error:
                raise rate_limited from error
            raise


def create_client(access_token: str, app_type: str) -> ClacksWebClient:
    """
    Create a WebClient configured for the given app type.

    Args:
        access_token: Access token (may be combined token|cookie for cookie mode)
        app_type: Authentication mode (MODE_CLACKS, MODE_CLACKS_LITE, MODE_COOKIE)

    Returns:
        Configured ClacksWebClient instance (raises ClacksRateLimited on 429s)
    """
    if app_type == MODE_COOKIE:
        if "|" in access_token:
            token, cookie = access_token.split("|", 1)
            return ClacksWebClient(token=token, headers={"Cookie": f"d={cookie}"})
        else:
            raise ValueError(
                "Cookie mode requires token in format: xoxc-token|d-cookie-value"
            )

    return ClacksWebClient(token=access_token)
