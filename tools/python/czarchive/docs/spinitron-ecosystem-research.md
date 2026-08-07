# Spinitron Ecosystem Research — czarchive Context

**Researched:** August 2026  
**Scope:** GitHub utilities that work with Spinitron; comparison with czarchive; recommendations for czarchive, WordPress embedding, and stream audio download.

---

## Summary

czarchive is the right tool to keep and improve — not replace. No existing open-source project covers the full workflow (Spinitron playlist fetch → Ark audio download → Mixcloud upload with tracklist chapters). The tool has been dormant for months and likely has at least one critical bug that prevents it from producing correct audio. The fixes are small and localized.

---

## Ecosystem survey

62 Spinitron-related GitHub repositories were found. The most relevant are grouped below.

### Official Spinitron repos

| Repo | Purpose |
|---|---|
| [spinitron/v2-web-integration](https://github.com/spinitron/v2-web-integration) | HTML/JS examples for embedding Spinitron content (now-playing, recent spins) on a website |
| [spinitron/v2-api-demo](https://github.com/spinitron/v2-api-demo) | PHP + AJAX demo of the v2 REST API |

### Python API wrappers

| Repo | Notes |
|---|---|
| [slogsdon7/spinitron](https://github.com/slogsdon7/spinitron) | Python v2 API wrapper. Last meaningful update 2019; 6 open issues. czarchive's `spinitron.py` already does what this does and integrates with the local config/credential system. Not worth adopting. |

### Stream download tools — most directly comparable to czarchive

| Repo | Language | Notes |
|---|---|---|
| [artxfm/spinget](https://github.com/artxfm/spinget) | Python | WXOX-specific. Downloads Ark audio by fetching 30-minute HLS index files keyed to UTC timestamps and concatenating segments with ffmpeg. No Spinitron API or playlist integration. No upload. |
| [baslipps/spinitron-show-exporter](https://github.com/baslipps/spinitron-show-exporter/tree/add-readme) | Bash + SwiftUI | macOS desktop app (July 2026). Paste a playlist URL → downloads audio with 2-pass EBU R128 loudness normalization, embeds cover art and metadata, optionally produces a YouTube-ready MP4. No Spinitron API or Mixcloud upload. |
| [wrbb/StreamRecorder](https://github.com/wrbb/StreamRecorder) | Go | Archived. Records live stream keyed to Spinitron schedule. Not relevant. |

### API proxies (not relevant to czarchive)

| Repo | Notes |
|---|---|
| [aidansmth/API-Relay](https://github.com/aidansmth/API-Relay) | Rust SSE proxy to hide API keys from browser-facing sites. czarchive runs server-side with credentials in `~/.czarchive.toml`. |
| [wcbn/spinitron-proxy](https://github.com/wcbn/spinitron-proxy) | Go lightweight proxy. Same reason — not applicable. |

### Spotify / social / WordPress integrations

| Repo | Notes |
|---|---|
| [erikdidriksen/spin2spot](https://github.com/erikdidriksen/spin2spot) | Python. Creates Spotify playlists from Spinitron playlists. Bookmark if per-episode Spotify playlists become interesting. |
| [uoregon/WPSpin](https://github.com/uoregon/WPSpin) | WordPress plugin for Spinitron. Targets the old SpinPAPI v1 API; 7 open issues; not actively maintained. Use Spinitron's own embedded widget instead. |
| [iamjeremybe/spinitron-to-bluesky](https://github.com/iamjeremybe/spinitron-to-bluesky) | PHP. Posts now-playing to Bluesky via Metadata Push. Out of scope for czarchive. |

---

## Detailed comparison: czarchive vs. the stream download tools

### Feature matrix

| Feature | czarchive | spinget | spinitron-show-exporter |
|---|---|---|---|
| Spinitron API v2 | ✅ (with key; scraping fallback) | ❌ | ❌ |
| Playlist/tracklist data saved | ✅ JSON with all spins + timestamps | ❌ | YouTube chapters only (--youtube mode) |
| Ark stream discovery | `/cgi/avail/` endpoint (undocumented) | Hardcoded URL template | Scrapes playlist page HTML ✅ |
| Audio download | ffmpeg `-ss`/`-t` (seek + trim) | ffmpeg concat of individual segments | ffmpeg `-t DURATION` from stream start ✅ |
| Loudness normalization | ❌ | ❌ | ✅ 2-pass EBU R128 at -14 LUFS |
| Embedded metadata (ID3/MP4) | ❌ | ❌ | ✅ title, artist, date, album, cover art |
| YouTube MP4 output | ❌ | ❌ | ✅ (still image + audio, with description file) |
| Mixcloud upload + tracklist | ✅ full OAuth + chapters | ❌ | ❌ |
| Date-addressable history | ✅ `--date YYYY-MM-DD` | ❌ | ✅ (paste any playlist URL) |
| Config file / credentials | ✅ `~/.czarchive.toml` | Hardcoded constants | Environment variables |
| Debug / short download | ❌ | ❌ | ✅ `--debug` (5-minute cap) |
| Platform | Python, cross-platform | Python, cross-platform | macOS only (SwiftUI GUI) |

### The UTC/Pacific midnight offset bug (critical)

`ark.py` lines 64–67 compute the ffmpeg `-ss` seek offset as seconds since **midnight Pacific**:

```python
stream_origin = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
offset_secs = int((start_time - stream_origin).total_seconds())
```

But Spinitron's Ark HLS streams begin at **midnight UTC**.

**Concrete example — Convergence Zone, Tuesday winter broadcast:**

| | Value |
|---|---|
| Broadcast time | Tuesday 8:30 PM PT (UTC−8) |
| UTC equivalent | Wednesday 4:30 AM UTC |
| Ark stream for Wednesday UTC starts | Wednesday 00:00 UTC |
| **Correct** offset into Wednesday's stream | 4 h 30 min = **16,200 s** |
| czarchive **computes** | 20 h 30 min = **73,800 s** |

Seeking 73,800 seconds into a ~86,400-second recording points near the end of the wrong recording day. ffmpeg produces garbage audio or an empty file. **This is likely why czarchive stopped working.**

spinget avoids this by requesting UTC-timestamped HLS index files directly. spinitron-show-exporter avoids it by downloading from stream start with `-t DURATION` rather than seeking.

---

## Recommendations

### 1. Fix czarchive rather than switch to another tool

The other tools don't have Mixcloud upload, structured tracklist JSON, or config-driven operation. The full workflow — Spinitron → Ark → Mixcloud with chapters — exists only in czarchive. The problems are bugs and missing features, not architectural issues.

### 2. Prioritized fix list

| Priority | Item | Effort | Notes |
|---|---|---|---|
| 🔴 Critical | Fix UTC offset bug in `ark.py` | ~5 lines | Most likely cause of recent failures |
| 🟠 High | Verify `find_ark_stream` queries the UTC date, not PT date | ~5 lines | Tuesday PT show = Wednesday UTC stream |
| 🟡 Medium | Improve stream discovery: scrape playlist page for m3u8 | ~20 lines | Replaces undocumented `/cgi/avail/` endpoint; borrows from spinitron-show-exporter |
| 🟡 Medium | Verify HTML scraping selectors in `spinitron.py` against live KSER page | Inspection + ~5 lines | Add guard: error if HTTP 200 but zero spins returned |
| 🟢 Low | Add `--duration` flag to `czarchive download` | ~10 lines | 5-minute test downloads; from spinitron-show-exporter `--debug` |
| 🟢 Low | Add 2-pass EBU R128 loudness normalization | ~30 lines | Opt-in `--normalize` flag; borrows from spinitron-show-exporter |
| 🟢 Low | Embed ID3 metadata and cover art into output MP3 | ~8 ffmpeg flags | Station name, show title, date, album, cover image |

### 3. WordPress embedding

Use **Spinitron's own built-in station widget** (available in station admin under "Station Widgets"). It's an `<iframe>` or `<script>` tag — paste it into a WordPress Custom HTML block. No plugin needed.

[spinitron/v2-web-integration](https://github.com/spinitron/v2-web-integration) shows how to build a custom now-playing display using the public API with JavaScript if more control is needed.

**Do not use [uoregon/WPSpin](https://github.com/uoregon/WPSpin)** — it targets the old SpinPAPI v1 API and is not maintained.

### 4. What to borrow from spinitron-show-exporter

The most valuable patterns to adapt into czarchive (not wholesale adopt — it's macOS-only Bash):

- **Stream discovery from playlist page** — scrape `data-ark-start` and `ark2Player` config from the Spinitron playlist HTML to construct the m3u8 URL. More stable than the undocumented availability endpoint.
- **2-pass loudnorm** — standard ffmpeg invocation with EBU R128 targets.
- **`--debug` mode** — cap download to 5 minutes for testing.

---

## Files referenced

```
tools/python/czarchive/src/czarchive/ark.py          # UTC offset bug; stream discovery
tools/python/czarchive/src/czarchive/spinitron.py    # HTML scraping selectors
tools/python/czarchive/src/czarchive/cli.py          # --duration / --normalize flags
```

## External references

- [artxfm/spinget](https://github.com/artxfm/spinget)
- [baslipps/spinitron-show-exporter](https://github.com/baslipps/spinitron-show-exporter/tree/add-readme)
- [spinitron/v2-web-integration](https://github.com/spinitron/v2-web-integration)
- [slogsdon7/spinitron](https://github.com/slogsdon7/spinitron)
- [erikdidriksen/spin2spot](https://github.com/erikdidriksen/spin2spot)
- [EBU R128 loudness standard](https://tech.ebu.ch/loudness)
- [ffmpeg loudnorm filter](https://ffmpeg.org/ffmpeg-filters.html#loudnorm)
