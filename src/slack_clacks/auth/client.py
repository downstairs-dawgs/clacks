"""
Helper functions for creating properly configured Slack WebClients.
"""

from slack_sdk import WebClient

from slack_clacks.auth.constants import MODE_COOKIE


def create_client(access_token: str, app_type: str) -> WebClient:
    """
    Create a WebClient configured for the given app type.

    Args:
        access_token: Access token (may be combined token|cookie for cookie mode)
        app_type: Authentication mode (MODE_CLACKS, MODE_CLACKS_LITE, MODE_COOKIE)

    Returns:
        Configured WebClient instance
    """
    if app_type == MODE_COOKIE:
        if "|" in access_token:
            token, cookie = access_token.split("|", 1)
            return WebClient(token=token, headers={"Cookie": f"d={cookie}"})
        else:
            raise ValueError(
                "Cookie mode requires token in format: xoxc-token|d-cookie-value"
            )

    return WebClient(token=access_token)
