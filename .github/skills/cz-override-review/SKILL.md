---
name: cz-override-review
description: Walk the Convergence Zone playlist cache override decisions with the user, one item at a time. Use when asked to "review descriptions", "approve blurbs", "review participants/hosts", "review repeats", or "review duplicate spins".
---

# Reviewing playlist cache overrides

`tools/python/czcache/overrides/` is the only place a human decision enters the build.
Everything else in the cache is derived from the sources. These four files are what the
build cannot know:

| File | Decides |
|---|---|
| `descriptions.yaml` | Approved blurb text, or `skip`. Nothing reaches `description_status: "approved"` any other way, and approved text is what the site publishes. |
| `participants.yaml` | Host attribution where the workbook rule is wrong or a show was co-hosted |
| `repeats.yaml` | Force or suppress a repeat pairing the 0.60 threshold got wrong |
| `spins.yaml` | Merge a same-persona duplicate the build deliberately left alone |

## The one rule

**Ask item by item. Never batch-apply.** The user has asked for this explicitly. Present
one item, get an answer, write it, move on. Do not present twenty items and a proposed
YAML block.

You are a transcriber here, not a judge. Propose nothing as approved on your own
assessment. A `proposed` description is the build's guess; only a person turns it into
`approved`.

## Steps

1. **Build first**, so the reports reflect the current sources:

   ```sh
   cd tools/python && make build
   ```

2. **Read the relevant report** in `tools/python/czcache/reports/` (gitignored, regenerated
   every build):

   | Reviewing | Read |
   |---|---|
   | Descriptions | `descriptions-review.md` — each proposed description **and the text that was rejected** |
   | Hosts | `attribution.md` — persona × workbook cross-tab, and the broadcasts that break the alternation |
   | Repeats | `repeats.md` — clusters, chosen originals, and every pair scoring 0.40–0.95 |
   | Duplicate spins | `discrepancies.md` — merged and flagged duplicates |

3. **For each item, present:**
   - The broadcast date and episode number.
   - The proposed value, quoted in full.
   - The **evidence against it** — for a description, the rejected text; for a repeat, the
     score and the other candidates; for attribution, what the workbook rule inferred.
   - The options: approve as-is / approve with edits / `skip` / leave undecided.

   Then wait.

4. **Write only what was approved**, keyed by air date. Both `2026-07-07:` and
   `"2026-07-07":` work — the loader normalises `datetime.date` and `str` keys alike, and
   it does that because forgetting the quotes once made every entry silently miss.

5. **Prove the decision took effect:**

   ```sh
   cd tools/python && make check
   ```

   `verify.py` gates each override file so an inert entry cannot pass silently:
   the approved set must equal the descriptions file exactly, every `participants.yaml`
   entry must appear verbatim in the cache, every forced repeat must be linked, every
   suppressed one gone, and every `merge_duplicates` entry must have left exactly one
   logged spin.

   **If the cache did not change, the override did not fire.** That is a bug or a wrong
   key, not something to shrug at — say so and investigate. This exact failure hid for
   weeks: the gate reported PASS the whole time because the file was empty, and the check
   could not distinguish "the gate holds" from "the gate is not wired up."

6. **Record the session.** When the review settles non-obvious calls — especially any made
   *against* the evidence — write them up. Use the `decision-record` skill;
   `shows/convergence-zone/docs/playlist-cache-review-session.md` is the model.

## Context worth having before you start

- **`dj_ids` is not host attribution.** Two Spinitron personas display the identical name
  "Jim Causey" (173567 is the original account, 174269 a second one), and 26 of MichaelG's
  28 episodes were logged under Jim's original account. Hosts come from workbook presence
  and this override file.
- **Repeats form chains.** Episode 021 aired four times. Clustering resolves each airing to
  the *original*, never to the previous airing.
- **A forced spin merge matches on normalised artist and song**, so an override written
  against the plain title still catches a re-log that drifted it —
  `"Deep Mindset (Original Mix)"` vs `"Deep Mindset"`.

## Do not

- Approve, edit, or invent description text.
- Write an entry the user did not explicitly approve in this session.
- Commit `reports/`.
- Commit, push, or open a PR unless asked.
