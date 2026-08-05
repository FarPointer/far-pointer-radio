"""Check the built cache against the invariants the build is supposed to guarantee.

Run after build.py. Every check either passes or prints what it found; the exit code is
non-zero if any failed, so this works as a pre-commit gate.

These are not unit tests of the loaders -- they are assertions about the *output*, which
is what actually has to be right. Several encode facts that were measured from the
sources during design (3,282 Spinitron rows, 7 cross-persona merges, 28 workbooks), so a
source file changing underneath the build shows up here rather than silently.
"""
import collections
import csv
import json
import re
import subprocess
import sys

import yaml

from paths import BROADCASTS, INDEX, MICHAELG_DIR, OVERRIDES, REPO, SPINS_CSV

FAILURES = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def load_cache():
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(BROADCASTS.glob("*.json"))]


def main():
    bcs = load_cache()
    by_id = {b["id"]: b for b in bcs}
    spins = [s for b in bcs for s in b["spins"]]

    # 1 -----------------------------------------------------------------
    r = subprocess.run(["git", "diff", "--stat", "--", "shows/convergence-zone/playlists/cache/"],
                       cwd=REPO, capture_output=True, text=True)
    tracked = subprocess.run(["git", "ls-files", "shows/convergence-zone/playlists/cache/"],
                             cwd=REPO, capture_output=True, text=True).stdout.strip()
    if not tracked:
        check("1 determinism (cache not yet committed; rerun after first commit)", True,
              "nothing tracked yet, so there is no baseline to diff against")
    else:
        check("1 determinism: rebuild produces no diff", r.stdout.strip() == "",
              r.stdout.strip()[:400])

    # 2 -----------------------------------------------------------------
    with open(SPINS_CSV, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    logged = [s for s in spins if "spinitron" in s["sources"]]
    check("2 conservation: 164 broadcast files", len(bcs) == 164, f"found {len(bcs)}")
    # 7 cross-persona pairs merge automatically; each reviewed entry in spins.yaml merges
    # one more. Derived rather than hardcoded so an approved decision does not read as a
    # regression -- but still exact, so an unexplained loss of rows does.
    forced = len((yaml.safe_load((OVERRIDES / "spins.yaml").read_text(encoding="utf-8"))
                  or {}).get("merge_duplicates") or [])
    expected = len(rows) - 7 - forced
    check("2 conservation: Spinitron rows accounted for",
          len(logged) == expected,
          f"{len(rows)} rows - 7 persona merges - {forced} reviewed = {expected}; "
          f"cache has {len(logged)}")
    classes = collections.Counter(json.loads(INDEX.read_text())[i]["class"]
                                 for i in range(len(bcs)))
    check("2 conservation: class split 31/70/63",
          (classes["A"], classes["B"], classes["C"]) == (31, 70, 63), str(dict(classes)))
    check("2 conservation: id equals air_datetime verbatim",
          all(b["id"] == b["air_datetime"] for b in bcs))
    check("2 conservation: every spin id unique",
          len({s["id"] for s in spins}) == len(spins),
          f"{len(spins)} spins, {len({s['id'] for s in spins})} distinct ids")

    # 3 -----------------------------------------------------------------
    b1014 = next((b for b in bcs if b["id"].startswith("2025-10-14")), None)
    def one(b, artist, song):
        return [s for s in b["spins"]
                if s["artist"].lower() == artist and s["song"].lower() == song]
    ft = one(b1014, "fotoform", "digging trenches")
    bv = one(b1014, "beach vacation", "weighted down")
    check("3 persona: 2025-10-14 emits one Fotoform and one Beach Vacation spin",
          len(ft) == 1 and len(bv) == 1, f"fotoform={len(ft)} beach_vacation={len(bv)}")
    check("3 persona: merged spins kept the populated UPC",
          bool(ft and ft[0]["upc"]) and bool(bv and bv[0]["upc"]),
          f"fotoform upc={ft[0]['upc'] if ft else None}, "
          f"beach vacation upc={bv[0]['upc'] if bv else None}")
    check("3 persona: 2025-10-14 dj_ids carries both personas",
          b1014["dj_ids"] == ["173567", "174269"], str(b1014["dj_ids"]))
    # Matched on the song, not the artist: in class A the artist name comes from the
    # workbook, which spells "Eydis Evensen" without the accent Spinitron uses and marks
    # the second airing "(OUTRO)" -- itself confirmation that the wide-gap duplicate is a
    # deliberate repeat play rather than a double-log.
    wide = [("2024-02-20", "music for the dome"), ("2025-02-11", "always return to you"),
            ("2025-08-19", "tranquilant")]
    kept = []
    for date, song in wide:
        b = next(x for x in bcs if x["id"].startswith(date))
        kept.append(sum(1 for s in b["spins"] if song in s["song"].lower()))
    check("3 persona: wide-gap same-persona duplicates survive as two spins",
          all(n == 2 for n in kept), f"counts={kept}")

    # 4 -----------------------------------------------------------------
    b = next(x for x in bcs if x["id"].startswith("2025-10-14"))
    seqs = [s["sequence"] for s in b["spins"]]
    check("4 class A: 2025-10-14 (no ordering column) sequences 1..n",
          seqs == list(range(1, len(seqs) + 1)), f"{seqs[:5]}...")
    b0623 = next(x for x in bcs if x["id"].startswith("2026-06-23"))
    check("4 class A: 2026-06-23 picked up 'Mic Summary' as publish_note",
          any(s["publish_note"] for s in b0623["spins"]),
          f"{sum(1 for s in b0623['spins'] if s['publish_note'])} spins have one")
    check("4 class A: 2026-04-14 filed under its filename date, not 'March 31, 2025'",
          any(x["id"].startswith("2026-04-14") for x in bcs)
          and not any(x["id"].startswith("2025-03-31") for x in bcs))

    # 5 -----------------------------------------------------------------
    idx = {r["id"]: r for r in json.loads(INDEX.read_text())}
    a_ids = [i for i, r in idx.items() if r["class"] == "A"]
    check("5 attribution: all 31 class A broadcasts name MichaelG",
          all("MichaelG" in idx[i]["participants"] for i in a_ids),
          f"{sum(1 for i in a_ids if 'MichaelG' not in idx[i]['participants'])} missing")
    wb_dates = {re.search(r"(\d{4})\.(\d{2})\.(\d{2})", p.name).expand(r"\1-\2-\3")
                for p in MICHAELG_DIR.glob("*.xlsx")}
    for d in ("2026-03-17", "2025-10-14"):
        bid = next(i for i in idx if i.startswith(d))
        check(f"5 attribution: {d} attributed from its workbook despite persona",
              d in wb_dates and "MichaelG" in idx[bid]["participants"])

    # 6 -----------------------------------------------------------------
    reps = [b for b in bcs if b["first_broadcast_id"]]
    # 31 from detection alone; overrides/repeats.yaml can add more. The floor is the
    # assertion -- detection silently finding fewer than it did at design time is the
    # regression worth catching.
    rep_ov = yaml.safe_load((OVERRIDES / "repeats.yaml").read_text(encoding="utf-8")) or {}
    check("6 repeats: at least 31 broadcasts carry a first_broadcast_id", len(reps) >= 31,
          f"found {len(reps)} ({len(rep_ov.get('forced') or [])} forced, "
          f"{len(rep_ov.get('suppressed') or [])} suppressed by override)")
    check("6 repeats: no chains (every original is itself an original)",
          all(by_id[b["first_broadcast_id"]]["first_broadcast_id"] is None for b in reps),
          str([b["id"][:10] for b in reps
               if by_id[b["first_broadcast_id"]]["first_broadcast_id"]]))
    b0609 = next(x for x in bcs if x["id"].startswith("2026-06-09"))
    check("6 repeats: 2026-06-09 -> 2025-12-23 at confidence 1.0",
          b0609["first_broadcast_id"].startswith("2025-12-23")
          and b0609["repeat_of_confidence"] == 1.0,
          f"{b0609['first_broadcast_id'][:10]} conf={b0609['repeat_of_confidence']}")
    check("6 repeats: 2026-06-09 inherited MichaelG and the workbook's origins",
          "MichaelG" in [p["name"] for p in b0609["participants"]]
          and any(s["artist_origin_raw"] for s in b0609["spins"]))
    cluster = [b for b in bcs if (b["first_broadcast_id"] or "").startswith("2023-08-15")]
    check("6 repeats: the 2023-08-15 cluster's later airings all point at the original",
          len(cluster) == 3, f"{[b['id'][:10] for b in cluster]}")

    # 7 -----------------------------------------------------------------
    ac = {i for i, r in idx.items() if r["class"] in ("A", "C")}
    check("7 evidence: no planned spin in a class A or C broadcast",
          not [s for b in bcs if b["id"] in ac for s in b["spins"]
               if s["evidence"] == "planned"])
    planned = [s for s in spins if s["evidence"] == "planned"]
    check("7 evidence: every planned spin has a set-list source and no Spinitron one",
          all("spinitron" not in s["sources"] and s["sources"] for s in planned),
          f"{len(planned)} planned spins")
    check("7 evidence: no spin is 'reconstructed' (nothing fabricates spins yet)",
          not [s for s in spins if s["evidence"] == "reconstructed"])

    # 8 -----------------------------------------------------------------
    def empties(obj, path=""):
        out = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                out += empties(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                out += empties(v, f"{path}[{i}]")
        elif obj == "":
            out.append(path)
        return out
    bad = [p for b in bcs for p in empties(b)]
    check("8 nulls: no empty string anywhere in the cache", not bad, str(bad[:5]))
    false_no_basis = [s for s in spins if s["local"] is True and not s["local_basis"]]
    check("8 nulls: local=true always records a basis", not false_no_basis,
          f"{len(false_no_basis)} spins")
    check("8 nulls: local=false/null never carries a basis",
          not [s for s in spins if s["local"] is not True and s["local_basis"]])

    # 9 -----------------------------------------------------------------
    approved = [b for b in bcs if b["description_status"] == "approved"]
    # The gate is that "approved" comes from the overrides file and nowhere else -- one
    # approved broadcast per non-`skip` entry, exactly. An empty file must yield zero,
    # which is the same assertion, so this replaces the original empty-file check rather
    # than relaxing it.
    desc_ov = yaml.safe_load(
        (OVERRIDES / "descriptions.yaml").read_text(encoding="utf-8")) or {}
    entries = {(k.isoformat() if hasattr(k, "isoformat") else str(k))
               for k, v in desc_ov.items() if v != "skip"}
    got = {b["id"][:10] for b in approved}
    check("9 review gate: approved set equals the overrides file exactly",
          got == entries,
          f"{len(entries)} entries, {len(approved)} approved; "
          f"only in cache={sorted(got - entries)[:5]} "
          f"only in file={sorted(entries - got)[:5]}")
    # Repeats copy their original's content fields. A description approved once must not
    # silently become an approved description for a later airing nobody reviewed.
    check("9 review gate: no repeat inherited an approval it has no entry for",
          not [b for b in approved
               if b["first_broadcast_id"] and b["id"][:10] not in entries],
          str([b["id"][:10] for b in approved
               if b["first_broadcast_id"] and b["id"][:10] not in entries]))
    check("9 review gate: every non-null description has a status",
          all((b["description"] is None) == (b["description_status"] is None)
              for b in bcs))

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
