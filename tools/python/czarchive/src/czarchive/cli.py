"""czarchive CLI — download, upload, and archive Convergence Zone episodes."""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import click

from czarchive.config import CONFIG_PATH, load_config, save_token
from czarchive.spinitron import Playlist, Spin, make_spinitron_client

PACIFIC = ZoneInfo("America/Los_Angeles")


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _playlist_to_dict(pl: Playlist) -> dict:
    return {
        "id": pl.id,
        "title": pl.title,
        "start_time": pl.start_time.isoformat(),
        "end_time": pl.end_time.isoformat(),
        "spins": [
            {
                "artist": s.artist,
                "song": s.song,
                "album": s.album,
                "start_time": s.start_time.isoformat(),
            }
            for s in pl.spins
        ],
    }


def _playlist_from_dict(d: dict) -> Playlist:
    from dateutil import parser as dp
    return Playlist(
        id=d["id"],
        title=d["title"],
        start_time=dp.parse(d["start_time"]),
        end_time=dp.parse(d["end_time"]),
        spins=[
            Spin(
                artist=s["artist"],
                song=s["song"],
                album=s.get("album", ""),
                start_time=dp.parse(s["start_time"]),
            )
            for s in d.get("spins", [])
        ],
    )


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
def cli():
    """czarchive — Convergence Zone archive tool for KSER 90.7."""


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------

@cli.command()
def auth():
    """Run Mixcloud OAuth flow and save the access token."""
    config = load_config()
    if not config.mixcloud_client_id or not config.mixcloud_client_secret:
        click.echo(
            f"Error: mixcloud_client_id and mixcloud_client_secret must be set in {CONFIG_PATH}",
            err=True,
        )
        sys.exit(1)

    from czarchive.mixcloud import run_oauth_flow
    token = run_oauth_flow(config.mixcloud_client_id, config.mixcloud_client_secret)
    save_token(token)
    click.echo(f"Access token saved to {CONFIG_PATH}")


# ---------------------------------------------------------------------------
# download
# ---------------------------------------------------------------------------

@cli.command()
@click.option(
    "--date", "show_date_str",
    default=None,
    help="Show date as YYYY-MM-DD (default: most recent episode)",
)
def download(show_date_str: str | None):
    """Download the latest (or specified) show audio and tracklist."""
    config = load_config()
    config.output_path.mkdir(parents=True, exist_ok=True)

    # --- Resolve show date ---
    spinitron = make_spinitron_client(config)

    if show_date_str:
        show_date = date.fromisoformat(show_date_str)
        click.echo(f"Fetching playlist for {show_date} …")
        playlist = spinitron.get_playlist_by_date(config.show_name, show_date)
    else:
        click.echo("Fetching latest playlist …")
        playlist = spinitron.get_latest_playlist(config.show_name)
        show_date = playlist.start_time.date()

    click.echo(f"Playlist: {playlist.title} ({playlist.start_time} – {playlist.end_time})")
    click.echo(f"  {len(playlist.spins)} tracks")

    # --- Save JSON ---
    json_path = config.output_path / f"{show_date}.json"
    json_path.write_text(json.dumps(_playlist_to_dict(playlist), indent=2))
    click.echo(f"Saved tracklist → {json_path}")

    # --- Find Ark stream ---
    from czarchive.ark import find_ark_stream, download_show
    m3u8_url = find_ark_stream(config.station, show_date)
    if not m3u8_url:
        click.echo(
            f"Ark stream not yet available for {show_date}. "
            "(Usually appears ~2 weeks after broadcast.)",
            err=True,
        )
        sys.exit(1)

    click.echo(f"Ark stream: {m3u8_url}")

    # --- Download MP3 ---
    mp3_path = config.output_path / f"{show_date}.mp3"
    download_show(m3u8_url, playlist.start_time, playlist.end_time, mp3_path)
    click.echo(f"Saved audio → {mp3_path}")


# ---------------------------------------------------------------------------
# upload
# ---------------------------------------------------------------------------

@cli.command()
@click.option(
    "--file", "mp3_file",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="MP3 file to upload (default: most recently downloaded show)",
)
def upload(mp3_file: Path | None):
    """Upload a downloaded show to Mixcloud."""
    config = load_config()

    if mp3_file is None:
        # Find most recent .mp3 in output_dir
        mp3s = sorted(config.output_path.glob("*.mp3"), reverse=True)
        if not mp3s:
            click.echo(f"No .mp3 files found in {config.output_path}", err=True)
            sys.exit(1)
        mp3_file = mp3s[0]

    click.echo(f"Uploading: {mp3_file}")

    # Load matching JSON
    json_path = mp3_file.with_suffix(".json")
    if not json_path.exists():
        click.echo(f"Warning: no tracklist JSON found at {json_path}; uploading without tracklist.")
        playlist = None
    else:
        playlist = _playlist_from_dict(json.loads(json_path.read_text()))

    show_date = mp3_file.stem  # e.g. "2026-02-25"
    title = f"{config.show_name} — {show_date}"

    if playlist is None:
        from czarchive.spinitron import Playlist as PL
        from dateutil import parser as dp
        playlist = PL(
            id="unknown",
            title=title,
            start_time=datetime.now(PACIFIC),
            end_time=datetime.now(PACIFIC),
            spins=[],
        )

    from czarchive.mixcloud import upload_show
    url = upload_show(mp3_file, title, playlist, config)
    click.echo(f"Uploaded! {url}")


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

@cli.command()
@click.option(
    "--date", "show_date_str",
    default=None,
    help="Show date as YYYY-MM-DD (default: most recent episode)",
)
@click.pass_context
def run(ctx: click.Context, show_date_str: str | None):
    """Download then upload a show in one step."""
    ctx.invoke(download, show_date_str=show_date_str)

    config = load_config()
    if show_date_str:
        mp3_file = config.output_path / f"{show_date_str}.mp3"
    else:
        mp3s = sorted(config.output_path.glob("*.mp3"), reverse=True)
        mp3_file = mp3s[0] if mp3s else None

    if mp3_file and mp3_file.exists():
        ctx.invoke(upload, mp3_file=mp3_file)
    else:
        click.echo("Download did not produce an MP3 — skipping upload.", err=True)
        sys.exit(1)
