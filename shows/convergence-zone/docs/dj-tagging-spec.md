# DJ Tagging Spec — Convergence Zone

**Status:** Draft v1.0  
**Audience:** Tool builders, show hosts  
**Relates to:** Issue #24 — Tagging scheme for DJ software

---

## 1. Purpose

This document specifies how music files used on *Convergence Zone* should be tagged so that:

1. Standard metadata (artist, title, album, genre, BPM, key) is correct and consistent.
2. Show-specific metadata (regional flag, voiceover-bed flag, rotation priority) survives round-trips through Serato DJ Pro, Rekordbox, VirtualDJ, Mixxx, and deeJay.
3. A CLI tool (`cztag`) can read, write, and validate these tags across all supported audio formats.

---

## 2. Background: Tagging Formats by File Type

| Format | Container | Native tag format | Notes |
|--------|-----------|-------------------|-------|
| MP3 | MPEG Audio | **ID3v2.3 / ID3v2.4** | ID3v2.3 has widest DJ software support; use 2.3 unless otherwise noted |
| FLAC | Ogg FLAC | **Vorbis Comments** | Case-insensitive key=value pairs, UTF-8 |
| WAV | RIFF | **ID3v2 chunk** (`id3 ` or `ID3 `) | Serato and Rekordbox both read/write ID3 inside WAV |
| AIFF | IFF | **ID3v2 chunk** (`ID3 `) | Serato prefers ID3 in AIFF |
| AAC / M4A | MP4 | **MP4 atoms** (iTunes metadata) | Uses free-form `----` atoms for custom fields |
| OGG Vorbis | Ogg | **Vorbis Comments** | Same as FLAC |
| Opus | Ogg | **Vorbis Comments** | Same as FLAC |

### 2.1 Standard fields and their per-format names

| Semantic field | ID3v2 frame | Vorbis Comment key | MP4 atom |
|----------------|-------------|-------------------|----------|
| Title | `TIT2` | `TITLE` | `©nam` |
| Artist | `TPE1` | `ARTIST` | `©ART` |
| Album | `TALB` | `ALBUM` | `©alb` |
| Album Artist | `TPE2` | `ALBUMARTIST` | `aART` |
| Track number | `TRCK` | `TRACKNUMBER` | `trkn` |
| Year | `TDRC` (v2.4) / `TYER` (v2.3) | `DATE` | `©day` |
| Genre | `TCON` | `GENRE` | `©gen` |
| Comment | `COMM` | `COMMENT` | `©cmt` |
| BPM | `TBPM` | `BPM` | `tmpo` |
| Initial Key | `TKEY` | `INITIALKEY` | `----:com.apple.iTunes:initialkey` |
| Composer | `TCOM` | `COMPOSER` | `©wrt` |
| Label | `TPUB` | `ORGANIZATION` | `----:com.apple.iTunes:LABEL` |
| ISRC | `TSRC` | `ISRC` | `----:com.apple.iTunes:ISRC` |
| Grouping | `TIT1` | `GROUPING` | `©grp` |

---

## 3. DJ Software Compatibility

### 3.1 Serato DJ Pro

Serato stores its own data in proprietary ID3 frames and MP4 atoms, but reads all standard frames.

| Serato feature | Storage mechanism |
|----------------|------------------|
| BPM (analyzed) | `TBPM` (ID3) / `BPM` (Vorbis) — Serato overwrites with its own analysis |
| Cue points, loops | `GEOB` (General Encapsulated Object) frames named `Serato Markers2`, `Serato Overview` — binary blobs, not human-editable |
| Beat grid | `GEOB` frame `Serato BeatGrid` |
| Color label | `GEOB` frame `Serato Markers2` (encoded within the blob) |
| Custom tags visible in library | Standard frames: `TIT1` (Grouping), `TCON` (Genre), `COMM` (Comment), `TPUB` (Label) |

**Key takeaway:** Custom Convergence Zone flags must live in standard fields (Genre, Grouping, Comment, or Label) because Serato does not expose arbitrary custom frames in its library columns.

### 3.2 Rekordbox (Pioneer DJ)

Rekordbox reads ID3v2 and MP4. It surfaces these columns in its library:

- Artist, Title, Album, BPM, Key (reads `TKEY`/`INITIALKEY`), Genre, Comment, Label, Grouping, Rating.
- Custom fields beyond the above are not displayed natively. Use Comment or Grouping for extra flags.
- Rekordbox exports cue points and waveforms to its own XML database; those are not stored in file tags.

### 3.3 VirtualDJ

VirtualDJ reads ID3v2, Vorbis Comments, and MP4. It supports:

- All standard fields above.
- A `virtual_dj_*` namespace in Vorbis Comments, but this is VirtualDJ-internal and not portable.
- Custom column display via the standard `Comment` or `Grouping` fields.

### 3.4 Mixxx (open source)

Mixxx reads ID3v2 (2.3 and 2.4), Vorbis Comments, and MP4. It supports:

- All standard fields.
- User-defined `COMMENT` sub-frame description field (ID3: `COMM` with a `DESC` sub-field).
- The `TXXX` (user-defined text) ID3 frame is **read and indexed** by Mixxx, making it the best mechanism for truly custom fields in MP3/WAV/AIFF.

### 3.5 deeJay (macOS)

deeJay is a lightweight DJ app that reads standard iTunes/MP4 metadata and ID3 tags. It does not expose custom frames; use Genre, Grouping, or Comment.

### 3.6 Summary: cross-software field availability

| Field | Serato | Rekordbox | VirtualDJ | Mixxx | deeJay |
|-------|--------|-----------|-----------|-------|--------|
| Genre (`TCON`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Grouping (`TIT1`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Comment (`COMM`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Label (`TPUB`) | ✅ | ✅ | ✅ | ✅ | ❌ |
| `TXXX` custom | ❌ | ❌ | ❌ | ✅ | ❌ |

---

## 4. Convergence Zone Custom Tags

### 4.1 Tag definitions

These are the show-specific flags needed. Each is defined by its semantic meaning, storage location per format, and example values.

#### 4.1.1 `CZ_REGIONAL` — Pacific Northwest regional artist flag

| Aspect | Value |
|--------|-------|
| Purpose | Marks a track whose primary artist is a Pacific Northwest artist eligible for the Convergence Zone regional spotlight |
| Values | `true` / `false` (string `"1"` or `"0"` for formats that don't support boolean) |
| ID3v2 (MP3, WAV, AIFF) | `TXXX:CZ_REGIONAL` — user-defined text frame, description = `CZ_REGIONAL` |
| Vorbis (FLAC, OGG, Opus) | `CZ_REGIONAL=1` |
| MP4 (AAC, M4A) | `----:com.convergencezone:CZ_REGIONAL` |
| Serato / Rekordbox visible | Via **Grouping** field (see §4.2 encoding) |

#### 4.1.2 `CZ_BED` — voiceover bed flag

| Aspect | Value |
|--------|-------|
| Purpose | Marks a track suitable as a background bed during voiceover / DJ talk breaks |
| Values | `true` / `false` |
| ID3v2 | `TXXX:CZ_BED` |
| Vorbis | `CZ_BED=1` |
| MP4 | `----:com.convergencezone:CZ_BED` |
| Serato / Rekordbox visible | Via **Grouping** field |

#### 4.1.3 `CZ_ROTATION` — rotation priority

| Aspect | Value |
|--------|-------|
| Purpose | Controls how frequently the track should be scheduled in a set |
| Values | `heavy` / `medium` / `light` / `recurrent` / `none` |
| ID3v2 | `TXXX:CZ_ROTATION` |
| Vorbis | `CZ_ROTATION=heavy` |
| MP4 | `----:com.convergencezone:CZ_ROTATION` |
| Serato / Rekordbox visible | Via **Comment** field |

#### 4.1.4 `CZ_SHOW` — show name

| Aspect | Value |
|--------|-------|
| Purpose | Associates the file with a specific show, useful if the library is shared with other programs |
| Values | Free text; default `Convergence Zone` |
| ID3v2 | `TXXX:CZ_SHOW` |
| Vorbis | `CZ_SHOW=Convergence Zone` |
| MP4 | `----:com.convergencezone:CZ_SHOW` |
| Serato / Rekordbox visible | Via **Label** field (or Grouping if Label is unavailable) |

#### 4.1.5 `CZ_NOTES` — free-form notes

| Aspect | Value |
|--------|-------|
| Purpose | Show-host notes about the track (pronunciation, intro length, cue point hints) |
| Values | Free text, single line recommended |
| ID3v2 | `COMM:CZ_NOTES` — standard COMM frame with description `CZ_NOTES`, `eng` language |
| Vorbis | `CZ_NOTES=...` |
| MP4 | `----:com.convergencezone:CZ_NOTES` |
| Serato / Rekordbox visible | Will appear in Comment column if Grouping is used for other flags |

---

### 4.2 Grouping field encoding (cross-software visibility)

Because only `Genre`, `Grouping`, and `Comment` are universally visible across all five DJ applications, CZ boolean flags are also encoded into the **Grouping** field as a compact keyword list so they surface in any software.

**Format:**

```
[CZ] <flag1> <flag2> ...
```

Examples:

| Flags set | Grouping value |
|-----------|----------------|
| Regional only | `[CZ] regional` |
| Bed only | `[CZ] bed` |
| Regional + bed | `[CZ] regional bed` |
| Heavy rotation | `[CZ] heavy` |
| Regional + bed + heavy | `[CZ] regional bed heavy` |
| No CZ flags | *(Grouping untouched or blank)* |

If the track already has a Grouping value set by the label (e.g. `Classical/Ambient`), the CZ prefix is appended after a semicolon:

```
Classical/Ambient; [CZ] regional bed
```

The `cztag` tool must parse the Grouping field, update only the `[CZ] ...` portion, and preserve any pre-existing content.

**Comment field encoding for rotation:**

When `CZ_ROTATION` is set to anything other than `none`, the Comment field is suffixed with:

```
[CZ:rotation=heavy]
```

If the Comment field already has content, a space is inserted before the bracket tag.

---

## 5. Proposed Tool: `cztag`

### 5.1 Overview

`cztag` is a Python 3.11+ CLI tool, managed with `uv`, placed at `tools/python/cztag/`. It reads and writes the tags defined in §4 across all supported audio formats.

### 5.2 Dependencies

| Library | Purpose |
|---------|---------|
| [mutagen](https://mutagen.readthedocs.io/) | Read/write ID3v2, Vorbis Comments, MP4, AIFF, WAV tags |
| [click](https://click.palletsprojects.com/) | CLI framework (consistent with existing tools) |
| [rich](https://github.com/Textualize/rich) | Terminal output formatting |
| [pyyaml](https://pyyaml.org/) | Batch tag manifest files |

Mutagen covers all required formats natively; no additional audio libraries are needed.

### 5.3 Commands

#### `cztag show <file>`

Print all tags for a file in a human-readable table.

```
$ cztag show "artist - track.flac"

File: artist - track.flac
Format: FLAC (Vorbis Comments)

Standard tags
  TITLE          Drifting Between Worlds
  ARTIST         Yuna Reed
  ALBUM          Silence Intervals
  GENRE          Ambient
  BPM            92

Convergence Zone tags
  CZ_REGIONAL    true
  CZ_BED         false
  CZ_ROTATION    heavy
  CZ_SHOW        Convergence Zone
  CZ_NOTES       Intro is 24 s; safe to talk over

Grouping (DJ software visible)
  Classical/Ambient; [CZ] regional heavy
```

#### `cztag set <file> [options]`

Set one or more tags on a file.

```
cztag set "track.flac" \
  --regional \
  --bed \
  --rotation heavy \
  --notes "Intro: 24 s"
```

Options:

| Option | Type | Description |
|--------|------|-------------|
| `--regional` / `--no-regional` | flag | Set `CZ_REGIONAL` |
| `--bed` / `--no-bed` | flag | Set `CZ_BED` |
| `--rotation <value>` | choice | `heavy`, `medium`, `light`, `recurrent`, `none` |
| `--show <name>` | text | Set `CZ_SHOW` |
| `--notes <text>` | text | Set `CZ_NOTES` |
| `--dry-run` | flag | Print what would change, do not write |

#### `cztag clear <file>`

Remove all `CZ_*` tags and the `[CZ ...]` Grouping portion from a file.

#### `cztag validate <file> [<file> ...]`

Check that required standard tags (`TITLE`, `ARTIST`, `BPM`) are present and that all `CZ_*` tag values are valid. Exit non-zero if any file fails.

```
$ cztag validate *.flac
✅ yuna-reed-drifting.flac
❌ unnamed-track.mp3   — missing TITLE, BPM
```

#### `cztag batch <manifest.yaml>`

Apply tags to a set of files defined in a YAML manifest. Useful for tagging an entire episode's files at once.

**Manifest format:**

```yaml
# cztag-batch manifest
defaults:
  cz_show: Convergence Zone
  cz_rotation: medium

files:
  - path: "/mnt/music/yuna-reed-drifting.flac"
    cz_regional: true
    cz_bed: false
    cz_rotation: heavy
    notes: "Intro 24 s; safe to talk over"

  - path: "/mnt/music/outro-pad.mp3"
    cz_bed: true
    notes: "Outro bed; fade after 90 s"
```

### 5.4 Architecture

```
tools/python/cztag/
├── pyproject.toml          # uv / PEP 517 package definition
├── README.md
└── src/
    └── cztag/
        ├── __init__.py
        ├── cli.py          # Click command definitions
        ├── tagger.py       # Core read/write logic, format dispatch
        ├── formats/
        │   ├── __init__.py
        │   ├── id3.py      # MP3, WAV, AIFF via mutagen ID3
        │   ├── vorbis.py   # FLAC, OGG, Opus via mutagen VorbisComment
        │   └── mp4.py      # AAC, M4A via mutagen MP4
        ├── grouping.py     # Grouping field encode/decode logic
        └── validate.py     # Validation rules
```

### 5.5 Grouping round-trip contract

`grouping.py` must satisfy:

1. **Parse** — given any Grouping string, extract the CZ keyword list and the non-CZ prefix (may be empty).
2. **Encode** — given a non-CZ prefix and a set of CZ flags, produce the canonical Grouping string.
3. **Round-trip** — `encode(parse(s)) == s` for any valid Grouping string.
4. **Idempotent** — applying the same flags twice produces the same result as applying them once.

### 5.6 Dry-run and backup

- `--dry-run` prints a unified diff of tag changes.
- Without `--dry-run`, `cztag set` writes a `.bak` sidecar file before modifying. The sidecar is the original tag dump in YAML, not a copy of the audio data.

---

## 6. Open Questions

| # | Question | Owner |
|---|----------|-------|
| 1 | Should `CZ_REGIONAL` be inferred automatically from the locality data in `czcache`, or always set manually? | Jim / MichaelG |
| 2 | Is a `CZ_ROTATION` field actually needed, or does the existing Spinitron "heavy/recurrent" concept cover this? | MichaelG |
| 3 | Which DJ software do Jim and MichaelG use day-to-day? This affects which Grouping vs. Label vs. Comment fallback to prioritize. | Jim / MichaelG |
| 4 | Should `cztag batch` also accept CSV input (matching the playlist filename convention `YYYY-MM-DD-episode-title.csv`)? | Tool builder |
| 5 | Do WAV files need tagging support, or is the library FLAC/MP3 only? | Jim |

---

## 7. References

- [ID3.org v2.3 spec](https://id3.org/id3v2.3.0)
- [ID3.org v2.4 spec](https://id3.org/id3v2.4.0-structure)
- [Xiph Vorbis Comment spec](https://www.xiph.org/vorbis/doc/v-comment.html)
- [mutagen documentation](https://mutagen.readthedocs.io/)
- [Serato DJ metadata format (community documentation)](https://github.com/Holzchopf/community-solid-serato-markers)
- [Rekordbox XML export schema](https://cdn.rekordbox.com/files/20200410160904/xml_format_list.pdf)
- [Mixxx tag documentation](https://github.com/mixxxdj/mixxx/wiki/Metadata)
