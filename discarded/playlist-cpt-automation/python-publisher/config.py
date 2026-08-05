"""Discarded czpublish configuration prototype, preserved for reference."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from czpublish.paths import WORDPRESS_APP_PASSWORD_FILE

CONFIG_PATH = Path.home() / ".czpublish.toml"

DEFAULT_CONFIG = """\
site_url = "https://convergencezone.fm"
station = "KSER"

# Base URL used when a broadcast has no spinitron_playlist_ids (best-effort
# field, not guaranteed present) — link to the station's history instead of a
# broken per-playlist URL.
spinitron_fallback_url = "https://spinitron.com/KSER"
"""


@dataclass
class Config:
    site_url: str = "https://convergencezone.fm"
    station: str = "KSER"
    spinitron_fallback_url: str = "https://spinitron.com/KSER"

    @property
    def api_base(self) -> str:
        return f"{self.site_url.rstrip('/')}/wp-json/wp/v2"


def load_config(path: Path = CONFIG_PATH) -> Config:
    if not path.exists():
        path.write_text(DEFAULT_CONFIG)
        print(f"Created default config at {path} — please review it.")

    with open(path, "rb") as f:
        data = tomllib.load(f)

    return Config(
        site_url=data.get("site_url", "https://convergencezone.fm"),
        station=data.get("station", "KSER"),
        spinitron_fallback_url=data.get(
            "spinitron_fallback_url", "https://spinitron.com/KSER"
        ),
    )


@dataclass
class Credentials:
    username: str
    application_password: str


def load_credentials(path: Path = WORDPRESS_APP_PASSWORD_FILE) -> Credentials:
    """Parse the local secret file created via WordPress's Users > Profile >
    Application Passwords screen. Expected shape (see
    shows/convergence-zone/playlists/.wordpress-app-password.local.txt.example):

        username: playlist-scripts
        application-password: xxxx xxxx xxxx xxxx xxxx xxxx
    """
    if not path.exists():
        raise FileNotFoundError(
            f"WordPress credentials not found at {path}. Create an Application "
            "Password under Users > Profile on the site, then save it there "
            "(username: ... / application-password: ... lines). Never commit "
            "this file — it is gitignored."
        )

    text = path.read_text()
    username_match = re.search(r"^username:\s*(.+)$", text, re.MULTILINE)
    password_match = re.search(
        r"^application-password:\s*(.+)$", text, re.MULTILINE
    )
    if not username_match or not password_match:
        raise ValueError(
            f"{path} is missing a `username:` or `application-password:` line."
        )

    return Credentials(
        username=username_match.group(1).strip(),
        application_password=password_match.group(1).strip(),
    )
