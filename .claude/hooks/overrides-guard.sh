#!/bin/sh
# PreToolUse guard on writes to tools/python/czcache/overrides/*.yaml.
#
# Those four files are the only place a human decision enters the build: an approved
# description, a host attribution, a forced or suppressed repeat, a merged duplicate.
# Everything else in the cache is derived. An agent writing them on its own judgement
# would launder a guess into the record — and the site publishes approved descriptions.
#
# This does not block. It reminds, because the legitimate case (the human said yes, item
# by item) is common. Exit 0 with a message on stdout is advisory.
set -eu

path="${1:-}"
case "$path" in
    *czcache/overrides/*.yaml) ;;
    *) exit 0 ;;
esac

cat >&2 <<'EOF'
NOTE: this file records a HUMAN decision, not an inference.

  - descriptions.yaml   approved blurb text, or `skip`. Nothing reaches
                        description_status "approved" any other way, and approved text
                        is what the site publishes.
  - participants.yaml   host attribution where the workbook rule is wrong
  - repeats.yaml        force or suppress a repeat pairing
  - spins.yaml          merge a same-persona duplicate

Write an entry only if the user approved that specific item in this session. Review them
one at a time; do not batch-apply. After writing, rebuild and verify -- an override that
silently does nothing has happened before:

    cd tools/python && make check
EOF
exit 0
