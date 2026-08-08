---
name: decision-record
description: Write up what a session decided, and why, as a checked-in document. Use at the end of an exploratory session, or when asked to "summarize what you've done", "write this up so I can switch models", or "document what needs to be done".
---

# Writing a decision record

Chat history is not storage. When a session settles a question — an architecture, a
schema, a set of overrides, a plan — the outcome belongs in a checked-in markdown file
that can be read six months later without re-deriving it from the evidence.

`shows/convergence-zone/docs/playlist-cache-review-session.md` is the model. Read it before
writing one.

## Where it goes

| Scope | Location |
|---|---|
| One show | `shows/<show>/docs/` |
| Repository-wide (workflow, tooling, conventions) | `docs/` |

kebab-case filename, descriptive rather than dated: `playlist-publishing-plan.md`, not
`2026-08-05-notes.md`.

## What it must contain

1. **Header** — date, branch, and a one-line statement of purpose. Say plainly what the
   document is *for*: "so the decisions are auditable later without re-deriving them from
   the evidence."

2. **Where this picks up** — the state of the world when the session started, and what
   came before. Someone reading cold needs the entry point.

3. **What was decided** — each decision, and the reasoning. Not just the conclusion.

4. **What was decided *against* the evidence.** This is the part that gets dropped and the
   part that matters most. If a call was made on judgement that the data did not support,
   name it, and say why. It stays visible so it can be revisited.

5. **What was rejected, and why.** Including approaches that were built and abandoned.

6. **What is still open** — as a list someone can act on. If it is a plan, give the
   required order and say which items are tooling, which are process, and which are
   documentation.

7. **Bugs found along the way**, especially ones where something documented turned out to
   do nothing. Those are the expensive class: they look like working features.

## Style

- Prose, not bullet soup. Explain, do not list.
- Concrete numbers, and where they came from. "took proposed descriptions from 21 to 35"
  beats "improved extraction".
- Quote the user's own framing where it settled something.
- Tables for anything with a repeating shape — deliverables, files, decisions.
- No time or effort estimates unless the user asked for them.

## Superseded work

If the session replaced an earlier approach, move the earlier artifacts to `discarded/`
rather than deleting them — a subdirectory with its own `README.md` naming what replaced
it and why. Update `discarded/README.md`'s table. The history is the point; the code is
not.

Say so explicitly in the new document: "**Status:** Active plan. This replaces the
custom-post-type/plugin/child-theme approach archived under
`discarded/playlist-cpt-automation/`."

## Then

Show the file. Do not commit, push, or open a PR unless asked — and if asked, scope the
commit to the files this session touched, not to whatever else was already in the tree.
