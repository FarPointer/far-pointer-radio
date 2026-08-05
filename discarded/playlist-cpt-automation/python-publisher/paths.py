"""Discarded filesystem layout from the czpublish prototype.

Mirrors tools/python/czcache/paths.py's approach: everything derived from
this file's own location so the tool works from any cwd.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]

SHOW = REPO / "shows/convergence-zone"
CACHE = SHOW / "playlists/cache"
BROADCASTS = CACHE / "broadcasts"

# Local secret, gitignored — see shows/convergence-zone/playlists/.gitignore.
# Contains the WordPress application-password credentials, never committed.
WORDPRESS_APP_PASSWORD_FILE = SHOW / "playlists/.wordpress-app-password.local.txt"
