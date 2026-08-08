#!/bin/sh
# Stop hook: if the cache or its inputs changed but nothing verified them, say so.
#
# `verify.py` is the only thing that can tell "the gate holds" from "the gate is not
# wired up". Ending a session with an unverified cache is how the description review gate
# reported PASS for weeks while doing nothing.
set -eu

cd "$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0

changed=$(git status --porcelain -- \
    shows/convergence-zone/playlists/cache \
    shows/convergence-zone/playlists/sources \
    tools/python/czcache 2>/dev/null || true)

[ -z "$changed" ] && exit 0

echo "REMINDER: the playlist cache or its inputs changed in this session." >&2
echo "Run 'cd tools/python && make check' before committing -- it rebuilds, verifies," >&2
echo "and asserts the cache diff is what you intended." >&2
exit 0
