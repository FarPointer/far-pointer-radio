---
name: repo-config-audit
description: Audit this repository's instructions, agents, skills, and related workflow setup when the user asks for changes to repo configuration, agent setup, skill setup, prompts, hooks, or overall workflow. Use for prompts like "recommend changes to my repo configuration", "improve my agent setup", "audit our skills", or "what repo-level instructions should change?"
---

# Repo configuration audit

Use this skill when the user wants recommendations about how the repository is configured
for agent work. The point is to inspect the real setup first and return a short,
evidence-backed set of changes — not generic prompt-engineering advice.

## Read first

1. `AGENTS.md`
2. Relevant `.github/instructions/*.instructions.md`
3. `.github/skills/README.md` and any skills implicated by the request
4. `.github/agents/` if the request mentions agents or role prompts
5. `README.md`, `CONTRIBUTING.md`, and `docs/operating-procedures.md` if they affect the
   workflow being discussed

If the request is about Claude setup rather than just repo files, also inspect the live
`~/.claude` layout the repo relies on: `settings.json`, symlink targets, hooks, scripts,
and skill directories.

## What to look for

- Guidance gaps that force the same correction in multiple sessions
- Skills whose descriptions do not match the language the user actually uses
- Repo-level instruction that belongs in `AGENTS.md` versus path-scoped instruction files
- Overlap between agents, skills, and standing instructions
- Permission-denial loops, plan-mode drift, or advisory requests that become edits too early
- Checked-in setup that has drifted away from the live `~/.claude` configuration the user
  is actually running

## Rules

- Recommendation requests stay in recommendation mode unless the user explicitly asks to
  implement the changes.
- Prefer fixing an existing instruction, skill description, or agent brief over adding a
  new generic artifact.
- Name the exact file(s) that should change.
- Use concrete evidence from recent sessions when available.
- Keep the result short. Two to five high-leverage changes are better than a long backlog.

## Deliverable

Return:

1. The highest-leverage repo/config changes
2. Why each one matters, with evidence
3. The exact files to edit
4. Draft text or structure for the proposed change whenever possible

If the user then asks to implement the recommendations, make the repo changes surgically
and update adjacent docs when the instruction routing changes.
