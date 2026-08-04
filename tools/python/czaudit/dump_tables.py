"""Print the header and first rows of each table in a OneNote export, for inspection.

Nothing here parses a playlist -- this exists to establish a column map by eye before
extract.py is trusted with a new file. The OneNote tables share no schema: column order
varies (Episode.065 lists Album before Song), and several have no real header row at all
because the exporter promoted the first data row into <th>. Guessing positionally
transposes whole episodes silently, so every file added to extract.SPECS should be looked
at here first.

    python dump_tables.py <file-or-directory> [...] [--rows N]

With no path, walks the whole OneNote source directory.
"""
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

BASE = (Path(__file__).resolve().parents[3]
        / "shows/convergence-zone/playlists/sources/farpointer-onenote")


def cell_text(el) -> str:
    txt = el.get_text(" ", strip=True).replace("---", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", txt).strip()


def dump(path: Path, nrows: int) -> bool:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
    tables = soup.find_all("table")
    if not tables:
        return False
    print("=" * 100)
    print(path.relative_to(BASE) if BASE in path.parents else path.name)
    for ti, table in enumerate(tables):
        ths = [cell_text(t) for t in table.find_all("th")]
        body = [tr for tr in table.find_all("tr") if tr.find_all("td")]
        print(f"  -- table {ti}: {len(body)} body rows")
        if ths:
            print(f"     TH : {ths}")
        for tr in body[:nrows]:
            print(f"     ROW: {[cell_text(td) for td in tr.find_all('td')]}")
    return True


def main():
    args = [a for a in sys.argv[1:] if a != "--rows"]
    nrows = 3
    if "--rows" in sys.argv:
        i = sys.argv.index("--rows")
        nrows = int(sys.argv[i + 1])
        args = [a for a in args if a != sys.argv[i + 1]]

    targets = [Path(a) for a in args] or [BASE]
    files = []
    for t in targets:
        files.extend(sorted(t.rglob("*.md")) if t.is_dir() else [t])

    shown = sum(dump(f, nrows) for f in files)
    print(f"\n{shown} of {len(files)} files contain a table")


if __name__ == "__main__":
    main()
