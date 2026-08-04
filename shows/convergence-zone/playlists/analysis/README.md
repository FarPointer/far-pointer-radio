# Playlist Analysis

Working files produced by reconciling `sources/` against what Spinitron actually
logged. These are worksheets for fixing the Spinitron record, not playlists
themselves — expect them to be superseded once the corrections are applied.

## Files

| File | Contents |
|---|---|
| `cz-missing-spins.xlsx` | Two-sheet reconciliation workbook covering MichaelG's episodes |
| `cz-removal-candidates.csv` | Flat export of the removal-candidate sheet, for diffing and scripting |

## cz-missing-spins.xlsx

| Sheet | Contents |
|---|---|
| `Add missing` | Tracks present in MichaelG's workbooks but absent from Spinitron, with a suggested insertion timestamp, a confidence rating, and the source sheet row. Gray rows sit in tight log windows and may not have actually aired — MichaelG confirms those. |
| `Remove or replace` | Spins logged in Spinitron with no counterpart in the workbooks. Amber rows carry a hint naming a nearby missing track the spin may actually be; those get **edited in place** rather than removed, and the matching row on `Add missing` is skipped. |

`cz-removal-candidates.csv` is the `Remove or replace` sheet as CSV, with the
amber hints in the `hint` column.
