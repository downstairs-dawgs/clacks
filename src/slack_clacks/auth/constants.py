MODE_CLACKS = "clacks"
MODE_CLACKS_LITE = "clacks-lite"
MODE_COOKIE = "cookie"

OAUTH_PORT = 51403
REDIRECT_URI = f"https://127.0.0.1:{OAUTH_PORT}/callback"

CLIENT_ID = "9938573476978.9935591662693"
# Mirrors the GitHub CLI localhost OAuth flow implementation
# (https://github.com/cli/cli/blob/d3fb77f096677f9f5572f882f3ed5b3aa882386e/internal/authflow/flow.go)
# so `clacks` and `gh` share the same client secret and redirect mechanics.
CLIENT_SECRET = "cd914f918c2e8b802ebfbd4625e6dde6"

LITE_CLIENT_ID = "9938573476978.9944331808949"
LITE_CLIENT_SECRET = "341f564941b405ddf242169ed3adb23f"

DEFAULT_USER_SCOPES = [
    "channels:history",
    "channels:read",
    "channels:write",
    "chat:write",
    "files:read",
    "files:write",
    "groups:history",
    "groups:read",
    "im:history",
    "im:read",
    "im:write",
    "mpim:history",
    "mpim:read",
    "mpim:write",
    "reactions:read",
    "reactions:write",
    "search:read",
    "team:read",
    "users:read",
    "users:read.email",
]

LITE_USER_SCOPES = [
    "channels:read",
    "chat:write",
    "im:history",
    "im:read",
    "im:write",
    "mpim:history",
    "mpim:read",
    "mpim:write",
    "reactions:read",
    "reactions:write",
    "users:read",
    "users:read.email",
]
