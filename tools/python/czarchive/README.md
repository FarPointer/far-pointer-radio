# czarchive

Archive tool for **Convergence Zone** on KSER 90.7. Pulls the episode playlist from Spinitron, captures the audio from the Spinitron Ark stream, and uploads the result to Mixcloud.

## Layout

| Module | Purpose |
|---|---|
| `cli.py` | Click CLI — `auth`, `download`, `upload`, `run` |
| `spinitron.py` | Spinitron playlist/spin API client, with a scraping fallback when no API key is set |
| `ark.py` | Spinitron Ark stream discovery and ffmpeg-based audio capture |
| `mixcloud.py` | Mixcloud OAuth flow (local callback on `localhost:8765`) and multipart upload |
| `config.py` | Loads `~/.czarchive.toml`; writes the OAuth token back after `auth` |

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/)
- `ffmpeg` on `PATH` (for stream capture)

## Setup

```sh
uv sync
cp .czarchive.toml.example ~/.czarchive.toml   # then fill in credentials
uv run czarchive auth                          # completes the Mixcloud OAuth flow
```

Configuration lives at `~/.czarchive.toml`, outside this repo. If the file is missing, czarchive creates a default copy there on first run and prints a reminder to fill it in.

## Usage

```sh
uv run czarchive download              # latest show; --date YYYY-MM-DD for a specific one
uv run czarchive upload                # upload the most recent download
uv run czarchive run                   # download then upload in one step
```

Downloads land in `output_dir` (default `~/shows`).

## Notes

- The Spinitron API key is optional — without it, playlist data is scraped instead.
- Never commit `~/.czarchive.toml`; it holds the Mixcloud client secret and access token.
