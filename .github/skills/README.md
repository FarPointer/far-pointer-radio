# Skills

Repository-specific agent skills. Each is a directory with a `SKILL.md` carrying YAML
frontmatter (`name`, `description`) — the format GitHub Copilot and Claude Code both read.

These target the recurring loops in this repository, not generic coding.

| Skill | Use when |
|---|---|
| `cz-cache-rebuild/` | A new episode aired, or a playlist source changed, and the cache needs rebuilding and verifying |
| `cz-override-review/` | Descriptions, host attribution, repeats, or duplicate spins need a human decision recorded |
| `cz-publish-playlist/` | A playlist post on convergencezone.fm needs creating or updating, or a Mixcloud link needs backfilling |
| `cz-code-review/` | Reviewing a change before or during a pull request, against this repository's specific failure modes |
| `decision-record/` | A session settled a question and the outcome needs to be checked in |
| `episode-prep/` | Assembling the show-night packet — repeat avoidance, local coverage, outstanding gaps |
| `cz-spinitron-edit/` | Bulk or targeted edits to Spinitron playlist or show metadata via Playwright MCP |

## Boundaries between them

The split is deliberate: `cz-cache-rebuild` never edits an override, and
`cz-override-review` never decides one. Rebuilding is mechanical and safe to do
unattended; approving a description is a judgement that reaches the public site and
happens with the user present, one item at a time.

`cz-code-review` is read-only and reviews; it never fixes what it finds. It is aimed at
this repository's characteristic failure — a feature that ships documented, with a worked
example, and does nothing — which a generic reviewer has no reason to look for.

## Adding one

Keep them about *this* repository. A skill that could apply to any codebase belongs in the
personal skill directory, not here. State what the skill must **not** do as explicitly as
what it does — the failure modes in this repository are quiet ones, and a skill that only
lists happy paths will walk straight into them.
