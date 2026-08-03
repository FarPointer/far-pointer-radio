"""Mixcloud OAuth flow and multipart upload."""

from __future__ import annotations

import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from czarchive.spinitron import Playlist

MIXCLOUD_AUTH_URL = "https://www.mixcloud.com/oauth/authorize"
MIXCLOUD_TOKEN_URL = "https://www.mixcloud.com/oauth/access_token"
MIXCLOUD_UPLOAD_URL = "https://api.mixcloud.com/upload/"
REDIRECT_URI = "http://localhost:8765/callback"


def get_oauth_url(client_id: str, redirect_uri: str = REDIRECT_URI) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
    }
    return f"{MIXCLOUD_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str = REDIRECT_URI,
) -> str:
    """Exchange an authorization code for an access token."""
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    resp = requests.get(MIXCLOUD_TOKEN_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"Token exchange failed: {data}")
    return token


def run_oauth_flow(client_id: str, client_secret: str) -> str:
    """
    Open browser for OAuth, spin up a local callback server,
    exchange the code, and return the access token.
    """
    auth_url = get_oauth_url(client_id)
    print(f"\nOpening browser for Mixcloud authorization:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    code_holder: list[Optional[str]] = [None]

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            code_holder[0] = params.get("code", [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h1>Authorization received. You may close this tab.</h1>")

        def log_message(self, format, *args):  # silence request logs
            pass

    server = HTTPServer(("localhost", 8765), CallbackHandler)
    print("Waiting for Mixcloud callback on http://localhost:8765/callback …")
    server.handle_request()

    code = code_holder[0]
    if not code:
        raise RuntimeError("No authorization code received from Mixcloud.")

    return exchange_code_for_token(client_id, client_secret, code)


def upload_show(
    mp3_path: Path,
    title: str,
    playlist: Playlist,
    config,
) -> str:
    """
    Upload mp3_path to Mixcloud with full tracklist sections.
    Returns the Mixcloud URL of the newly created cloudcast.
    """
    if not config.mixcloud_access_token:
        raise RuntimeError(
            "No Mixcloud access token. Run `czarchive auth` first."
        )

    # Build multipart form data
    data: dict[str, str] = {
        "name": title,
        "access_token": config.mixcloud_access_token,
        "tags-0-tag": "radio",
        "tags-1-tag": "KSER",
        "tags-2-tag": "Convergence Zone",
    }

    # Add tracklist sections
    for i, spin in enumerate(playlist.spins):
        offset = int((spin.start_time - playlist.start_time).total_seconds())
        if offset < 0:
            offset = 0
        data[f"sections-{i}-chapter"] = str(i)
        data[f"sections-{i}-start_time"] = str(offset)
        data[f"sections-{i}-artist"] = spin.artist
        data[f"sections-{i}-song"] = spin.song

    with open(mp3_path, "rb") as audio_file:
        files = {"mp3": (mp3_path.name, audio_file, "audio/mpeg")}
        resp = requests.post(
            MIXCLOUD_UPLOAD_URL,
            data=data,
            files=files,
            timeout=300,  # large file upload
        )

    resp.raise_for_status()
    result = resp.json()

    if "error" in result:
        raise RuntimeError(f"Mixcloud upload error: {result['error']}")

    slug = result.get("slug") or result.get("key", "").lstrip("/")
    return f"https://www.mixcloud.com/farpointer/{slug}/"
