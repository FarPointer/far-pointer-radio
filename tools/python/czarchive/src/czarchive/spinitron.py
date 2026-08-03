"""Spinitron client — scraping and API modes with a shared Protocol."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Protocol
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

PACIFIC = ZoneInfo("America/Los_Angeles")
SPINITRON_BASE = "https://spinitron.com"
SPINITRON_API = "https://spinitron.com/api"


@dataclass
class Spin:
    artist: str
    song: str
    album: str
    start_time: datetime  # timezone-aware, America/Los_Angeles


@dataclass
class Playlist:
    id: str
    title: str
    start_time: datetime
    end_time: datetime
    spins: list[Spin] = field(default_factory=list)


class SpintronClient(Protocol):
    def get_latest_playlist(self, show_name: str) -> Playlist: ...
    def get_playlist_by_date(self, show_name: str, show_date: date) -> Playlist: ...


# ---------------------------------------------------------------------------
# Scraping client
# ---------------------------------------------------------------------------

class ScrapingSpintronClient:
    """Fetch playlist data from public Spinitron HTML pages."""

    def __init__(self, station: str):
        self.station = station
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "czarchive/0.1 (+https://github.com/farpointer)"

    def _station_url(self) -> str:
        return f"{SPINITRON_BASE}/{self.station}"

    def _find_playlist_links(self, show_name: str) -> list[tuple[str, str]]:
        """Return [(playlist_id, href), ...] for show_name on the station page."""
        resp = self.session.get(self._station_url(), timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        slug = show_name.replace(" ", "-")
        pattern = re.compile(
            rf"/{re.escape(self.station)}/pl/(\d+)/.*{re.escape(slug)}.*",
            re.IGNORECASE,
        )

        results = []
        for a in soup.find_all("a", href=pattern):
            m = pattern.match(a["href"])
            if m:
                results.append((m.group(1), a["href"]))
        return results

    def get_latest_playlist(self, show_name: str) -> Playlist:
        links = self._find_playlist_links(show_name)
        if not links:
            raise ValueError(f"No playlists found for '{show_name}' on {self.station}")
        playlist_id, href = links[0]
        return self._fetch_playlist(playlist_id, href)

    def get_playlist_by_date(self, show_name: str, show_date: date) -> Playlist:
        links = self._find_playlist_links(show_name)
        for playlist_id, href in links:
            pl = self._fetch_playlist(playlist_id, href)
            if pl.start_time.date() == show_date:
                return pl
        raise ValueError(
            f"No playlist found for '{show_name}' on {show_date} at {self.station}"
        )

    def _fetch_playlist(self, playlist_id: str, href: str) -> Playlist:
        url = f"{SPINITRON_BASE}{href}"
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        return _parse_playlist_page(soup, playlist_id)


def _parse_playlist_page(soup: BeautifulSoup, playlist_id: str) -> Playlist:
    """Parse a Spinitron playlist HTML page into a Playlist dataclass."""

    # --- Title ---
    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "Convergence Zone"

    # --- Playlist start/end times ---
    # Spinitron embeds times in <time> tags with datetime attributes
    time_tags = soup.find_all("time")
    datetimes = []
    for t in time_tags:
        dt_str = t.get("datetime", "")
        if dt_str:
            try:
                datetimes.append(dateutil_parser.parse(dt_str))
            except ValueError:
                pass

    if len(datetimes) >= 2:
        start_time = _to_pacific(datetimes[0])
        end_time = _to_pacific(datetimes[1])
    elif len(datetimes) == 1:
        start_time = _to_pacific(datetimes[0])
        end_time = start_time
    else:
        # Fallback: use today midnight Pacific
        start_time = datetime.now(PACIFIC).replace(hour=20, minute=30, second=0, microsecond=0)
        end_time = start_time

    # --- Spins ---
    spins: list[Spin] = []

    # Spinitron spin rows are typically <div class="spin"> or <tr> with spin data
    spin_divs = soup.select(".spin-item, .spin, tr.spin")
    for div in spin_divs:
        artist = _text(div, ".artist, .spin-artist, td.artist")
        song = _text(div, ".song, .spin-song, td.song")
        album = _text(div, ".release, .spin-release, td.release") or ""

        # Time for this spin
        time_tag = div.find("time")
        if time_tag and time_tag.get("datetime"):
            try:
                spin_dt = _to_pacific(dateutil_parser.parse(time_tag["datetime"]))
            except ValueError:
                spin_dt = start_time
        else:
            spin_dt = start_time

        if artist or song:
            spins.append(Spin(artist=artist, song=song, album=album, start_time=spin_dt))

    return Playlist(
        id=playlist_id,
        title=title,
        start_time=start_time,
        end_time=end_time,
        spins=spins,
    )


def _text(tag, selector: str) -> str:
    """Find first matching selector in tag and return stripped text."""
    for sel in selector.split(", "):
        found = tag.select_one(sel.strip())
        if found:
            return found.get_text(strip=True)
    return ""


def _to_pacific(dt: datetime) -> datetime:
    """Convert a datetime to America/Los_Angeles, attaching UTC if naive."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(PACIFIC)


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

class APISpintronClient:
    """Fetch playlist data from the Spinitron REST API."""

    def __init__(self, station: str, api_key: str):
        self.station = station
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "czarchive/0.1",
        })

    def _get(self, endpoint: str, **params) -> dict:
        resp = self.session.get(f"{SPINITRON_API}/{endpoint}", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def get_latest_playlist(self, show_name: str) -> Playlist:
        data = self._get("playlists", station=self.station, count=20)
        for item in data.get("items", []):
            if show_name.lower() in item.get("title", "").lower():
                return self._build_playlist(item)
        raise ValueError(f"No playlists found for '{show_name}'")

    def get_playlist_by_date(self, show_name: str, show_date: date) -> Playlist:
        data = self._get("playlists", station=self.station, count=50)
        for item in data.get("items", []):
            if show_name.lower() not in item.get("title", "").lower():
                continue
            start = _to_pacific(dateutil_parser.parse(item["start"]))
            if start.date() == show_date:
                return self._build_playlist(item)
        raise ValueError(f"No playlist for '{show_name}' on {show_date}")

    def _build_playlist(self, item: dict) -> Playlist:
        playlist_id = str(item["id"])
        start_time = _to_pacific(dateutil_parser.parse(item["start"]))
        end_time = _to_pacific(dateutil_parser.parse(item["end"]))

        spins_data = self._get("spins", playlist_id=playlist_id, count=200)
        spins = []
        for s in spins_data.get("items", []):
            spin_dt = _to_pacific(dateutil_parser.parse(s["start"]))
            spins.append(Spin(
                artist=s.get("artist", ""),
                song=s.get("song", ""),
                album=s.get("release", ""),
                start_time=spin_dt,
            ))

        return Playlist(
            id=playlist_id,
            title=item.get("title", "Convergence Zone"),
            start_time=start_time,
            end_time=end_time,
            spins=spins,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_spinitron_client(config) -> SpintronClient:
    """Return API client if key is set, otherwise scraping client."""
    if config.spinitron_api_key:
        return APISpintronClient(config.station, config.spinitron_api_key)
    return ScrapingSpintronClient(config.station)
