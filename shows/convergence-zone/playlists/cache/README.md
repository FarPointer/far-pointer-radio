# Playlist Cache

The canonical datastore of Convergence Zone broadcasts and spins, conforming to
`../schema.ts`. Generated — never hand-edited.

Built by `tools/python/czcache/`. To change what lands here, change a source under
`../sources/`, record a decision in `tools/python/czcache/overrides/`, or fix the build;
then rebuild. A hand edit is lost on the next run.

## Contents

| Path | Contents |
|---|---|
| `index.json` | One summary row per broadcast — id, date, episode number, merge class, spin count, participants, repeat pointer, description status |
| `broadcasts/YYYY-MM-DD.json` | A full `Broadcast` record with its `Spin` list nested |

Spins nest inside their broadcast rather than living in a parallel file: they belong to a
single airing, a broadcast is the natural unit to review in a pull request, and nesting
makes the schema's `broadcast_id` foreign key implicit instead of something to keep in
sync.

## Reading it

- `first_broadcast_id` names the **original** airing, never the previous one, so repeat
  chains never form. Repeats are self-contained — content is copied, not referenced.
- `evidence` says how much to trust a spin: `logged` (a source recorded it as played),
  `planned` (from a pre-air set list only — it may never have aired).
- `local` is three-state. `null` means *not yet assessed*, which is not the same as
  `false`. `local_basis` records why a spin counts as local (`artist`, `label`, `dj_flag`).
- `dj_ids` records which Spinitron login was used, **not who hosted**. Use `participants`.
- `spinitron_playlist_ids` comes from the public Spinitron show-history snapshot. Most
  broadcasts have one; six persona-switch broadcasts have two.
- `description_status` distinguishes human-approved copy from an unreviewed extraction.
  Treat `"proposed"` as a draft — it has not been read by a person.
- `mixcloud_url` is intentionally nullable. A page can be published without an embed and
  updated later after the recording URL is added to `../publication-links.json`.
