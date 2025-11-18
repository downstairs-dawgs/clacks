import http.server
import ssl
import threading
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Dict, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .cert import ensure_cert_exists
from .constants import (
    CLIENT_ID,
    CLIENT_SECRET,
    DEFAULT_USER_SCOPES,
    OAUTH_PORT,
    REDIRECT_URI,
)


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    authorization_code: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path == "/callback":
            query_params = urllib.parse.parse_qs(parsed_path.query)

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
    scopes: Optional[list] = None, config_dir: str | Path | None = None
) -> Dict[str, str]:
    if scopes is None:
        scopes = DEFAULT_USER_SCOPES

    scope_string = ",".join(scopes)

    auth_url = (
        f"https://slack.com/oauth/v2/authorize?"
        f"client_id={CLIENT_ID}&"
        f"user_scope={urllib.parse.quote(scope_string)}&"
        f"redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
    )

    OAuthCallbackHandler.authorization_code = None
    OAuthCallbackHandler.error = None

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
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            code=authorization_code,
            redirect_uri=REDIRECT_URI,
        )

        return {
            "access_token": response["authed_user"]["access_token"],
            "user_id": response["authed_user"]["id"],
            "workspace_id": response["team"]["id"],
        }
    except SlackApiError as e:
        raise Exception(f"Failed to exchange authorization code: {e.response['error']}")
