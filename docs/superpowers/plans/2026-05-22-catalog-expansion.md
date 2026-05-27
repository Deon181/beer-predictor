# Catalog Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hand-curated 262-beer catalog with a 500–1,000-beer catalog sourced from OpenBeerDB and selected by stratified sampling for better geographic and stylistic breadth.

**Architecture:** Four-stage pipeline (fetch → join+clean → normalize+sample → taste-vector). Stages 1–3 are new Python scripts; Stage 4 is the existing data-prep notebook, untouched if possible. A static `OBDB_TO_BJCP` alias dictionary maps OBDB's 143 style names to the BJCP keys already in `src/style_attributes.py`.

**Tech Stack:** Python 3.13, pandas, `requests` (already in `pyproject.toml`), pytest. No new dependencies.

**Note on git:** This repository is not a git repo (no `.git` directory at the project root). Per-task "commit" steps are omitted. If git is initialized later, group the work into logical commits at that time.

**Spec:** `docs/superpowers/specs/2026-05-22-catalog-expansion-design.md`

---

## File Structure

Files created or modified by this plan:

| Path | Action | Responsibility |
|---|---|---|
| `scripts/fetch_obdb.py` | create | Download OBDB raw CSVs from pinned GitHub commit |
| `data/raw/obdb/beers.csv` | create (via fetch) | OBDB beers (7,722 rows) |
| `data/raw/obdb/breweries.csv` | create (via fetch) | OBDB breweries (1,414 rows) |
| `data/raw/obdb/styles.csv` | create (via fetch) | OBDB styles (143 rows) |
| `data/raw/obdb/LICENCE.txt` | create (via fetch) | DbCL license text |
| `data/raw/obdb/ATTRIBUTION.md` | create | Attribution notice |
| `src/style_aliases.py` | create | `OBDB_TO_BJCP` mapping |
| `scripts/build_catalog.py` | create | Pipeline: join + clean + normalize + sample |
| `data/raw/curated_beers.csv` | overwrite | Final catalog (replaces 262-row file) |
| `data/raw/coverage_report.md` | create | Country/style distribution report |
| `tests/test_style_aliases.py` | create | Map validity tests |
| `tests/test_catalog.py` | create | Breadth invariants tests |
| `tests/test_data_prep.py` | modify | Bump min size, relax style count if needed |
| `README.md` | modify | Data-source + ODbL attribution |
| `scripts/build_raw_catalog.py` | delete | Replaced by `build_catalog.py` |

---

## Task 1: Set up obdb data directory and download script

**Files:**
- Create: `scripts/fetch_obdb.py`
- Create: `data/raw/obdb/.gitkeep` (empty placeholder)

- [ ] **Step 1.1: Verify the OBDB source URL with a HEAD request**

Run from the project root:
```powershell
$head = Invoke-WebRequest "https://raw.githubusercontent.com/jpargudo/pgOpenBeerDB/main/openbeerdb_csv/beers.csv" -Method Head -UseBasicParsing
$head.Headers["Content-Length"]
```
Expected: a content-length around `1187387` bytes.

- [ ] **Step 1.2: Resolve the latest commit SHA to pin**

```powershell
$ref = Invoke-RestMethod "https://api.github.com/repos/jpargudo/pgOpenBeerDB/commits/main"
$ref.sha
```
Expected: a 40-char SHA. Record it — it goes into `OBDB_REF` in the next step.

- [ ] **Step 1.3: Write `scripts/fetch_obdb.py`**

```python
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
# Pinned SHA — replace with the SHA from Step 1.2 before running.
OBDB_REF = "REPLACE_WITH_SHA_FROM_STEP_1_2"
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
```

- [ ] **Step 1.4: Run the fetch script**

```powershell
uv run python scripts/fetch_obdb.py
```
Expected output:
```
GET  https://raw.githubusercontent.com/jpargudo/pgOpenBeerDB/<sha>/openbeerdb_csv/beers.csv
  -> wrote .../data/raw/obdb/beers.csv (1187387 bytes)
GET  .../breweries.csv
  -> wrote .../data/raw/obdb/breweries.csv (~331197 bytes)
GET  .../styles.csv
  -> wrote .../data/raw/obdb/styles.csv (~8250 bytes)
GET  .../LICENCE.txt
  -> wrote .../data/raw/obdb/LICENCE.txt (~2378 bytes)
```

- [ ] **Step 1.5: Verify the files**

```powershell
Get-ChildItem "data/raw/obdb" | Select-Object Name,Length
```
Expected: four files with sizes matching the byte counts above.

---

## Task 2: Attribution file

**Files:**
- Create: `data/raw/obdb/ATTRIBUTION.md`

- [ ] **Step 2.1: Write the attribution file**

```markdown
# OpenBeerDB Attribution

This directory contains a snapshot of the [OpenBeerDB][obdb] public beer
catalog, mirrored at <https://github.com/jpargudo/pgOpenBeerDB>.

[obdb]: https://openbeerdb.com

## License

- **Database structure:** [Open Database License (ODbL)][odbl]
- **Database contents:** [Database Contents License (DbCL)][dbcl]
- Full license text: see `LICENCE.txt` in this directory.

[odbl]: https://opendatacommons.org/licenses/odbl/
[dbcl]: https://opendatacommons.org/licenses/dbcl/

## Required notice

> Contains information from OpenBeerDB (https://openbeerdb.com),
> which is made available here under the Open Database License (ODbL).

## Derivative

Files in `data/raw/obdb/` are an unmodified snapshot. The downstream
file `data/raw/curated_beers.csv` is a derivative produced by
`scripts/build_catalog.py` (joining, cleaning, style-normalizing, and
sampling). As a derivative it is shared under the same ODbL/DbCL terms.
```

---

## Task 3: Style alias module — test first, then skeleton

**Files:**
- Create: `tests/test_style_aliases.py`
- Create: `src/style_aliases.py`

- [ ] **Step 3.1: Write the failing test**

`tests/test_style_aliases.py`:
```python
"""Tests for the OBDB → BJCP style alias map."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.style_aliases import OBDB_TO_BJCP, to_bjcp
from src.style_attributes import STYLE_ATTRS

OBDB_STYLES = ROOT / "data" / "raw" / "obdb" / "styles.csv"


def test_every_mapped_value_is_a_valid_bjcp_key() -> None:
    bjcp_keys = set(STYLE_ATTRS.keys())
    bad = {k: v for k, v in OBDB_TO_BJCP.items() if v not in bjcp_keys}
    assert not bad, f"mapped values not in STYLE_ATTRS: {bad}"


def test_to_bjcp_returns_none_for_unmapped_style() -> None:
    assert to_bjcp("Definitely Not A Real Style") is None


def test_to_bjcp_returns_mapping_for_known_style() -> None:
    # Picks a row guaranteed to be in the map.
    assert to_bjcp("American-Style India Pale Ale") == "American IPA"


def test_map_covers_styles_needed_by_recommender_tests() -> None:
    """The recommender's extreme-profile tests depend on specific BJCP
    keys appearing in the final catalog. Confirm the alias map can
    produce each of them from at least one OBDB style."""
    required_bjcp = {
        "American IPA", "Imperial IPA", "American Barleywine",
        "Sweet Stout", "Imperial Stout", "Saison", "Doppelbock",
    }
    produced = set(OBDB_TO_BJCP.values())
    missing = required_bjcp - produced
    assert not missing, f"alias map cannot produce: {missing}"


@pytest.mark.skipif(not OBDB_STYLES.exists(), reason="run scripts/fetch_obdb.py first")
def test_alias_map_covers_at_least_half_of_obdb_styles() -> None:
    styles = pd.read_csv(OBDB_STYLES)
    obdb_names = set(styles["style_name"].dropna().astype(str))
    covered = obdb_names & set(OBDB_TO_BJCP.keys())
    ratio = len(covered) / max(1, len(obdb_names))
    assert ratio >= 0.5, f"only {ratio:.0%} of OBDB styles mapped ({len(covered)}/{len(obdb_names)})"
```

- [ ] **Step 3.2: Create a stub `src/style_aliases.py` that will fail the tests**

```python
"""Map OpenBeerDB style names → BJCP keys used by src/style_attributes.py.

OBDB ships 143 style names (in data/raw/obdb/styles.csv). Many map cleanly
to a BJCP equivalent in STYLE_ATTRS; a handful (specialty/honey/energy-drink
categories) have no good match and are intentionally absent. Rows whose
OBDB style is absent from this map are dropped during sampling.
"""
from __future__ import annotations

from typing import Mapping

# To be filled in Task 4.
OBDB_TO_BJCP: Mapping[str, str] = {}


def to_bjcp(obdb_style: str) -> str | None:
    """Return the BJCP key for an OBDB style, or None if unmapped."""
    return OBDB_TO_BJCP.get(obdb_style)
```

- [ ] **Step 3.3: Run the tests and confirm they fail**

```powershell
uv run pytest tests/test_style_aliases.py -v
```
Expected: `test_to_bjcp_returns_mapping_for_known_style` and the coverage tests FAIL because the map is empty. The "returns None" test PASSES.

---

## Task 4: Style alias map — full coverage

**Files:**
- Modify: `src/style_aliases.py` (replace `OBDB_TO_BJCP = {}`)

- [ ] **Step 4.1: Print the full OBDB style list**

```powershell
$styles = Import-Csv "data/raw/obdb/styles.csv"
$styles | Select-Object id, style_name | Format-Table -AutoSize | Out-String -Width 200
```
Read every style name. The list has 143 rows.

- [ ] **Step 4.2: Replace `OBDB_TO_BJCP = {}` in `src/style_aliases.py`**

Build the map deliberately, mapping each OBDB style to its closest BJCP key in `src/style_attributes.py` (or omit if no reasonable match exists).

Important constraints, verified by tests:
- Every value MUST be one of the keys in `STYLE_ATTRS` from `src/style_attributes.py`. The valid keys are:
  ```
  American IPA, Imperial IPA, Session IPA, New England IPA, American Pale Ale,
  English Pale Ale, Premium Bitter, Strong Bitter, Ordinary Bitter,
  Belgian Pale Ale, American Amber Ale, Irish Red Ale, American Amber Lager,
  British Brown Ale, American Brown Ale, English Porter, American Porter,
  Smoked Porter, Baltic Porter, Irish Stout, Sweet Stout, Oatmeal Stout,
  American Stout, Imperial Stout, Russian Imperial Stout, Foreign Extra Stout,
  Czech Pilsner, German Pilsner, Munich Helles, Munich Dunkel, Märzen,
  Vienna Lager, Schwarzbier, American Lager, American Light Lager,
  International Pale Lager, Doppelbock, Eisbock, Weizenbock, Hefeweizen,
  Dunkelweizen, Witbier, American Wheat, Berliner Weisse, Gose, Gueuze,
  Fruit Lambic, Flanders Red, Flanders Pale Ale, American Wild Ale,
  Belgian Tripel, Belgian Dubbel, Belgian Strong Pale, Belgian Strong Dark,
  Quadrupel, Saison, Rauchbier, Kölsch, Cream Ale, American Barleywine,
  English Barleywine, Old Ale, Wee Heavy, Scotch Ale, American Strong Ale,
  Christmas/Winter Ale, Wood-Aged Ale, Düsseldorf Altbier, Fruit Beer
  ```
- The required keys produced by the test (`test_map_covers_styles_needed_by_recommender_tests`) must each appear as a value at least once: `American IPA`, `Imperial IPA`, `American Barleywine`, `Sweet Stout`, `Imperial Stout`, `Saison`, `Doppelbock`.
- Skip OBDB styles that have no reasonable BJCP equivalent: `Energy Drinks`, `Specialty Honey Ale or Lager`, `Pumpkin Beer`, `Vegetable Beer`, `Chili Pepper Beer`, etc. — these correctly stay out of the map (the row gets dropped during sampling).
- The "Unknown" style (id=-1) must NOT be in the map.

Reference mappings (illustrative — the implementer should produce the full ~120-entry map by reading the OBDB style names directly):

```python
OBDB_TO_BJCP: Mapping[str, str] = {
    # English IPAs and Pale Ales
    "English-Style India Pale Ale":                   "American IPA",  # closest BJCP key by hop profile
    "American-Style India Pale Ale":                  "American IPA",
    "Imperial or Double India Pale Ale":              "Imperial IPA",
    "American-Style Pale Ale":                        "American Pale Ale",
    "Classic English-Style Pale Ale":                 "English Pale Ale",
    "Ordinary Bitter":                                "Ordinary Bitter",
    "Special Bitter or Best Bitter":                  "Premium Bitter",
    "Extra Special Bitter":                           "Strong Bitter",
    "Golden or Blonde Ale":                           "American Pale Ale",
    "American-Style Strong Pale Ale":                 "American Strong Ale",

    # Belgian & French
    "Belgian-Style Pale Ale":                         "Belgian Pale Ale",
    "Belgian-Style Dubbel":                           "Belgian Dubbel",
    "Belgian-Style Tripel":                           "Belgian Tripel",
    "Belgian-Style Quadrupel":                        "Quadrupel",
    "Belgian-Style Pale Strong Ale":                  "Belgian Strong Pale",
    "Belgian-Style Dark Strong Ale":                  "Belgian Strong Dark",
    "Belgian-Style White (or Wit) / Belgian-Style Wheat":  "Witbier",
    "Belgian-Style Lambic":                           "Gueuze",
    "Belgian-Style Gueuze Lambic":                    "Gueuze",
    "Belgian-Style Fruit Lambic":                     "Fruit Lambic",
    "Belgian-Style Flanders Oud Bruin or Oud Red Ales":  "Flanders Red",
    "French & Belgian-Style Saison":                  "Saison",
    "Bière de Garde":                                 "Saison",

    # German
    "Bohemian-Style Pilsener":                        "Czech Pilsner",
    "German-Style Pilsener":                          "German Pilsner",
    "Münchner-Style Helles":                          "Munich Helles",
    "Münchner-Style Dunkel":                          "Munich Dunkel",
    "Bamberg-Style Märzen Rauchbier (smoke beer)":    "Rauchbier",
    "Bavarian-Style Weizen / Weissbier":              "Hefeweizen",
    "South German-Style Bernsteinfarbenes Weizen / Weissbier":  "Hefeweizen",
    "South German-Style Dunkel Weizen / Dunkel Weissbier":      "Dunkelweizen",
    "South German-Style Weizenbock / Weissbock":      "Weizenbock",
    "Berliner-Style Weisse":                          "Berliner Weisse",
    "Leipzig-Style Gose":                             "Gose",
    "German-Style Schwarzbier":                       "Schwarzbier",
    "Vienna-Style Lager":                             "Vienna Lager",
    "German-Style Märzen / Oktoberfest":              "Märzen",
    "German-Style Doppelbock":                        "Doppelbock",
    "German-Style Eisbock":                           "Eisbock",
    "German-Style Heller Bock / Maibock":             "Doppelbock",
    "German-Style Brown Ale / Düsseldorf-Style Altbier":  "Düsseldorf Altbier",
    "German-Style Kölsch / Köln-Style Kölsch":        "Kölsch",

    # Brown / Amber / Red
    "American-Style Brown Ale":                       "American Brown Ale",
    "English-Style Brown Ale":                        "British Brown Ale",
    "Irish-Style Red Ale":                            "Irish Red Ale",
    "American-Style Amber/Red Ale":                   "American Amber Ale",
    "American-Style Amber Lager":                     "American Amber Lager",

    # Porter / Stout
    "Robust Porter":                                  "American Porter",
    "Brown Porter":                                   "English Porter",
    "Smoke Porter":                                   "Smoked Porter",
    "Baltic-Style Porter":                            "Baltic Porter",
    "American-Style Stout":                           "American Stout",
    "American-Style Imperial Stout":                  "Imperial Stout",
    "Sweet Stout":                                    "Sweet Stout",
    "Oatmeal Stout":                                  "Oatmeal Stout",
    "Foreign-Style Stout":                            "Foreign Extra Stout",
    "Classic Irish-Style Dry Stout":                  "Irish Stout",
    "Russian Imperial Stout":                         "Russian Imperial Stout",

    # Strong / Wood-aged
    "American-Style Barley Wine Ale":                 "American Barleywine",
    "British-Style Barley Wine Ale":                  "English Barleywine",
    "Old Ale":                                        "Old Ale",
    "Strong Scotch Ale":                              "Wee Heavy",
    "Scottish-Style Light Ale":                       "Scotch Ale",
    "Scottish-Style Heavy Ale":                       "Scotch Ale",
    "Scottish-Style Export Ale":                      "Scotch Ale",
    "Wood- and Barrel-aged Beer":                     "Wood-Aged Ale",
    "Wood- and Barrel-Aged Strong Beer":              "Wood-Aged Ale",
    "Wood- and Barrel-aged Pale to Amber Beer":       "Wood-Aged Ale",
    "Wood- and Barrel-aged Dark Beer":                "Wood-Aged Ale",
    "Wood- and Barrel-aged Sour Beer":                "American Wild Ale",

    # American & light lagers
    "American-Style Lager":                           "American Lager",
    "American-Style Light Lager":                     "American Light Lager",
    "American-Style Premium Lager":                   "American Lager",
    "American-Style Ice Lager":                       "American Lager",
    "American-Style Cream Ale or Lager":              "Cream Ale",
    "American-Style Wheat Beer":                      "American Wheat",
    "American-Style Wheat Wine Ale":                  "American Barleywine",
    "Australian-Style Pale Ale":                      "American Pale Ale",
    "International-Style Pale Ale":                   "American Pale Ale",
    "Tropical-Style Light Lager":                     "International Pale Lager",

    # Specialty mappings (best fit, dropped if no fit)
    "Fruit Beer":                                     "Fruit Beer",
    "Herb and Spice Beer":                            "Christmas/Winter Ale",
    "Winter Warmer":                                  "Christmas/Winter Ale",

    # ...
    # The implementer should add the remaining OBDB style names from
    # data/raw/obdb/styles.csv that have a reasonable BJCP equivalent.
    # Aim for ≥75 entries (50%+ of 143). Tests enforce the ≥50% floor.
}
```

> **Why the duplicates** (e.g., both `Strong Scotch Ale` and `Scottish-Style Heavy Ale` mapping to `Wee Heavy`/`Scotch Ale`): OBDB groups beers more granularly than BJCP. Collapsing them is the point.

- [ ] **Step 4.3: Run the alias tests**

```powershell
uv run pytest tests/test_style_aliases.py -v
```
Expected: all 5 tests PASS (including the 50%-coverage test).

---

## Task 5: build_catalog.py — Stage 2 (join + clean)

**Files:**
- Create: `scripts/build_catalog.py`
- Create: `tests/test_catalog.py` (header only — body in Task 7)

- [ ] **Step 5.1: Write `scripts/build_catalog.py` skeleton with the join+clean function**

```python
"""Build the curated beer catalog from the OBDB raw data.

Pipeline:
    Stage 2: JOIN + CLEAN      join_and_clean()
    Stage 3a: NORMALIZE        normalize_style()
    Stage 3b: STRATIFIED SAMPLE stratified_sample()
    Stage 3c: COVERAGE REPORT   write_coverage_report()

Run:
    uv run python scripts/build_catalog.py
    uv run python scripts/build_catalog.py --target-size 750 --seed 42
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.style_aliases import to_bjcp

RAW_OBDB = ROOT / "data" / "raw" / "obdb"
OUT_CURATED = ROOT / "data" / "raw" / "curated_beers.csv"
OUT_JOINED = ROOT / "data" / "raw" / "obdb_joined.csv"
OUT_COVERAGE = ROOT / "data" / "raw" / "coverage_report.md"

# Schema for the final curated_beers.csv (unchanged from the existing app):
CURATED_COLUMNS = ("beer_id", "name", "brewery", "style", "country", "abv", "ibu", "srm")

# Country name normalization: OBDB uses "United States" / "United Kingdom",
# but the curated catalog (and dashboard filters) historically use "USA" / "UK".
COUNTRY_NORMALIZATION = {
    "United States": "USA",
    "United Kingdom": "UK",
}


def join_and_clean(raw_dir: Path = RAW_OBDB) -> pd.DataFrame:
    """Stage 2: join beers ↔ breweries ↔ styles, drop unusable rows."""
    beers = pd.read_csv(raw_dir / "beers.csv")
    breweries = pd.read_csv(raw_dir / "breweries.csv")
    styles = pd.read_csv(raw_dir / "styles.csv")

    # Rename to avoid column collisions on join.
    beers = beers.rename(columns={"name": "name", "id": "beer_id"})
    breweries = breweries.rename(columns={"name": "brewery", "id": "brewery_id"})
    styles = styles.rename(columns={"id": "style_id", "style_name": "style_obdb"})

    df = beers.merge(breweries[["brewery_id", "brewery", "country"]], on="brewery_id", how="left")
    df = df.merge(styles[["style_id", "style_obdb"]], on="style_id", how="left")

    # Coerce numerics; OBDB uses 0 to mean missing for IBU/SRM.
    for col in ("abv", "ibu", "srm"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.loc[df["ibu"] == 0, "ibu"] = np.nan
    df.loc[df["srm"] == 0, "srm"] = np.nan
    df.loc[df["abv"] == 0, "abv"] = np.nan

    # Normalize country labels.
    df["country"] = df["country"].replace(COUNTRY_NORMALIZATION)

    # Drop rows missing any field required by the recommender.
    df = df.dropna(subset=["name", "brewery", "style_obdb", "country", "abv"])

    # Drop accidental duplicates (same name, same brewery).
    df = df.drop_duplicates(subset=["name", "brewery"])

    # Clip to plausible bounds (existing notebook does this too).
    df["abv"] = df["abv"].clip(lower=0, upper=20)
    df["ibu"] = df["ibu"].clip(lower=0, upper=120)

    # Project to a stable column order.
    df = df[["name", "brewery", "country", "style_obdb", "abv", "ibu", "srm"]].reset_index(drop=True)
    return df


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target-size", type=int, default=750)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    joined = join_and_clean()
    OUT_JOINED.parent.mkdir(parents=True, exist_ok=True)
    joined.to_csv(OUT_JOINED, index=False)
    print(f"joined+cleaned: {len(joined)} rows -> {OUT_JOINED}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5.2: Run the script — Stage 2 only for now**

```powershell
uv run python scripts/build_catalog.py
```
Expected output:
```
joined+cleaned: ~4500-6500 rows -> .../data/raw/obdb_joined.csv
```
Why the range: OBDB has 7,722 beers, but ~1,000 rows are missing ABV (=0), and a few hundred have null brewery/country.

- [ ] **Step 5.3: Spot-check the joined file**

```powershell
Get-Content "data/raw/obdb_joined.csv" -TotalCount 5
$joined = Import-Csv "data/raw/obdb_joined.csv"
"rows: $($joined.Count)"
"countries: $((($joined | Group-Object country).Count))"
"styles: $((($joined | Group-Object style_obdb).Count))"
$joined | Group-Object country | Sort-Object Count -Descending | Select-Object -First 5 Count,Name | Format-Table -AutoSize
```
Expected: ~5,000 rows, ~60+ countries, ~140 OBDB styles. Top country: USA (~3500), then Germany / Belgium / UK.

---

## Task 6: build_catalog.py — Stage 3a (style normalize)

**Files:**
- Modify: `scripts/build_catalog.py` (add `normalize_style`)

- [ ] **Step 6.1: Add the `normalize_style` function**

Insert below `join_and_clean` in `scripts/build_catalog.py`:

```python
def normalize_style(df: pd.DataFrame) -> pd.DataFrame:
    """Stage 3a: map OBDB style -> BJCP key; drop rows with unmapped style."""
    df = df.copy()
    df["style"] = df["style_obdb"].map(to_bjcp)
    dropped = df["style"].isna().sum()
    print(f"normalize_style: dropping {dropped} rows with unmapped OBDB style")
    df = df.dropna(subset=["style"])
    return df.drop(columns=["style_obdb"]).reset_index(drop=True)
```

- [ ] **Step 6.2: Call it from `main()`**

Replace the `main()` body with:

```python
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target-size", type=int, default=750)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    joined = join_and_clean()
    OUT_JOINED.parent.mkdir(parents=True, exist_ok=True)
    joined.to_csv(OUT_JOINED, index=False)
    print(f"joined+cleaned: {len(joined)} rows -> {OUT_JOINED}")

    normalized = normalize_style(joined)
    print(f"after style normalization: {len(normalized)} rows, {normalized['style'].nunique()} BJCP styles")
    return 0
```

- [ ] **Step 6.3: Run it and check the drop count**

```powershell
uv run python scripts/build_catalog.py
```
Expected output:
```
joined+cleaned: ~5000 rows -> .../obdb_joined.csv
normalize_style: dropping <N> rows with unmapped OBDB style
after style normalization: ~3000-4500 rows, ~60+ BJCP styles
```
If the drop count is more than ~40% of the input, the alias map needs more entries — return to Task 4 and add the high-volume unmapped styles. The script prints them in Task 8's coverage report; for now you can check manually:

```powershell
$j = Import-Csv "data/raw/obdb_joined.csv"
$j | Group-Object style_obdb | Sort-Object Count -Descending | Select-Object -First 30 Count,Name | Format-Table -AutoSize
```

---

## Task 7: build_catalog.py — Stage 3b (stratified sample)

**Files:**
- Modify: `scripts/build_catalog.py` (add `stratified_sample`)

- [ ] **Step 7.1: Add the `stratified_sample` function**

Insert below `normalize_style`:

```python
def stratified_sample(
    df: pd.DataFrame, target_size: int = 750, seed: int = 42
) -> pd.DataFrame:
    """Stage 3b: stratified sample with three-tier caps.

    Caps:
        per (country, style) cell: 6
        per style: ceil(0.08 * target_size)
        per country: ceil(0.35 * target_size)

    Order matters: (country, style) cap first so no country can monopolize
    one style, then per-style cap, then per-country cap. Each subsequent
    cap drops surplus rows preferring to keep diversity on the other axis.
    """
    rng = np.random.default_rng(seed)
    max_per_cell = 6
    max_per_style = math.ceil(0.08 * target_size)
    max_per_country = math.ceil(0.35 * target_size)

    def shuffle(group: pd.DataFrame) -> pd.DataFrame:
        idx = rng.permutation(len(group))
        return group.iloc[idx]

    # 1. Per-(country, style) cell cap.
    capped = (
        df.groupby(["country", "style"], group_keys=False)
        .apply(lambda g: shuffle(g).head(max_per_cell))
        .reset_index(drop=True)
    )

    # 2. Per-style cap — when a style is too big, prefer diverse countries:
    #    keep up to one row per country first, then fill with extras.
    def cap_per_style(group: pd.DataFrame) -> pd.DataFrame:
        if len(group) <= max_per_style:
            return group
        first_per_country = group.groupby("country", group_keys=False).head(1)
        rest = group.drop(first_per_country.index)
        rest_shuffled = shuffle(rest)
        slots = max_per_style - len(first_per_country)
        if slots > 0:
            return pd.concat([first_per_country, rest_shuffled.head(slots)])
        return first_per_country.head(max_per_style)

    capped = (
        capped.groupby("style", group_keys=False)
        .apply(cap_per_style)
        .reset_index(drop=True)
    )

    # 3. Per-country cap — analogous, prefer diverse styles within country.
    def cap_per_country(group: pd.DataFrame) -> pd.DataFrame:
        if len(group) <= max_per_country:
            return group
        first_per_style = group.groupby("style", group_keys=False).head(1)
        rest = group.drop(first_per_style.index)
        rest_shuffled = shuffle(rest)
        slots = max_per_country - len(first_per_style)
        if slots > 0:
            return pd.concat([first_per_style, rest_shuffled.head(slots)])
        return first_per_style.head(max_per_country)

    capped = (
        capped.groupby("country", group_keys=False)
        .apply(cap_per_country)
        .reset_index(drop=True)
    )

    # 4. Final size adjustment.
    if len(capped) > target_size:
        capped = shuffle(capped).head(target_size).reset_index(drop=True)

    # Assign sequential beer_id starting at 1.
    capped.insert(0, "beer_id", range(1, len(capped) + 1))
    return capped[list(CURATED_COLUMNS)]
```

- [ ] **Step 7.2: Wire it into `main()` and write the final CSV**

Replace the `main()` body again:

```python
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target-size", type=int, default=750)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    joined = join_and_clean()
    OUT_JOINED.parent.mkdir(parents=True, exist_ok=True)
    joined.to_csv(OUT_JOINED, index=False)
    print(f"joined+cleaned: {len(joined)} rows -> {OUT_JOINED}")

    normalized = normalize_style(joined)
    print(f"after style normalization: {len(normalized)} rows, {normalized['style'].nunique()} BJCP styles")

    sampled = stratified_sample(normalized, target_size=args.target_size, seed=args.seed)
    sampled.to_csv(OUT_CURATED, index=False)
    print(f"final catalog: {len(sampled)} rows -> {OUT_CURATED}")
    print(f"countries: {sampled['country'].nunique()}, styles: {sampled['style'].nunique()}")
    return 0
```

- [ ] **Step 7.3: Run it**

```powershell
uv run python scripts/build_catalog.py
```
Expected:
```
joined+cleaned: ~5000 rows -> .../obdb_joined.csv
normalize_style: dropping <N> rows with unmapped OBDB style
after style normalization: ~3500 rows, ~60+ BJCP styles
final catalog: ~750 rows -> .../curated_beers.csv
countries: 20-30, styles: 50-65
```

- [ ] **Step 7.4: Eyeball the result**

```powershell
$c = Import-Csv "data/raw/curated_beers.csv"
"rows: $($c.Count)"
"countries: $((($c | Group-Object country).Count))"
"styles: $((($c | Group-Object style).Count))"
$c | Group-Object country | Sort-Object Count -Descending | Select-Object -First 10 Count,Name | Format-Table -AutoSize
$c | Group-Object style | Sort-Object Count -Descending | Select-Object -First 10 Count,Name | Format-Table -AutoSize
```
Expected: USA at most ~263 (35% of 750), top styles at most ~60 (8% of 750).

---

## Task 8: build_catalog.py — Stage 3c (coverage report)

**Files:**
- Modify: `scripts/build_catalog.py` (add `write_coverage_report`)

- [ ] **Step 8.1: Add the report function**

Insert below `stratified_sample`:

```python
def write_coverage_report(
    joined: pd.DataFrame,
    normalized: pd.DataFrame,
    sampled: pd.DataFrame,
    out: Path = OUT_COVERAGE,
) -> None:
    """Markdown summary of what the pipeline kept and dropped."""
    dropped_styles = (
        joined.loc[joined["style_obdb"].map(to_bjcp).isna()]
        .groupby("style_obdb")
        .size()
        .sort_values(ascending=False)
    )
    top_dropped = dropped_styles.head(10)

    lines: list[str] = ["# Catalog Coverage Report", ""]
    lines += [
        f"- joined rows (pre-normalize): **{len(joined)}**",
        f"- after style normalization: **{len(normalized)}**",
        f"- final sampled catalog: **{len(sampled)}**",
        "",
        "## Top 10 OBDB styles dropped (no BJCP alias)",
        "",
        "| OBDB style | rows dropped |",
        "|---|---|",
    ]
    for style, n in top_dropped.items():
        lines.append(f"| {style} | {n} |")

    lines += ["", "## Country distribution (final)", "", "| country | rows | share |", "|---|---|---|"]
    total = len(sampled)
    for country, n in sampled["country"].value_counts().items():
        lines.append(f"| {country} | {n} | {n/total:.1%} |")

    lines += ["", "## Style distribution (final, top 30)", "", "| style | rows | share |", "|---|---|---|"]
    for style, n in sampled["style"].value_counts().head(30).items():
        lines.append(f"| {style} | {n} | {n/total:.1%} |")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"coverage report: {out}")
```

- [ ] **Step 8.2: Call it from `main()`**

Replace `main()` once more:

```python
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target-size", type=int, default=750)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    joined = join_and_clean()
    OUT_JOINED.parent.mkdir(parents=True, exist_ok=True)
    joined.to_csv(OUT_JOINED, index=False)
    print(f"joined+cleaned: {len(joined)} rows -> {OUT_JOINED}")

    normalized = normalize_style(joined)
    print(f"after style normalization: {len(normalized)} rows, {normalized['style'].nunique()} BJCP styles")

    sampled = stratified_sample(normalized, target_size=args.target_size, seed=args.seed)
    sampled.to_csv(OUT_CURATED, index=False)
    print(f"final catalog: {len(sampled)} rows -> {OUT_CURATED}")
    print(f"countries: {sampled['country'].nunique()}, styles: {sampled['style'].nunique()}")

    write_coverage_report(joined, normalized, sampled)
    return 0
```

- [ ] **Step 8.3: Re-run and read the report**

```powershell
uv run python scripts/build_catalog.py
Get-Content "data/raw/coverage_report.md"
```
If the top dropped-OBDB-style is something with a clean BJCP equivalent, return to Task 4 and add it to the alias map.

---

## Task 9: Breadth invariant tests on the regenerated catalog

**Files:**
- Create: `tests/test_catalog.py`

- [ ] **Step 9.1: Write the tests**

```python
"""Breadth invariants for the regenerated curated catalog."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.style_attributes import STYLE_ATTRS

CATALOG = ROOT / "data" / "raw" / "curated_beers.csv"


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    assert CATALOG.exists(), "run scripts/build_catalog.py first"
    return pd.read_csv(CATALOG)


def test_minimum_size(df: pd.DataFrame) -> None:
    assert len(df) >= 500, f"catalog has only {len(df)} rows"


def test_schema(df: pd.DataFrame) -> None:
    expected = {"beer_id", "name", "brewery", "style", "country", "abv", "ibu", "srm"}
    missing = expected - set(df.columns)
    assert not missing, f"missing columns: {missing}"


def test_diverse_countries(df: pd.DataFrame) -> None:
    assert df["country"].nunique() >= 20


def test_diverse_styles(df: pd.DataFrame) -> None:
    assert df["style"].nunique() >= 50


def test_no_country_dominates(df: pd.DataFrame) -> None:
    counts = df["country"].value_counts(normalize=True)
    top_share = counts.iloc[0]
    assert top_share <= 0.36, f"top country {counts.index[0]} holds {top_share:.1%}"


def test_no_style_dominates(df: pd.DataFrame) -> None:
    counts = df["style"].value_counts(normalize=True)
    top_share = counts.iloc[0]
    assert top_share <= 0.085, f"top style {counts.index[0]} holds {top_share:.1%}"


def test_every_style_is_in_bjcp_table(df: pd.DataFrame) -> None:
    unknown = set(df["style"]) - set(STYLE_ATTRS.keys())
    assert not unknown, f"styles missing from STYLE_ATTRS: {unknown}"


def test_unique_beer_ids(df: pd.DataFrame) -> None:
    assert df["beer_id"].is_unique


def test_abv_within_bounds(df: pd.DataFrame) -> None:
    assert df["abv"].between(0, 20).all()


def test_has_high_abv_beers_for_filter_tests(df: pd.DataFrame) -> None:
    """test_recommender.test_filters_min_max_abv needs beers in [8, 12]."""
    assert ((df["abv"] >= 8.0) & (df["abv"] <= 12.0)).sum() >= 5


def test_has_saison_for_filter_test(df: pd.DataFrame) -> None:
    """test_recommender.test_filters_styles uses 'Saison'."""
    assert (df["style"] == "Saison").any()
```

- [ ] **Step 9.2: Run the new tests**

```powershell
uv run pytest tests/test_catalog.py -v
```
Expected: all PASS. If any breadth test fails, the alias map or quotas need tweaking — re-open Task 4 or revisit the cap constants in `stratified_sample`.

---

## Task 10: Rebuild the processed parquet and verify existing tests

**Files:**
- May modify: `notebooks/data_prep.ipynb` (only if existing IBU backfill is insufficient)
- May modify: `tests/test_data_prep.py` (only to bump thresholds upward)

- [ ] **Step 10.1: Re-execute the data-prep notebook**

```powershell
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/data_prep.ipynb
```
Expected: notebook runs to completion, writing `data/processed/beers.parquet`. The "Sanity checks passed for N beers across M styles" line should show N ≈ 750.

- [ ] **Step 10.2: If the notebook fails on a null-IBU style group**

Edit cell 4 in `notebooks/data_prep.ipynb` (the "Clean" cell). The current code is:
```python
df['ibu'] = df.groupby('style')['ibu'].transform(lambda s: s.fillna(s.mean()))
df['ibu'] = df['ibu'].fillna(df['ibu'].mean())
```
If after the first line some IBUs remain null (a style with 100% null IBU), the second `fillna` catches them. If they STILL remain null, replace the block with:
```python
df['ibu'] = df.groupby('style')['ibu'].transform(lambda s: s.fillna(s.mean()))
# Fall back to style-baseline-derived bitterness for any style with 100% null IBU.
from src.style_attributes import style_lookup
def _baseline_ibu(style):
    return style_lookup(style)[2] * 10.0  # hop_base on 0-10 -> back to IBU
df.loc[df['ibu'].isna(), 'ibu'] = df.loc[df['ibu'].isna(), 'style'].map(_baseline_ibu)
df['ibu'] = df['ibu'].fillna(df['ibu'].mean())
```
Rerun Step 10.1.

- [ ] **Step 10.3: Run the existing test suite**

```powershell
uv run pytest tests/ -v
```
Expected: ALL tests pass. If `test_data_prep.py::test_minimum_catalog_size` or `test_diverse_styles` fail because the thresholds are stale-low rather than because the catalog is bad, bump them upward:
```python
def test_minimum_catalog_size(df: pd.DataFrame) -> None:
    assert len(df) >= 500   # was 100

def test_diverse_styles(df: pd.DataFrame) -> None:
    assert df["style"].nunique() >= 50   # was 30
```

- [ ] **Step 10.4: Verify the recommender extreme-profile tests still pass**

Run specifically:
```powershell
uv run pytest tests/test_recommender.py::test_recommend_extreme_bitterness_pulls_hoppy_styles tests/test_recommender.py::test_recommend_extreme_sweetness_pulls_sweet_styles tests/test_recommender.py::test_filters_styles tests/test_recommender.py::test_filters_min_max_abv -v
```
Expected: all PASS. If any fail, the alias map needs an extra entry to ensure the required style appears in the catalog — return to Task 4.

---

## Task 11: Smoke-launch the dashboard

**Files:** none modified — verification only.

- [ ] **Step 11.1: Start the dashboard**

```powershell
uv run python dashboard/app.py
```
Expected: server starts on http://127.0.0.1:8050 without errors.

- [ ] **Step 11.2: Visually confirm**

Open http://127.0.0.1:8050 in a browser. Move the sliders to an extreme (bitterness=10, hoppiness=10, sweetness=0). Confirm:
- Results display.
- The top result is hop-forward (IPA family).
- The style and country filters are populated with the new, broader options (~50+ styles, ~20+ countries).

Stop the server with Ctrl+C.

---

## Task 12: README + cleanup

**Files:**
- Modify: `README.md`
- Delete: `scripts/build_raw_catalog.py`

- [ ] **Step 12.1: Update `README.md`**

Replace the "Dataset" section (lines ~11–33) with:

```markdown
## Dataset

The catalog is a ~750-beer subset of [OpenBeerDB][obdb] (a public catalog
of ~7,700 beers across 1,400+ breweries in 50+ countries), selected by
stratified sampling for breadth across style and country. Each row carries
name, brewery, style, country, ABV, IBU, and SRM. Style baselines for the
taste-vector attributes come from the [BJCP 2021 Style Guidelines][bjcp]
(publicly available; only factual style descriptors are referenced — no
copyrighted prose is reproduced).

[obdb]: https://openbeerdb.com
[bjcp]: https://www.bjcp.org/style/2021/

The pipeline is:

1. `scripts/fetch_obdb.py` — downloads OBDB raw CSVs to `data/raw/obdb/`
   (pinned to a specific commit hash for reproducibility).
2. `scripts/build_catalog.py` — joins OBDB beers/breweries/styles, drops
   rows missing required fields, maps OBDB style names to BJCP keys via
   `src/style_aliases.py`, and stratified-samples to ~750 rows with
   per-country / per-style / per-cell caps. Writes
   `data/raw/curated_beers.csv` and a `coverage_report.md` summary.
3. `notebooks/data_prep.ipynb` — engineers the 7-axis taste vector and
   writes `data/processed/beers.parquet`.

**Attribution:** Contains information from [OpenBeerDB](https://openbeerdb.com),
made available under the [Open Database License (ODbL)][odbl]. The derived
`curated_beers.csv` is shared under the same terms. See
`data/raw/obdb/ATTRIBUTION.md` for the full notice.

[odbl]: https://opendatacommons.org/licenses/odbl/
```

Also replace the "Run it" / "Build the processed catalog" steps with:

```markdown
## Run it

Requirements: Python 3.13 and [`uv`](https://docs.astral.sh/uv/).

```bash
# 1. Install deps
uv sync

# 2. Fetch OBDB raw data + build the curated catalog
uv run python scripts/fetch_obdb.py
uv run python scripts/build_catalog.py

# 3. Engineer the taste vector (writes data/processed/beers.parquet)
uv run jupyter nbconvert --to notebook --execute \
    --inplace notebooks/data_prep.ipynb

# 4. Launch the dashboard
uv run python dashboard/app.py
# then open http://127.0.0.1:8050
```
```

Remove (or update) the "If the curated catalog is missing for any reason"
paragraph that references the old `build_raw_catalog.py`.

In the "Layout" section, replace:
```
├─ scripts/
│  └─ build_raw_catalog.py           # regenerates data/raw/curated_beers.csv
```
with:
```
├─ scripts/
│  ├─ fetch_obdb.py                  # downloads OpenBeerDB raw data
│  └─ build_catalog.py               # builds data/raw/curated_beers.csv from OBDB
```

- [ ] **Step 12.2: Delete the old script**

```powershell
Remove-Item "scripts/build_raw_catalog.py"
```

- [ ] **Step 12.3: Final test run**

```powershell
uv run pytest tests/ -v
```
Expected: all tests PASS.

- [ ] **Step 12.4: Final smoke check**

```powershell
Get-Content "data/raw/coverage_report.md"
```
Eyeball: USA share is <35%, style share max is <8%, ≥20 countries and ≥50 styles represented.

---

## Done

The catalog now spans ~750 beers across 20+ countries and 50+ styles,
sourced from a reproducible OBDB snapshot pinned to a specific commit.
The app code (recommender, dashboard, taste vector logic) is unchanged.
