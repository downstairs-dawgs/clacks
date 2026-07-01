"""Setup instructions for clacks authentication modes.

Rendered by ``clacks auth instructions``. Scope lists are derived from
``auth.constants`` so the printed instructions cannot drift from what the
OAuth flow actually requests.
"""

from collections.abc import Callable

from slack_clacks.auth.constants import (
    DEFAULT_USER_SCOPES,
    LITE_USER_SCOPES,
    MODE_CLACKS,
    MODE_CLACKS_LITE,
    MODE_COOKIE,
    OAUTH_PORT,
)

COOKIE_DOC_URL = (
    "https://github.com/downstairs-dawgs/clacks/blob/main/docs/cookie-auth.md"
)

MODE_SUMMARIES: dict[str, str] = {
    MODE_CLACKS: "Full OAuth in your browser. Broad user scopes. Acts as you.",
    MODE_CLACKS_LITE: ("OAuth in your browser with a reduced scope set. Acts as you."),
    MODE_COOKIE: (
        "Reuse an existing Slack browser session (xoxc token + d cookie). No OAuth app."
    ),
}


def _format_scopes(scopes: list[str]) -> str:
    return "\n".join(f"  - {scope}" for scope in scopes)


def _oauth_instructions(mode: str, scopes: list[str]) -> str:
    return f"""\
{mode}: OAuth login

Authenticate in your browser. clacks opens the Slack authorization page and
runs a local HTTPS callback on 127.0.0.1:{OAUTH_PORT} to receive the redirect.

Steps:
  1. Start the login flow:
       clacks auth login --mode {mode}
  2. A browser opens for Slack authorization. The local callback uses a
     self-signed certificate created automatically on first run, so your
     browser may warn about 127.0.0.1 -- proceed past the warning.
  3. Approve the requested scopes, then name the context when prompted.

This stores a user token; clacks acts as you. Granted user scopes:
{_format_scopes(scopes)}
"""


def _cookie_instructions() -> str:
    return f"""\
{MODE_COOKIE}: browser session

Reuse your existing Slack web session instead of creating an OAuth app. You
supply two values extracted from your logged-in browser:
  - xoxc token (personal session token, starts with xoxc-)
  - d cookie (session cookie value)

Steps:
  1. Extract the xoxc token and d cookie from your browser. Full extraction
     guide:
       {COOKIE_DOC_URL}
  2. Log in:
       clacks auth login --mode cookie
     clacks prompts for the xoxc token and d cookie without echoing them.
     Do not pass these secrets as command-line flags: argv is visible in
     shell history, terminal scrollback, and process listings.
  3. Name the context when prompted.

This reuses your user session; clacks acts as you. It stays valid only while
that browser session is valid.
"""


_INSTRUCTIONS: dict[str, Callable[[], str]] = {
    MODE_CLACKS: lambda: _oauth_instructions(MODE_CLACKS, DEFAULT_USER_SCOPES),
    MODE_CLACKS_LITE: lambda: _oauth_instructions(MODE_CLACKS_LITE, LITE_USER_SCOPES),
    MODE_COOKIE: _cookie_instructions,
}


def available_modes() -> list[str]:
    """Return the modes that have setup instructions, in display order."""
    return list(_INSTRUCTIONS.keys())


def get_instructions(mode: str) -> str:
    """Return the full setup instructions for a single mode."""
    if mode not in _INSTRUCTIONS:
        valid = ", ".join(available_modes())
        raise ValueError(f"Unknown mode: {mode}. Valid modes: {valid}")
    return _INSTRUCTIONS[mode]()


def get_overview() -> str:
    """Return a summary of all modes and how to see per-mode detail."""
    lines = ["clacks authentication modes:", ""]
    for mode in available_modes():
        lines.append(f"  {mode}")
        lines.append(f"      {MODE_SUMMARIES[mode]}")
    lines.append("")
    lines.append("Show full setup for a mode:  clacks auth instructions --mode <mode>")
    return "\n".join(lines)
