"""Check the built cache against the invariants the build is supposed to guarantee.

Run after build.py. Every check either passes or prints what it found; the exit code is
non-zero if any failed, so this works as a pre-commit gate.

These are not unit tests of the loaders -- they are assertions about the *output*, which
is what actually has to be right. Every expected count is derived from the sources at
run time, never written down here: a new Spinitron export or another workbook is normal
and must not read as a regression, while a broadcast or a spin going missing between the
sources and the cache still fails loudly.
"""
import collections
import csv
import json
import pathlib
import re
import subprocess
import sys
import tempfile

import yaml

import build
import load_spinitron
import repeats
from paths import (BROADCASTS, CZAUDIT, INDEX, MICHAELG_DIR, OVERRIDES, REPO,
                   SPINITRON_PLAYLISTS, SPINS_CSV)

sys.path.insert(0, str(CZAUDIT))
from matching import norm  # noqa: E402

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
    # Two separate assertions that the old single check conflated.
    #
    # Determinism is a property of the build: same sources in, same bytes out. Testing it
    # by diffing the working tree against git only ever answered "is the committed cache
    # current?", which is a different question -- it cannot detect nondeterminism before
    # the cache is first committed, and it reports a false regression during any
    # legitimate in-flight change. So build twice into throwaway directories and compare.
    with tempfile.TemporaryDirectory() as tmp:
        a, b = pathlib.Path(tmp) / "a", pathlib.Path(tmp) / "b"
        build.main(cache_root=a, quiet=True)
        build.main(cache_root=b, quiet=True)
        differing = sorted(
            p.name for p in sorted((a / "broadcasts").glob("*.json"))
            if p.read_bytes() != (b / "broadcasts" / p.name).read_bytes())
        same_index = (a / "index.json").read_bytes() == (b / "index.json").read_bytes()
        check("1 determinism: two builds produce identical bytes",
              not differing and same_index,
              f"{len(differing)} broadcast file(s) differ: {differing[:5]}"
              if differing else "index.json differs")

    tracked = subprocess.run(["git", "ls-files", "shows/convergence-zone/playlists/cache/"],
                             cwd=REPO, capture_output=True, text=True).stdout.strip()
    r = subprocess.run(["git", "diff", "--stat", "--", "shows/convergence-zone/playlists/cache/"],
                       cwd=REPO, capture_output=True, text=True)
    if not tracked:
        check("1 committed cache is current (nothing tracked yet)", True,
              "no baseline to diff against")
    else:
        check("1 committed cache is current: rebuild produces no diff",
              r.stdout.strip() == "", r.stdout.strip()[:400])

    # 2 -----------------------------------------------------------------
    with open(SPINS_CSV, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    logged = [s for s in spins if "spinitron" in s["sources"]]
    # One broadcast per distinct playlist start in the export -- the same grouping
    # load_spinitron uses, recomputed from the CSV so a new export simply raises the
    # expected number instead of failing.
    export_broadcasts = {r["Playlist Date-time"] for r in rows}
    check("2 conservation: one broadcast file per exported playlist start",
          len(bcs) == len(export_broadcasts),
          f"export has {len(export_broadcasts)}; cache has {len(bcs)}")
    # Cross-persona pairs merge automatically; each reviewed entry in spins.yaml merges
    # one more. Both counts come from the loader itself rather than being written down,
    # so an approved decision or a new export does not read as a regression -- but the
    # check is still exact, so an unexplained loss of rows does.
    forced = (yaml.safe_load((OVERRIDES / "spins.yaml").read_text(encoding="utf-8"))
              or {}).get("merge_duplicates") or []
    merges = load_spinitron.load(forced)[1]
    expected = len(rows) - len(merges)
    check("2 conservation: Spinitron rows accounted for",
          len(logged) == expected,
          f"{len(rows)} rows - {len(merges)} merges ({len(forced)} reviewed) = "
          f"{expected}; cache has {len(logged)}")
    classes = collections.Counter(json.loads(INDEX.read_text())[i]["class"]
                                 for i in range(len(bcs)))
    # 31/70/63 at design time, but the split is override-sensitive: a forced repeat of a
    # MichaelG episode promotes that airing to class A, because a repeat inherits its
    # original's canonical source. Hardcoding the numbers would make an approved decision
    # read as a regression -- the same trap checks 2, 6 and 9 already avoid elsewhere.
    a_from_workbook = {re.search(r"(\d{4})\.(\d{2})\.(\d{2})", p.name).expand(r"\1-\2-\3")
                       for p in MICHAELG_DIR.glob("*.xlsx")}
    a_from_repeat = {b["id"][:10] for b in bcs
                     if b["first_broadcast_id"]
                     and b["first_broadcast_id"][:10] in a_from_workbook}
    expected_a = len(a_from_workbook | a_from_repeat)
    check("2 conservation: class A equals workbooks plus repeats of one",
          classes["A"] == expected_a,
          f"{len(a_from_workbook)} workbooks + {len(a_from_repeat - a_from_workbook)} "
          f"repeats = {expected_a}; cache has {classes['A']}")
    check("2 conservation: every broadcast lands in exactly one class",
          sum(classes.values()) == len(bcs), str(dict(classes)))
    check("2 conservation: id equals air_datetime verbatim",
          all(b["id"] == b["air_datetime"] for b in bcs))
    check("2 conservation: every spin id unique",
          len({s["id"] for s in spins}) == len(spins),
          f"{len(spins)} spins, {len({s['id'] for s in spins})} distinct ids")
    playlist_ids = [pid for b in bcs for pid in b["spinitron_playlist_ids"]]
    multiple = [b for b in bcs if len(b["spinitron_playlist_ids"]) > 1]
    multiple_dates = {b["id"][:10] for b in multiple}
    # A persona switch mid-show produces two Spinitron playlists for one broadcast, so
    # the snapshot itself says which dates those are and how many IDs there should be.
    snapshot = json.loads(SPINITRON_PLAYLISTS.read_text(encoding="utf-8"))["playlists"]
    cache_dates = {b["id"][:10] for b in bcs}
    snapshot_dates = collections.Counter(p["start"][:10] for p in snapshot
                                         if p["start"][:10] in cache_dates)
    expected_multiple_dates = {d for d, n in snapshot_dates.items() if n > 1}
    check("2 conservation: every broadcast has a Spinitron playlist ID",
          all(b["spinitron_playlist_ids"] for b in bcs))
    check("2 conservation: persona-switch broadcasts carry every playlist ID",
          multiple_dates == expected_multiple_dates
          and len(playlist_ids) == sum(snapshot_dates.values()),
          f"dates={sorted(multiple_dates)} (snapshot says "
          f"{sorted(expected_multiple_dates)}), {len(playlist_ids)} of "
          f"{sum(snapshot_dates.values())} IDs")
    check("2 conservation: every Spinitron playlist ID belongs to one broadcast",
          len(set(playlist_ids)) == len(playlist_ids),
          f"{len(playlist_ids)} IDs, {len(set(playlist_ids))} distinct")

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
    check("5 attribution: every class A broadcast names MichaelG",
          all("MichaelG" in idx[i]["participants"] for i in a_ids),
          f"{len(a_ids)} class A, "
          f"{sum(1 for i in a_ids if 'MichaelG' not in idx[i]['participants'])} missing")
    wb_dates = {re.search(r"(\d{4})\.(\d{2})\.(\d{2})", p.name).expand(r"\1-\2-\3")
                for p in MICHAELG_DIR.glob("*.xlsx")}
    for d in ("2026-03-17", "2025-10-14"):
        bid = next(i for i in idx if i.startswith(d))
        check(f"5 attribution: {d} attributed from its workbook despite persona",
              d in wb_dates and "MichaelG" in idx[bid]["participants"])

    # 6 -----------------------------------------------------------------
    reps = [b for b in bcs if b["first_broadcast_id"]]
    # No expected count: the archive grows, and a rerun of an old episode is ordinary
    # news. What has to hold is that every link is explainable -- detected at or above
    # the floor, or written down in overrides/repeats.yaml.
    rep_ov = yaml.safe_load((OVERRIDES / "repeats.yaml").read_text(encoding="utf-8")) or {}
    forced_pairs = {tuple(sorted(p)) for p in (rep_ov.get("forced") or [])}
    unexplained = [b["id"][:10] for b in reps
                   if b["repeat_of_confidence"] < repeats.REPLAY_FLOOR
                   and tuple(sorted((b["id"], b["first_broadcast_id"]))) not in forced_pairs]
    check("6 repeats: every first_broadcast_id is detected or forced", not unexplained,
          f"found {len(reps)} repeats ({len(forced_pairs)} forced, "
          f"{len(rep_ov.get('suppressed') or [])} suppressed by override); "
          f"unexplained={unexplained}")
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
    # silently become an approved description for a later airing nobody reviewed. This
    # is implied by the set equality above, but stated separately because it is the
    # specific leak the gate exists to stop, and the two could drift apart.
    check("9 review gate: no repeat inherited an approval it has no entry for",
          not [b for b in approved
               if b["first_broadcast_id"] and b["id"][:10] not in entries],
          str([b["id"][:10] for b in approved
               if b["first_broadcast_id"] and b["id"][:10] not in entries]))
    check("9 review gate: every non-null description has a status",
          all((b["description"] is None) == (b["description_status"] is None)
              for b in bcs))

    # 10 ----------------------------------------------------------------
    # The same gate as check 9, for the three override files that did not have one.
    #
    # `descriptions.yaml` and `spins.yaml` were both parsed and silently ignored for the
    # whole life of the build, and the checks in place could not tell "the gate holds"
    # from "the gate is not wired up" -- because the files were empty, both look alike.
    # An override file with no assertion behind it is exactly that situation waiting to
    # recur, so each of these derives what the cache must look like from the file itself.
    def by_date(name):
        data = yaml.safe_load((OVERRIDES / name).read_text(encoding="utf-8")) or {}
        return {(k.isoformat() if hasattr(k, "isoformat") else str(k)): v
                for k, v in data.items()}

    part_ov = by_date("participants.yaml")
    empty_entries = [d for d, v in part_ov.items() if not v]
    check("10 participants gate: no entry is empty",
          not empty_entries,
          f"{empty_entries} would silently fall back to workbook inference")
    wrong = []
    for date, want in part_ov.items():
        if not want:
            continue
        b = next((x for x in bcs if x["id"][:10] == date), None)
        if b is None:
            wrong.append(f"{date}: no such broadcast")
            continue
        got_p = [(p["name"], p["coverage"]) for p in b["participants"]]
        want_p = [(p["name"], p.get("coverage", "full")) for p in want]
        if got_p != want_p:
            wrong.append(f"{date}: want {want_p}, got {got_p}")
    check("10 participants gate: every entry appears verbatim in the cache",
          not wrong, "; ".join(wrong[:3]))

    rep_pairs = yaml.safe_load(
        (OVERRIDES / "repeats.yaml").read_text(encoding="utf-8")) or {}
    linked = {(b["first_broadcast_id"], b["id"]) for b in bcs if b["first_broadcast_id"]}
    missing_forced = [p for p in (rep_pairs.get("forced") or [])
                      if tuple(sorted(p)) not in
                      {tuple(sorted(x)) for x in linked}]
    check("10 repeats gate: every forced pair is linked in the cache",
          not missing_forced, str(missing_forced[:3]))
    # Suppression is the direction that cannot be confirmed by counting, because a
    # suppressed pair leaves no trace anywhere. Assert the absence directly.
    live_suppressed = [p for p in (rep_pairs.get("suppressed") or [])
                       if tuple(sorted(p)) in {tuple(sorted(x)) for x in linked}]
    check("10 repeats gate: no suppressed pair survived",
          not live_suppressed, str(live_suppressed[:3]))

    # The count assertion in check 2 passes as long as the totals add up, which they
    # would even if an override merged some other pair entirely. Name the specific spin.
    spins_ov = yaml.safe_load(
        (OVERRIDES / "spins.yaml").read_text(encoding="utf-8")) or {}
    unmerged = []
    for entry in spins_ov.get("merge_duplicates") or []:
        date = str(entry.get("broadcast") or "")[:10]
        b = next((x for x in bcs if x["id"][:10] == date), None)
        if b is None:
            unmerged.append(f"{date}: no such broadcast")
            continue
        want_song = norm(entry.get("song") or "", drop_paren=True)
        hits = [s for s in b["spins"]
                if norm(s["artist"]) == norm(entry.get("artist") or "")
                and norm(s["song"], drop_paren=True) == want_song
                and "spinitron" in s["sources"]]
        if len(hits) != 1:
            unmerged.append(
                f"{date} {entry.get('artist')} - {entry.get('song')}: "
                f"{len(hits)} logged spins, expected 1")
    check("10 spins gate: every merge_duplicates entry left exactly one logged spin",
          not unmerged, "; ".join(unmerged[:3]))

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
