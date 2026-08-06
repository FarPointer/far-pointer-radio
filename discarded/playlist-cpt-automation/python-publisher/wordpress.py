"""Discarded REST client for the abandoned `playlist` custom post type.

Uses HTTP Basic Auth with an Application Password (WordPress core feature
since 5.6 — no extra plugin needed for auth itself). Requires HTTPS in
production, which convergencezone.fm already has.
"""

from __future__ import annotations

import requests

from czpublish.config import Config, Credentials


class WordPressClient:
    def __init__(self, config: Config, credentials: Credentials):
        self.config = config
        self.auth = (credentials.username, credentials.application_password)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers["User-Agent"] = "czpublish/0.1 (+https://github.com/farpointer)"

    # -- lookups ------------------------------------------------------------

    def find_playlist_by_air_datetime(self, air_datetime: str) -> dict | None:
        """Find an existing `playlist` post by its cz_air_datetime meta, so
        re-running the publisher updates the same post instead of creating a
        duplicate (needed for the two-pass Mixcloud-embed publish)."""
        resp = self.session.get(
            f"{self.config.api_base}/playlist",
            params={"meta_key": "cz_air_datetime", "meta_value": air_datetime, "status": "any"},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json()
        return results[0] if results else None

    # -- taxonomy -------------------------------------------------------

    def ensure_host_term_ids(self, host_names: list[str]) -> list[int]:
        """Get-or-create `host` taxonomy terms, return their ids."""
        ids = []
        for name in host_names:
            resp = self.session.get(
                f"{self.config.api_base}/host", params={"search": name}, timeout=15
            )
            resp.raise_for_status()
            match = next((t for t in resp.json() if t["name"] == name), None)
            if match:
                ids.append(match["id"])
                continue

            create = self.session.post(
                f"{self.config.api_base}/host", json={"name": name}, timeout=15
            )
            create.raise_for_status()
            ids.append(create.json()["id"])
        return ids

    # -- posts ----------------------------------------------------------

    def create_or_update_playlist(self, payload: dict) -> dict:
        """payload must include meta.cz_air_datetime; used as the idempotency key."""
        existing = self.find_playlist_by_air_datetime(payload["meta"]["cz_air_datetime"])
        if existing:
            resp = self.session.post(
                f"{self.config.api_base}/playlist/{existing['id']}", json=payload, timeout=30
            )
        else:
            resp = self.session.post(f"{self.config.api_base}/playlist", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
