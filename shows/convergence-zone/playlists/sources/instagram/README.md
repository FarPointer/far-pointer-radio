# Instagram promo source data

Raw and normalized promo-copy artifacts from `@converge.fm`.

## Files

| File | Purpose |
|---|---|
| `promos.json` | Normalized caption feed consumed by `tools/python/czcache/load_instagram.py` |

## Format (`promos.json`)

```json
{
  "generated_at": "2026-08-05T23:59:59Z",
  "source": "instaloader|graph_api|data_download|mixed",
  "posts": [
    {
      "id": "1789...",
      "timestamp": "2026-07-28T18:04:00+00:00",
      "caption": "This week on Convergence Zone ...",
      "permalink": "https://www.instagram.com/p/ABC123/",
      "media_type": "IMAGE",
      "source": "graph_api"
    }
  ]
}
```

Only `id`, `timestamp`, and `caption` are required per post. Additional fields are
preserved when available.
