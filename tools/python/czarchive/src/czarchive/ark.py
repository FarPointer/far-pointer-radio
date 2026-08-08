"""Spinitron Ark audio stream discovery and ffmpeg-based download."""

from __future__ import annotations

import shutil
import subprocess
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

PACIFIC = ZoneInfo("America/Los_Angeles")
ARK_AVAIL_URL = "https://ark3.spinitron.com/cgi/avail/"


def _require_ffmpeg() -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "ffmpeg is not installed or not on PATH.\n"
            "Install it with: brew install ffmpeg  (macOS)\n"
            "or: sudo apt install ffmpeg  (Linux)"
        )


def find_ark_stream(station: str, show_date: date) -> str | None:
    """
    Query Ark availability endpoint and return the HLS m3u8 URL for
    the given station/date, or None if not yet available.

    The availability response is plain text, one URL per line, e.g.:
        https://ark3.spinitron.com/stream/KSER/2026/02/25/KSER-20260225T000000Z.m3u8
    """
    resp = requests.get(ARK_AVAIL_URL, params={"station": station}, timeout=15)
    resp.raise_for_status()

    date_str = show_date.strftime("%Y%m%d")
    for line in resp.text.splitlines():
        line = line.strip()
        if line and date_str in line and station in line:
            return line
    return None


def download_show(
    m3u8_url: str,
    start_time: datetime,
    end_time: datetime,
    output_path: Path,
) -> Path:
    """
    Download a segment of an HLS stream to an MP3 using ffmpeg.

    The Ark streams are continuous daily recordings.  We use -ss / -t to
    extract just the show window.

    start_time / end_time must be timezone-aware (America/Los_Angeles).
    The m3u8 stream starts at midnight Pacific on show_date.
    """
    _require_ffmpeg()

    # Ark streams start at midnight UTC on the recording date; convert to seconds offset.
    stream_origin = start_time.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    offset_secs = int((start_time - stream_origin).total_seconds())
    duration_secs = int((end_time - start_time).total_seconds())

    if duration_secs <= 0:
        raise ValueError(f"Invalid show window: start={start_time}, end={end_time}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",                       # overwrite output if exists
        "-i", m3u8_url,
        "-ss", str(offset_secs),
        "-t", str(duration_secs),
        "-c:a", "libmp3lame",
        "-q:a", "2",               # VBR ~190 kbps
        str(output_path),
    ]

    print(f"Downloading: offset={offset_secs}s duration={duration_secs}s → {output_path.name}")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg exited with code {result.returncode}")

    return output_path
