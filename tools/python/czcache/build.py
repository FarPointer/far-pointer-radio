"""Build the whole playlist cache. One command, no arguments.

    uv run --with openpyxl --with beautifulsoup4 --with lxml --with pyyaml python build.py

Order matters: repeats are found first, because a repeat of a MichaelG episode is class A
even though it has no workbook of its own, and classification depends on knowing that.
"""
import argparse
import collections
import datetime as dt
import json
import pathlib
import sys

import yaml

import emit
import load_instagram
import load_prose
import load_setlists
import load_spinitron
import load_workbooks
import merge
import repeats
from paths import CACHE, OVERRIDES, PUBLICATION_LINKS, REPORTS


def load_overrides():
    """Checked-in human decisions. Absent or empty files are fine."""
    def read(name, default):
        path = OVERRIDES / name
        if not path.exists():
            return default
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return default if data is None else data

    def by_date(name):
        """Normalise keys to ISO strings.

        The files are documented as keyed by air date, and `2026-07-07:` is the obvious
        way to write that -- but YAML resolves an unquoted ISO date to a datetime.date,
        so every lookup against a string id missed and the override silently did nothing.
        Accept both forms rather than making correctness depend on remembering quotes.
        """
        data = read(name, {})
        return {(k.isoformat() if isinstance(k, dt.date) else str(k)): v
                for k, v in data.items()}

    publication_links = {}
    if PUBLICATION_LINKS.exists():
        publication_links = json.loads(PUBLICATION_LINKS.read_text(encoding="utf-8"))

    return {
        "descriptions": by_date("descriptions.yaml"),
        "participants": by_date("participants.yaml"),
        "repeats": read("repeats.yaml", {}) or {},
        "spins": read("spins.yaml", {}) or {},
        "publication_links": publication_links,
    }


def choose_prose_candidates(onenote, instagram):
    """Pick one candidate per date; keep all for review output.

    Highest score wins, with OneNote winning ties for continuity with historical builds.
    """
    by_date = collections.defaultdict(list)
    for date, p in (onenote or {}).items():
        q = dict(p)
        q["source"] = "onenote"
        by_date[date].append(q)
    for date, p in (instagram or {}).items():
        q = dict(p)
        q["source"] = "instagram"
        by_date[date].append(q)

    chosen = {}
    for date, candidates in by_date.items():
        with_text = [p for p in candidates if p.get("candidate")]
        if not with_text:
            continue
        chosen[date] = max(
            with_text,
            key=lambda p: (p.get("score", 0), 1 if p.get("source") == "onenote" else 0),
        )
    return chosen, by_date


def main(cache_root=None, quiet=False):
    ov = load_overrides()

    broadcasts, merges, flagged = load_spinitron.load(
        (ov["spins"] or {}).get("merge_duplicates") or [])
    workbooks = load_workbooks.load()
    setlists = load_setlists.load()

    rep_ov = ov["repeats"] or {}
    scored, clusters = repeats.assign(
        broadcasts,
        forced=[tuple(p) for p in (rep_ov.get("forced") or [])],
        suppressed=[tuple(p) for p in (rep_ov.get("suppressed") or [])],
    )

    bindings = load_setlists.bind(setlists, broadcasts)
    classes = merge.classify(broadcasts, workbooks, bindings, clusters)
    broadcast_dates = {b["date"] for b in broadcasts.values()}
    prose_onenote = load_prose.load(broadcast_dates)
    prose_instagram = load_instagram.load(broadcast_dates)
    prose, prose_review = choose_prose_candidates(prose_onenote, prose_instagram)

    # For a repeat of a MichaelG episode, the canonical track list is the ORIGINAL's
    # workbook -- the repeat has none of its own.
    workbook_for = {}
    for bid, b in broadcasts.items():
        date = b["date"]
        if date in workbooks:
            workbook_for[bid] = workbooks[date]
        elif b.get("first_broadcast_id"):
            orig_date = broadcasts[b["first_broadcast_id"]]["date"]
            if orig_date in workbooks:
                workbook_for[bid] = workbooks[orig_date]

    report = collections.defaultdict(list)
    out, description_review = {}, []
    for bid in sorted(broadcasts):
        b = broadcasts[bid]
        klass = classes[bid]
        p = prose.get(b["date"])
        bc = merge.build_broadcast(
            bid, b, klass, workbook_for.get(bid),
            setlists.get(bindings[bid]["setlist"]) if klass == "B" else None,
            p, ov, report,
        )
        bc["_class"] = klass
        out[bid] = bc
        for entry in prose_review.get(b["date"], []):
            if not (entry.get("candidate") or entry.get("rejected")):
                continue
            status = "not used"
            if bc["description_status"] == "approved":
                status = "approved override"
            elif p is entry and bc["description_status"] == "proposed":
                status = "proposed"
            description_review.append({
                "date": b["date"],
                "source": entry.get("source", "unknown"),
                "file": entry.get("file", ""),
                "score": entry.get("score", 0.0),
                "candidate": entry.get("candidate"),
                "rejected": entry.get("rejected"),
                "permalink": entry.get("permalink", ""),
                "status": status,
            })

    # --- attribution cross-tab -------------------------------------------------
    tab = collections.Counter()
    exceptions = []
    for bid, b in broadcasts.items():
        has_wb = bid in workbook_for
        key = ("+".join(b["dj_ids"]), "yes" if has_wb else "no")
        tab[key] += 1
        alternating_era = b["date"] >= "2025-07-15"
        expected_mg = "173567" in b["dj_ids"] and "174269" not in b["dj_ids"]
        if alternating_era and has_wb != expected_mg:
            exceptions.append({
                "date": b["date"], "dj_ids": "+".join(b["dj_ids"]),
                "has_workbook": "yes" if has_wb else "no",
                "attributed_to": ", ".join(p["name"] for p in out[bid]["participants"]),
            })
    attribution_rows = [{"dj_ids": k[0], "has_workbook": k[1], "broadcasts": n}
                        for k, n in sorted(tab.items())]

    index = emit.write_cache(out, root=cache_root)

    counts = collections.Counter(classes.values())
    spins = sum(len(b["spins"]) for b in out.values())
    evidence = collections.Counter(s["evidence"] for b in out.values() for s in b["spins"])
    localc = collections.Counter(
        str(s["local"]) for b in out.values() for s in b["spins"])
    basis = collections.Counter(
        x for b in out.values() for s in b["spins"] for x in s["local_basis"])
    desc = collections.Counter(b["description_status"] for b in out.values())

    summary = f"""# Build summary

Generated {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}.

| | |
|---|---|
| Broadcasts | {len(out)} |
| Spins | {spins} |
| Spinitron rows read | {spins - evidence['planned'] - report_len(report, 'workbook_only')} logged from Spinitron |

## Classes

| Class | Canonical source | Broadcasts |
|---|---|---|
| A | MichaelG workbook (+ repeats of one) | {counts['A']} |
| B | Set list merged with Spinitron | {counts['B']} |
| C | Spinitron alone | {counts['C']} |

## Spin evidence

{dict(evidence)}

## Locality

resolved: {dict(localc)}
basis counts: {dict(basis)}

## Descriptions

{dict(desc)}

## Repeats

{len(clusters)} clusters, {sum(len(v) for v in clusters.values())} repeat airings.

## Reports

- `discrepancies.md` — field conflicts, merged and flagged duplicates
- `repeats.md` — clusters and the 0.40–0.95 review band
- `attribution.md` — persona vs workbook cross-tab
- `unmatched.md` — planned-only, workbook-only, Spinitron-only tracks
- `descriptions-review.md` — proposed descriptions and rejected remainders
"""

    # Reports describe the build, not the cache, so a throwaway determinism build has no
    # business rewriting them -- and the summary carries a timestamp, which would make
    # any two builds differ by construction.
    if cache_root is None:
        emit.write_reports({
            "report": report, "merges": merges, "flagged": flagged,
            "clusters": clusters, "scored": scored, "broadcasts_raw": broadcasts,
            "attribution_rows": attribution_rows, "attribution_exceptions": exceptions,
            "description_review": sorted(description_review, key=lambda d: d["date"]),
            "summary": summary,
        })

    if not quiet:
        print(f"broadcasts {len(out)}   spins {spins}   "
              f"A/B/C {counts['A']}/{counts['B']}/{counts['C']}")
        print(f"evidence {dict(evidence)}")
        print(f"descriptions {dict(desc)}")
        print(f"cache   -> {cache_root or CACHE}")
        print(f"reports -> {REPORTS}")
    return 0


def report_len(report, key):
    return len(report.get(key, []))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", metavar="DIR", type=pathlib.Path,
                    help="write the cache here instead of playlists/cache/, and skip "
                         "the reports. Used by verify.py to build twice and compare.")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    sys.exit(main(cache_root=args.out, quiet=args.quiet))
