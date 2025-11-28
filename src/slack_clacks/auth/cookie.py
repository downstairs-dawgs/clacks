"""
Cookie-based authentication for Slack using xoxc token and d cookie.
"""

from typing import Dict

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from slack_clacks.auth.constants import MODE_COOKIE


def authenticate_with_cookie(token: str, cookie: str) -> Dict[str, str]:
    """
    Authenticate using xoxc token and d cookie from browser session.

    Args:
        token: Slack xoxc token (extracted from browser localStorage)
        cookie: Slack d cookie value (extracted from browser cookies)

    Returns:
        Dictionary containing:
        - access_token: Combined token+cookie for API calls
        - user_id: Authenticated user's ID
        - workspace_id: Workspace team ID
        - app_type: MODE_COOKIE constant

    Raises:
        Exception: If authentication fails
    """
    client = WebClient(token=token, headers={"Cookie": f"d={cookie}"})

    try:
        auth_response = client.auth_test()

        return {
            "access_token": f"{token}|{cookie}",
            "user_id": auth_response["user_id"],
            "workspace_id": auth_response["team_id"],
            "app_type": MODE_COOKIE,
        }
    except SlackApiError as e:
        raise Exception(f"Cookie authentication failed: {e.response['error']}")
