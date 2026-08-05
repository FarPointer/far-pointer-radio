"""Discarded prototype for turning a Broadcast into WordPress payload pieces.

Reads the shape written by tools/python/czcache (see ../czcache/model.py and
../../../shows/convergence-zone/playlists/schema.ts) — this module doesn't
reimplement anything from czcache, it only renders the already-built cache.
"""

from __future__ import annotations

from datetime import datetime
from html import escape


def render_title(broadcast: dict) -> str:
    """'Convergence Zone – Ep. 53' or 'Convergence Zone – July 28, 2026'."""
    show_name = broadcast.get("show_name") or "Convergence Zone"
    episode_number = broadcast.get("episode_number")
    if episode_number:
        return f"{show_name} – Ep. {episode_number}"

    air_dt = datetime.fromisoformat(broadcast["air_datetime"])
    return f"{show_name} – {air_dt.strftime('%B %-d, %Y')}"


def render_hosts(broadcast: dict) -> list[str]:
    """Host names for the `host` taxonomy, in participants[] order, deduped."""
    seen = []
    for p in broadcast.get("participants", []):
        name = p.get("name")
        if name and name not in seen:
            seen.append(name)
    return seen


def render_description(broadcast: dict) -> str | None:
    """The approved description, or None.

    Deliberately returns None (not the raw text) when description_status is
    anything other than "approved" — publishing a "proposed" (unreviewed)
    description would put un-vetted prose on the live site. See
    playlists/schema-rationale.md on description_status.
    """
    if broadcast.get("description_status") != "approved":
        return None
    return broadcast.get("description")


def render_spinitron_url(broadcast: dict, station: str, fallback_url: str) -> str:
    """Best-effort direct link; spinitron_playlist_ids may legitimately be empty."""
    ids = broadcast.get("spinitron_playlist_ids") or []
    if ids:
        return f"https://spinitron.com/{station}/pl/{ids[0]}"
    return fallback_url


def _spin_sort_key(spin: dict) -> int:
    return spin.get("sequence") or 0


def render_tracklist_table_block(broadcast: dict) -> str:
    """A core/table block (Gutenberg HTML) for post_content.

    Not read back from custom fields at render time — the cz_tracklist SCF
    repeater holds the same data for querying, but the actual displayed table
    is this pre-rendered markup, written once at publish time. See
    wp-plugin/cz-playlists/README.md for why block bindings can't do this.
    """
    spins = sorted(broadcast.get("spins", []), key=_spin_sort_key)

    rows = []
    for spin in spins:
        artist = escape(spin.get("artist") or "")
        song = escape(spin.get("song") or "")
        release = escape(spin.get("release") or "")
        note = escape(spin.get("publish_note") or "")
        rows.append(
            "<tr>"
            f"<td>{artist}</td><td>{song}</td><td>{release}</td><td>{note}</td>"
            "</tr>"
        )

    body = "".join(rows)
    table_html = (
        '<figure class="wp-block-table">'
        "<table>"
        "<thead><tr><th>Artist</th><th>Song</th><th>Release</th><th>Notes</th></tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
        "</figure>"
    )
    return f"<!-- wp:table -->\n{table_html}\n<!-- /wp:table -->"


def render_mixcloud_embed_block(mixcloud_url: str) -> str:
    """A core/embed block. Only call this when mixcloud_url is not None —
    freshly-aired episodes won't have one yet (see two-pass publishing note
    in tools/python/czpublish/README.md)."""
    url = escape(mixcloud_url, quote=True)
    return (
        '<!-- wp:embed {"url":"'
        + url
        + '","type":"rich","providerNameSlug":"mixcloud","responsive":true} -->\n'
        '<figure class="wp-block-embed is-type-rich is-provider-mixcloud '
        'wp-block-embed-mixcloud wp-embed-aspect-16-9 wp-has-aspect-ratio">'
        f"<div class=\"wp-block-embed__wrapper\">\n{escape(mixcloud_url, quote=True)}\n</div>"
        "</figure>\n"
        "<!-- /wp:embed -->"
    )


def render_post_content(broadcast: dict) -> str:
    """post_content: tracklist table, plus a Mixcloud embed if archived yet."""
    blocks = [render_tracklist_table_block(broadcast)]
    mixcloud_url = broadcast.get("mixcloud_url")
    if mixcloud_url:
        blocks.append(render_mixcloud_embed_block(mixcloud_url))
    return "\n\n".join(blocks)
