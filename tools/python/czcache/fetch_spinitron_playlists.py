"""Snapshot the public Spinitron playlist history for Convergence Zone.

The spin-search CSV has playlist timestamps but not playlist IDs. Spinitron's
public show page exposes the IDs in playlist URLs and paginates through the
complete history, so this fetch is independent of a station API key.

Run explicitly before `build.py`; the cache build itself stays offline and
deterministic against the checked-in snapshot.
"""
import datetime as dt
import json
import re
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from paths import SPINITRON_PLAYLISTS

SHOW_URL = "https://spinitron.com/KSER/show/260646/Convergence-Zone"
PACIFIC = ZoneInfo("America/Los_Angeles")
USER_AGENT = "czcache/0.1 (+https://github.com/FarPointer/far-pointer-radio)"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def parse_start(text):
    start = text.replace("\xa0", " ").split("–", 1)[0].strip()
    parsed = dt.datetime.strptime(start, "%b %d, %Y %I:%M %p")
    return parsed.replace(tzinfo=PACIFIC).strftime("%Y-%m-%dT%H:%M:%S%z")


def load_all():
    url = SHOW_URL
    playlists = {}
    while url:
        soup = BeautifulSoup(fetch(url), "lxml")
        for item in soup.select(".playlist-list .list-item"):
            link = item.select_one('a[href*="/KSER/pl/"]')
            timeslot = item.select_one(".timeslot")
            if not link or not timeslot:
                continue
            match = re.search(r"/KSER/pl/(\d+)/", link.get("href", ""))
            if not match:
                continue
            playlist_id = match.group(1)
            playlists[playlist_id] = {
                "id": playlist_id,
                "start": parse_start(timeslot.get_text(" ", strip=True)),
                "url": urllib.parse.urljoin(SHOW_URL, link["href"]),
            }

        pager = soup.select_one(".infpager_next")
        if not pager or pager.get("data-has-more") != "1":
            url = None
        else:
            url = urllib.parse.urljoin(SHOW_URL, pager["data-url"])

    return sorted(playlists.values(), key=lambda p: (p["start"], int(p["id"])))


def main():
    data = {"show_url": SHOW_URL, "playlists": load_all()}
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    temporary = SPINITRON_PLAYLISTS.with_suffix(".json.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(SPINITRON_PLAYLISTS)
    print(f"{len(data['playlists'])} playlists -> {SPINITRON_PLAYLISTS}")


if __name__ == "__main__":
    main()
