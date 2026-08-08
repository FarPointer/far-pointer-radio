#!/bin/sh
# PostToolUse hook: lint-fix the Python file that was just written.
#
# Style is not worth a conversation. Keeping the safe fixes automatic is what makes
# `make lint` a real gate for new code instead of a backlog.
#
# Deliberately `check --fix` and NOT `ruff format`: this codebase was never
# formatter-managed and uses deliberate hanging indents in the loaders. A wholesale
# reformat would bury a real change in churn. `make format` exists for when that is
# actually wanted, as a separate, deliberate commit.
set -eu

path="${1:-}"
case "$path" in
    *.py) ;;
    *) exit 0 ;;
esac
case "$path" in
    */tools/python/*|tools/python/*) ;;
    *) exit 0 ;;
esac

command -v uvx >/dev/null 2>&1 || exit 0

root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$root/tools/python" || exit 0

uvx ruff check --fix "$path" 2>&1 || true
exit 0
