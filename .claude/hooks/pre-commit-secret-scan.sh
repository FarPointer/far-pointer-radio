#!/bin/sh
# PreToolUse guard on `git commit`.
#
# .gitignore covers the common cases but is not a substitute for looking. This blocks the
# commit outright if a staged file is one that must never enter the repository, or if a
# staged diff looks like a credential.
#
# Exit 0 = allow. Exit 2 = block, and the message on stderr is shown to the agent.
set -eu

staged=$(git diff --cached --name-only 2>/dev/null || true)
[ -z "$staged" ] && exit 0

fail() {
    echo "BLOCKED: $1" >&2
    echo "Remove it from the index (git restore --staged <path>) before committing." >&2
    exit 2
}

# Paths that are never committable, regardless of what .gitignore currently says.
for f in $staged; do
    case "$f" in
        .env|.env.*)
            [ "$f" = ".env.example" ] || fail "$f is an environment file"
            ;;
        *.czarchive.toml|.czarchive.toml)
            case "$f" in
                *.example) ;;
                *) fail "$f holds Spinitron and Mixcloud credentials" ;;
            esac
            ;;
        cookie.txt|*/cookie.txt)
            fail "$f is a session cookie"
            ;;
        *.pem|*.key|*.p12|*.pfx|credentials.json|api_keys.txt)
            fail "$f looks like a credential file"
            ;;
    esac
done

# Content scan of the staged diff. Deliberately narrow -- a noisy guard gets ignored.
if git diff --cached -U0 | grep -nEi \
    '^\+.*(spinitron[_-]?api[_-]?key|mixcloud[_-]?(client[_-]?)?secret|oauth[_-]?token|access[_-]?token|api[_-]?key)[[:space:]]*[:=][[:space:]]*["'"'"']?[A-Za-z0-9_\-]{16,}' \
    >/dev/null 2>&1; then
    echo "BLOCKED: a staged line looks like a hard-coded credential." >&2
    echo "Credentials belong in ~/.czarchive.toml or the environment, never in the repo." >&2
    exit 2
fi

exit 0
