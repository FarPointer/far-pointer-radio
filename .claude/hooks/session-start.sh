#!/bin/sh
# SessionStart hook: state the branch and whether the tree is dirty.
#
# "did you already merge that? If not, don't do it" has been asked more than once. The
# answer should be on screen before the first tool call, not reconstructed later.
set -eu

cd "$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
ahead=$(git rev-list --count "@{upstream}..HEAD" 2>/dev/null || echo "0")

echo "branch: $branch"
if [ "$dirty" != "0" ]; then
    echo "working tree: $dirty uncommitted path(s) -- these predate this session"
else
    echo "working tree: clean"
fi
[ "$ahead" != "0" ] && echo "unpushed commits: $ahead"

echo "Do not commit, push, or open a PR unless asked. See AGENTS.md."
exit 0
