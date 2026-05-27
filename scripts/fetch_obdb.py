"""Download OpenBeerDB raw CSVs into data/raw/obdb/.

Pinned to a specific commit of jpargudo/pgOpenBeerDB for reproducibility.
Skips files already on disk unless --force is passed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

OBDB_REPO = "jpargudo/pgOpenBeerDB"
OBDB_REF = "ef7e103861f2299e65fbcfab074a891d85333d65"
BASE_URL = (
    f"https://raw.githubusercontent.com/{OBDB_REPO}/{OBDB_REF}/openbeerdb_csv"
)
FILES = ("beers.csv", "breweries.csv", "styles.csv", "LICENCE.txt")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "obdb"


def fetch(force: bool = False) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        target = OUT / name
        if target.exists() and not force:
            print(f"skip {name} (already on disk; pass --force to redownload)")
            continue
        url = f"{BASE_URL}/{name}"
        print(f"GET  {url}")
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        target.write_bytes(r.content)
        print(f"  -> wrote {target} ({len(r.content)} bytes)")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--force", action="store_true", help="redownload even if present")
    args = p.parse_args(argv)
    fetch(force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
