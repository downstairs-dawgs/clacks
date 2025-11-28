# Cookie-Based Authentication

Cookie-based authentication allows you to use clacks with your existing Slack browser session by extracting your session token and cookie. This avoids creating a new OAuth app.

## Overview

Slack's web interface uses two credentials for authentication:
- **xoxc token**: Personal session token (starts with `xoxc-`)
- **d cookie**: Session cookie value

These can be extracted from your browser and used with clacks.

## Extracting Credentials from Browser

### Method 1: Browser Developer Tools (Recommended)

**For Chrome/Edge/Brave:**

1. Open Slack in your browser and log in
2. Press `F12` or right-click → **Inspect** to open DevTools
3. Go to the **Application** tab (or **Storage** in Firefox)

**Get the d cookie:**
1. In the left sidebar, expand **Cookies**
2. Click on `https://app.slack.com`
3. Find the cookie named `d`
4. Copy its **Value** (long hexadecimal string)

**Get the xoxc token:**
1. In the **Application** tab, expand **Local Storage** in the left sidebar
2. Click on `https://app.slack.com`
3. Find the key `localConfig_v2`
4. Double-click its value to see the full JSON
5. Or run this in the **Console** tab:
   ```javascript
   JSON.parse(localStorage.localConfig_v2).teams[JSON.parse(localStorage.localConfig_v2).lastActiveTeamId].token
   ```
6. Copy the token value (starts with `xoxc-`)

**For Firefox:**

1. Open Slack and log in
2. Press `F12` → **Storage** tab
3. For **d cookie**: Click **Cookies** → `https://app.slack.com` → find `d` cookie
4. For **xoxc token**: Click **Local Storage** → `https://app.slack.com` → find `localConfig_v2`, then use Console method above

**For Safari:**

1. Enable Developer menu: **Safari** → **Preferences** → **Advanced** → check **Show Develop menu**
2. **Develop** → **Show Web Inspector**
3. Follow similar steps as Chrome (Storage tab)

### Method 2: Using slacktokens Python Package

```bash
pip install slacktokens
python -m slacktokens
```

This automatically extracts tokens from the Slack desktop app's local storage.

## Using Cookie Auth with clacks

Once you have both credentials:

```bash
clacks auth login --mode cookie -c my-context
```

You'll be prompted to enter:
1. `xoxc` token
2. `d` cookie value

Or provide them directly:

```bash
clacks auth login --mode cookie --token "xoxc-..." --cookie "..." -c my-context
```

## Security Considerations

**Important Warnings:**

1. **Session tokens are sensitive** - They grant full access to your Slack account
2. **Cookie-dependent** - The token only works with its matching cookie
3. **Session expiration** - Tokens expire when you log out of Slack in the browser
4. **No revocation** - Tokens can't be revoked via `clacks auth logout` (only OAuth tokens can)
5. **Shared across workspaces** - The `d` cookie works for all your Slack workspaces

**Best Practices:**

- Never share your tokens or cookies
- Don't commit them to version control
- Tokens expire when you log out, requiring re-extraction
- Use OAuth modes (clacks/clacks-lite) for better security and manageability

## Cookie vs OAuth Modes

| Feature | Cookie | clacks (OAuth) | clacks-lite (OAuth) |
|---------|--------|----------------|---------------------|
| Browser required | For extraction only | Yes (during auth) | Yes (during auth) |
| Setup steps | Extract from browser | OAuth flow | OAuth flow |
| Token management | Manual re-extraction | Automatic | Automatic |
| Revocation | Logout from browser | Via API | Via API |
| Expiration | On browser logout | Rarely | Rarely |
| Scopes | All user permissions | Fixed (full) | Fixed (restricted) |
| Multi-workspace | One `d` cookie for all | Per workspace | Per workspace |

## Troubleshooting

**"Cookie authentication failed: invalid_auth":**
- Token or cookie may be invalid or expired
- Verify you copied the complete values
- Log out and back in to Slack, then re-extract

**"Cookie authentication failed: missing_scope":**
- Your Slack session doesn't have required permissions
- Check workspace admin settings

**Token expired:**
- Log out of Slack in browser, log back in
- Re-extract token and cookie
- Re-authenticate with clacks

**d cookie format:**
- Should be a long hexadecimal string
- Do not include `d=` prefix, just the value
- Do not include semicolons or other cookies

**xoxc token format:**
- Must start with `xoxc-`
- Include the entire token string

## When to Use Cookie Mode

**Good use cases:**
- Quick testing without setting up OAuth
- Temporary access
- Environments where OAuth flow is blocked
- You need access to multiple workspaces with one auth

**Not recommended for:**
- Production automation (use OAuth modes instead)
- Long-running scripts (tokens expire on browser logout)
- Security-conscious environments (OAuth provides better audit trails)
- CI/CD pipelines (OAuth modes are more reliable)

## Alternative: Use OAuth Modes

For most use cases, OAuth modes are preferred:

```bash
# Full access
clacks auth login --mode clacks

# Restricted access (DMs only)
clacks auth login --mode clacks-lite
```

OAuth provides better security, automatic token management, and proper revocation support.
