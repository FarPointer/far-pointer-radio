"""Filesystem locations and the small set of constants shared across the build.

Everything is derived from this file's own location so the build works from any cwd,
and so a checkout in a different directory needs no configuration.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

SHOW = REPO / "shows/convergence-zone"
SOURCES = SHOW / "playlists/sources"

# The Spinitron export. The older Spinssearchresults84208326forKSER.csv covers the same
# spins but lacks DJ ID, Playlist Date-time, and Playlist Duration, so it cannot
# distinguish the two personas that both display as "Jim Causey". Kept in the repo as an
# archived export; nothing here reads it.
SPINS_CSV = SOURCES / "spinitron" / "Spins-search-results-12-5-19-8-4-26-for-KSER.csv"
SPINITRON_PLAYLISTS = SOURCES / "spinitron" / "convergence-zone-playlists.json"

MICHAELG_DIR = SOURCES / "michaelg"
CZFM_DIR = SOURCES / "convergencezone.fm"
ONENOTE_DIR = SOURCES / "farpointer-onenote"

CACHE = SHOW / "playlists/cache"
BROADCASTS = CACHE / "broadcasts"
INDEX = CACHE / "index.json"
PUBLICATION_LINKS = SHOW / "playlists/publication-links.json"

REPORTS = HERE / "reports"
OVERRIDES = HERE / "overrides"

# czaudit owns the matching primitives; importing beats reimplementing them, because a
# divergence there would let the cache and the audit disagree about what matched.
CZAUDIT = REPO / "tools/python/czaudit"

SHOW_NAME = "Convergence Zone"

# Spinitron personas. Both "Jim Causey" entries are Jim's own accounts (confirmed by
# Jim); 174269 is a second account he created, first seen 2024-10-08. This mapping is
# login provenance only and is deliberately NOT used to attribute hosts -- see
# merge.derive_participants.
DJ_NAMES = {
    "173567": "Jim Causey",
    "174269": "Jim Causey",
    "189849": "MichaelG",
}

HOST_JIM = "Jim Causey"
HOST_MICHAELG = "MichaelG"
