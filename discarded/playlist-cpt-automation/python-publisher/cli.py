"""Discarded czpublish CLI prototype; do not use for live publishing."""

from __future__ import annotations

import json
import sys

import click

from czpublish.config import load_config, load_credentials
from czpublish.paths import BROADCASTS
from czpublish.render import (
    render_description,
    render_hosts,
    render_post_content,
    render_spinitron_url,
    render_title,
)
from czpublish.wordpress import WordPressClient


def _load_broadcast(date_str: str) -> dict:
    path = BROADCASTS / f"{date_str}.json"
    if not path.exists():
        raise click.ClickException(f"No cached broadcast at {path}")
    return json.loads(path.read_text())


def _build_payload(broadcast: dict, config, host_term_ids: list[int] | None) -> dict:
    payload = {
        "title": render_title(broadcast),
        "content": render_post_content(broadcast),
        "status": "draft",
        "meta": {
            "cz_air_datetime": broadcast["air_datetime"],
            "cz_episode_number": broadcast.get("episode_number") or 0,
            "cz_mixcloud_url": broadcast.get("mixcloud_url") or "",
            "cz_spinitron_playlist_url": render_spinitron_url(
                broadcast, config.station, config.spinitron_fallback_url
            ),
        },
    }
    description = render_description(broadcast)
    if description is not None:
        payload["meta"]["cz_description"] = description
    payload["meta"]["cz_description_status"] = broadcast.get("description_status") or ""

    if host_term_ids is not None:
        payload["host"] = host_term_ids

    return payload


@click.group()
def cli():
    """czpublish — publish Convergence Zone playlist pages to WordPress."""


@cli.command()
@click.argument("date_str", metavar="YYYY-MM-DD")
@click.option("--publish", "do_publish", is_flag=True, help="Set status=publish instead of draft.")
@click.option(
    "--dry-run", is_flag=True, help="Print the payload that would be sent; don't call the API."
)
def publish(date_str: str, do_publish: bool, dry_run: bool):
    """Create or update the WordPress playlist post for one cached broadcast.

    Safe to re-run: it looks up the existing post by cz_air_datetime and
    updates it rather than creating a duplicate — this is how the two-pass
    publish works (run once at air time, run again once czarchive has
    uploaded to Mixcloud to fill in cz_mixcloud_url and the embed).
    """
    broadcast = _load_broadcast(date_str)
    config = load_config()

    if dry_run:
        payload = _build_payload(broadcast, config, host_term_ids=None)
        payload["host_names"] = render_hosts(broadcast)  # shown in place of resolved term ids
        if do_publish:
            payload["status"] = "publish"
        click.echo(json.dumps(payload, indent=2))
        return

    credentials = load_credentials()
    client = WordPressClient(config, credentials)

    host_names = render_hosts(broadcast)
    host_term_ids = client.ensure_host_term_ids(host_names) if host_names else []

    payload = _build_payload(broadcast, config, host_term_ids)
    if do_publish:
        payload["status"] = "publish"

    result = client.create_or_update_playlist(payload)
    click.echo(f"OK: {result.get('link', result.get('id'))}")


@cli.command(name="publish-all")
@click.option("--publish", "do_publish", is_flag=True, help="Set status=publish instead of draft.")
@click.option("--dry-run", is_flag=True, help="Print payloads; don't call the API.")
def publish_all(do_publish: bool, dry_run: bool):
    """Publish/update every cached broadcast under playlists/cache/broadcasts/."""
    paths = sorted(BROADCASTS.glob("*.json"))
    if not paths:
        raise click.ClickException(f"No broadcasts found under {BROADCASTS}")

    for path in paths:
        date_str = path.stem
        click.echo(f"--- {date_str} ---")
        ctx = click.get_current_context()
        ctx.invoke(publish, date_str=date_str, do_publish=do_publish, dry_run=dry_run)


if __name__ == "__main__":
    cli()
