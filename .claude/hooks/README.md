# Claude Code hooks

Shell hooks wired into `.claude/settings.json`. All are POSIX `sh` — no bashisms — so they
run the same on macOS and Linux.

| Hook | Event | Behaviour |
|---|---|---|
| `session-start.sh` | `SessionStart` | Prints the branch, whether the tree is dirty, and unpushed commit count. Answers "did you already merge that?" before it has to be asked. |
| `pre-commit-secret-scan.sh` | `PreToolUse` on `git commit` | **Blocks** (exit 2) if a staged path is a credential file or a staged line looks like a hard-coded key. |
| `overrides-guard.sh` | `PreToolUse` on writes to `czcache/overrides/*.yaml` | Advisory. Reminds that those files record human decisions and must not be batch-applied. |
| `format-python.sh` | `PostToolUse` on `tools/python/**/*.py` | Runs `ruff check --fix`. Not `ruff format` — see the comment in the script. |
| `verify-reminder.sh` | `Stop` | If the cache or its inputs changed and nothing verified them, says so. |

Only the secret scan blocks. The rest are advisory on purpose: a guard that cries wolf is a
guard that gets disabled.

GitHub Copilot has no equivalent hook surface, so the same intent is written as rules in
`AGENTS.md` ("How I work", "Data safety") and enforced in CI by
`.github/workflows/verify-cache.yml`.

## Testing a hook

```sh
sh .claude/hooks/session-start.sh
sh .claude/hooks/overrides-guard.sh tools/python/czcache/overrides/descriptions.yaml
git add -A && sh .claude/hooks/pre-commit-secret-scan.sh; echo "exit $?"
```
