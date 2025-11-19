import http.server
import secrets
import ssl
import threading
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Dict, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from slack_clacks.auth.cert import ensure_cert_exists
from slack_clacks.auth.constants import (
    CLIENT_ID,
    CLIENT_SECRET,
    DEFAULT_USER_SCOPES,
    LITE_CLIENT_ID,
    LITE_CLIENT_SECRET,
    LITE_USER_SCOPES,
    MODE_CLACKS,
    MODE_CLACKS_LITE,
    OAUTH_PORT,
    REDIRECT_URI,
)


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    authorization_code: Optional[str] = None
    error: Optional[str] = None
    expected_state: Optional[str] = None

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path == "/callback":
            query_params = urllib.parse.parse_qs(parsed_path.query)

            received_state = query_params.get("state", [None])[0]
            if received_state != OAuthCallbackHandler.expected_state:
                OAuthCallbackHandler.error = "state_mismatch"
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h1>Authentication failed</h1>"
                    b"<p>Error: State validation failed - potential CSRF attack</p>"
                    b"</body></html>"
                )
                return

            if "code" in query_params:
                OAuthCallbackHandler.authorization_code = query_params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h1>Authentication successful!</h1>"
                    b"<p>You can close this window and return to the terminal.</p>"
                    b"</body></html>"
                )
            elif "error" in query_params:
                OAuthCallbackHandler.error = query_params["error"][0]
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h1>Authentication failed</h1>"
                    b"<p>Error: " + query_params["error"][0].encode() + b"</p>"
                    b"</body></html>"
                )
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def start_oauth_flow(
    scopes: Optional[list] = None,
    config_dir: str | Path | None = None,
    mode: str = MODE_CLACKS,
) -> Dict[str, str]:
    if scopes is None:
        scopes = LITE_USER_SCOPES if mode == MODE_CLACKS_LITE else DEFAULT_USER_SCOPES

    client_id = LITE_CLIENT_ID if mode == MODE_CLACKS_LITE else CLIENT_ID
    client_secret = LITE_CLIENT_SECRET if mode == MODE_CLACKS_LITE else CLIENT_SECRET

    scope_string = ",".join(scopes)
    state = secrets.token_urlsafe(32)

    auth_url = (
        f"https://slack.com/oauth/v2/authorize?"
        f"client_id={client_id}&"
        f"user_scope={urllib.parse.quote(scope_string)}&"
        f"redirect_uri={urllib.parse.quote(REDIRECT_URI)}&"
        f"state={urllib.parse.quote(state)}"
    )

    OAuthCallbackHandler.authorization_code = None
    OAuthCallbackHandler.error = None
    OAuthCallbackHandler.expected_state = state

    cert_path, key_path = ensure_cert_exists(config_dir)

    print(f"Starting HTTPS server on port {OAUTH_PORT}...")
    print(f"Using certificate: {cert_path}")

    try:
        httpd = http.server.HTTPServer(("127.0.0.1", OAUTH_PORT), OAuthCallbackHandler)
        print(f"HTTP server bound to 127.0.0.1:{OAUTH_PORT}")

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        print("SSL context created")

        httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
        print("HTTPS server ready and listening")
    except Exception as e:
        print(f"Failed to start HTTPS server: {e}")
        raise

    def run_server():
        httpd.serve_forever()

    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    print("Opening browser for Slack authentication...")
    print(f"If the browser doesn't open, visit: {auth_url}")
    webbrowser.open(auth_url)

    timeout = 300
    for _ in range(timeout * 10):
        if OAuthCallbackHandler.authorization_code or OAuthCallbackHandler.error:
            break
        threading.Event().wait(0.1)

    httpd.shutdown()

    if OAuthCallbackHandler.error:
        raise Exception(f"OAuth error: {OAuthCallbackHandler.error}")

    if not OAuthCallbackHandler.authorization_code:
        raise Exception("OAuth timeout or no authorization code received")

    authorization_code = OAuthCallbackHandler.authorization_code

    client = WebClient()
    try:
        response = client.oauth_v2_access(
            client_id=client_id,
            client_secret=client_secret,
            code=authorization_code,
            redirect_uri=REDIRECT_URI,
        )

        return {
            "access_token": response["authed_user"]["access_token"],
            "user_id": response["authed_user"]["id"],
            "workspace_id": response["team"]["id"],
            "app_type": mode,
        }
    except SlackApiError as e:
        raise Exception(f"Failed to exchange authorization code: {e.response['error']}")
