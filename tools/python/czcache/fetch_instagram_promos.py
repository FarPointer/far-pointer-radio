"""Build `sources/instagram/promos.json` from reusable upstream exports.

Reuse-first inputs:
1. Instaloader metadata directory (`--instaloader-dir`) [recommended]
2. Meta Graph API (`--graph-token`, `--ig-user-id`)
3. Existing JSON dump (`--input-json`) shaped as `{"posts":[...]}` or a post list
"""
import argparse
import datetime as dt
import json
import lzma
import urllib.parse
import urllib.request
from pathlib import Path

from paths import INSTAGRAM_PROMOS


def _iso(ts):
    if ts is None:
        return ""
    if isinstance(ts, str):
        return ts
    try:
        return dt.datetime.fromtimestamp(int(ts), tz=dt.UTC).isoformat()
    except (TypeError, ValueError, OSError):
        return ""


def _caption_from_node(node):
    cap = node.get("caption")
    if cap:
        return str(cap)
    edges = ((node.get("edge_media_to_caption") or {}).get("edges") or [])
    if edges and isinstance(edges[0], dict):
        text = ((edges[0].get("node") or {}).get("text") or "").strip()
        if text:
            return text
    return ""


def _load_json_file(path: Path):
    if path.suffix == ".xz":
        with lzma.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    return json.loads(path.read_text(encoding="utf-8"))


def from_instaloader(root: Path):
    posts = []
    for path in sorted(root.rglob("*.json*")):
        if path.name == "promos.json":
            continue
        try:
            obj = _load_json_file(path)
        except Exception:
            continue
        node = obj.get("node") if isinstance(obj, dict) else None
        node = node if isinstance(node, dict) else (obj if isinstance(obj, dict) else {})
        pid = str(node.get("id") or obj.get("id") or "").strip()
        caption = _caption_from_node(node)
        if not pid or not caption.strip():
            continue
        shortcode = str(node.get("shortcode") or "").strip()
        permalink = f"https://www.instagram.com/p/{shortcode}/" if shortcode else ""
        posts.append({
            "id": pid,
            "timestamp": _iso(node.get("taken_at_timestamp")),
            "caption": caption,
            "permalink": permalink,
            "media_type": str(node.get("__typename") or ""),
            "source": "instaloader",
        })
    return posts


def _fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "far-pointer-radio czcache"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def from_graph_api(token: str, ig_user_id: str, api_version: str = "v25.0"):
    fields = "id,caption,timestamp,permalink,media_type"
    query = urllib.parse.urlencode({
        "fields": fields,
        "limit": 100,
        "access_token": token,
    })
    url = f"https://graph.facebook.com/{api_version}/{ig_user_id}/media?{query}"
    posts = []
    while url:
        data = _fetch_json(url)
        for p in data.get("data") or []:
            caption = str(p.get("caption") or "").strip()
            if not caption:
                continue
            posts.append({
                "id": str(p.get("id") or ""),
                "timestamp": str(p.get("timestamp") or ""),
                "caption": caption,
                "permalink": str(p.get("permalink") or ""),
                "media_type": str(p.get("media_type") or ""),
                "source": "graph_api",
            })
        url = ((data.get("paging") or {}).get("next") or "").strip() or None
    return posts


def from_input_json(path: Path):
    payload = _load_json_file(path)
    if isinstance(payload, dict) and isinstance(payload.get("posts"), list):
        posts = payload["posts"]
    elif isinstance(payload, list):
        posts = payload
    else:
        raise ValueError("input JSON must be a post list or {'posts': [...]} payload")

    out = []
    for p in posts:
        if not isinstance(p, dict):
            continue
        caption = str(p.get("caption") or "").strip()
        if not caption:
            continue
        out.append({
            "id": str(p.get("id") or ""),
            "timestamp": str(p.get("timestamp") or ""),
            "caption": caption,
            "permalink": str(p.get("permalink") or ""),
            "media_type": str(p.get("media_type") or ""),
            "source": str(p.get("source") or "input_json"),
        })
    return out


def dedupe(posts):
    by_id = {}
    for p in posts:
        pid = p.get("id") or ""
        key = pid or f"{p.get('timestamp')}::{p.get('caption', '')[:80]}"
        prior = by_id.get(key)
        if prior is None or len(p.get("caption", "")) > len(prior.get("caption", "")):
            by_id[key] = p
    return list(by_id.values())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=INSTAGRAM_PROMOS,
                    help="Output JSON path (default: sources/instagram/promos.json)")
    ap.add_argument("--instaloader-dir", type=Path,
                    help="Path containing Instaloader post metadata (.json/.json.xz)")
    ap.add_argument("--graph-token", help="Meta Graph API user token")
    ap.add_argument("--ig-user-id", help="Instagram professional account user ID")
    ap.add_argument("--input-json", type=Path,
                    help="Existing JSON post dump to normalize")
    args = ap.parse_args()

    if bool(args.graph_token) ^ bool(args.ig_user_id):
        raise SystemExit("Graph API ingestion requires both --graph-token and --ig-user-id.")

    feeds = []
    if args.instaloader_dir:
        feeds.append(("instaloader", from_instaloader(args.instaloader_dir)))
    if args.graph_token and args.ig_user_id:
        feeds.append(("graph_api", from_graph_api(args.graph_token, args.ig_user_id)))
    if args.input_json:
        feeds.append(("input_json", from_input_json(args.input_json)))
    if not feeds:
        raise SystemExit(
            "No input source provided. Use --instaloader-dir, or --graph-token with "
            "--ig-user-id, or --input-json."
        )

    merged = []
    for _, posts in feeds:
        merged.extend(posts)
    posts = sorted(dedupe(merged), key=lambda p: (p.get("timestamp") or "", p.get("id") or ""))

    payload = {
        "generated_at": dt.datetime.now(tz=dt.UTC).isoformat(),
        "source": "mixed" if len(feeds) > 1 else feeds[0][0],
        "posts": posts,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"posts written: {len(posts)}")
    print(f"output: {args.out}")


if __name__ == "__main__":
    main()
