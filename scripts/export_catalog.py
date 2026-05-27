"""Export the processed beer catalog to JSON for the Next.js web app.

Reads data/processed/beers.parquet and writes public/data/beers.json
with only the columns the frontend needs, floats rounded to 2 dp.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PARQUET = ROOT / "data" / "processed" / "beers.parquet"
OUT_DIR = ROOT / "public" / "data"
OUT_FILE = OUT_DIR / "beers.json"

COLUMNS = [
    "beer_id", "name", "brewery", "style", "country",
    "abv", "ibu", "srm",
    "bitterness", "sweetness", "maltiness", "hoppiness",
    "body", "sourness", "abv_normalized",
]


def main() -> None:
    df = pd.read_parquet(PARQUET)
    df = df[COLUMNS].copy()
    for col in df.select_dtypes(include="float").columns:
        df[col] = df[col].round(2)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records = df.to_dict(orient="records")
    OUT_FILE.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(records)} beers to {OUT_FILE} ({OUT_FILE.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
