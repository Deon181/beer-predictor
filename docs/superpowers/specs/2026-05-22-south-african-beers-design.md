# South African Beers — Manual Supplement Layer

**Date:** 2026-05-22
**Status:** Approved sections 1–3 in brainstorming session 2026-05-22

## 1. Goal

Add ~25 commercially available South African beers to the catalog through a
persistent **supplement layer**, so the additions survive every future run of
`scripts/build_catalog.py`. The supplement layer is country-agnostic — future
manual additions for any country use the same file and code path.

(The user requested ~25–30; the final count of 25 reflects the share-cap
trade-off documented in §11.)

## 2. Problem

The current catalog (`data/raw/curated_beers.csv`, 563 rows from 43 countries)
contains no South African beers because OpenBeerDB carries no SA breweries.
The pipeline rebuilds `curated_beers.csv` from OBDB on every run, so a direct
edit to that file would be wiped the next time anyone runs
`build_catalog.py`.

The user wants ~25–30 SA beers spread across the styles the SA scene actually
covers, with broad brewery representation (macro + craft).

## 3. Approach

Append a `data/raw/supplemental_beers.csv` file to the pipeline output, after
the stratified sample but before `beer_id` assignment. The supplement file
holds hand-written rows in the same column shape as `curated_beers.csv`
(minus `beer_id`). `build_catalog.py` always merges it in.

Chosen over two alternatives:
- **Per-country YAML/JSON files** — over-engineered for the scale; CSV
  matches the existing `data/raw/` idiom.
- **Python module with a hard-coded list** — exactly the pattern we just
  deleted (`scripts/build_raw_catalog.py`); reverting is a regression.

## 4. Architecture

```
                       OBDB raw CSVs
                            ↓
                    Stage 1–3 pipeline        (unchanged)
                            ↓
              stratified_sample → DataFrame
              (returns 7 cols, no beer_id)    ← changed
                            ↓
                    apply_supplements         ← NEW
                            ↑
              data/raw/supplemental_beers.csv ← NEW
                            ↓
                    assign sequential beer_id ← moved into main()
                            ↓
                   data/raw/curated_beers.csv (schema unchanged)
                            ↓
                  taste-vector engineering    (unchanged)
```

- The supplement file's columns match the existing seven non-id columns:
  `name, brewery, style, country, abv, ibu, srm`.
- Supplement-side `beer_id` is omitted; build_catalog.py assigns
  sequential IDs across the combined catalog at the very end.
- Share-cap enforcement is unchanged and runs *before* supplements (i.e.,
  supplements bypass the cap math). This is acceptable in practice
  because 28 SA beers across ~16 styles spread thinly.

## 5. Components

### 5.1 `data/raw/supplemental_beers.csv` (new)

CSV with the seven columns above. ~28 rows for the SA seed, but the file
is country-agnostic — future Ireland, Mexico, etc. additions go here too.

ABV values come from each brewery's published spec. IBU/SRM come from
brewery spec where available, otherwise the BJCP style baseline (the
recommender already imputes missing IBU from the style mean, so any
chosen value is consistent with downstream behavior).

### 5.2 `scripts/build_catalog.py` changes

Three changes:

1. `stratified_sample(...)` returns the seven non-id columns (drop the
   trailing `capped.insert(0, "beer_id", ...)`).
2. New module-level constants:
   ```python
   SUPPLEMENT_PATH = ROOT / "data" / "raw" / "supplemental_beers.csv"
   SUPPLEMENT_COLUMNS = ("name", "brewery", "style", "country", "abv", "ibu", "srm")
   ```
3. New functions:
   ```python
   def apply_supplements(sampled: pd.DataFrame, path: Path = SUPPLEMENT_PATH) -> pd.DataFrame: ...
   def _validate_supplement(df: pd.DataFrame) -> None: ...
   ```
4. `main()` orchestrates:
   ```python
   sampled = stratified_sample(normalized, ...)
   combined = apply_supplements(sampled)
   combined.insert(0, "beer_id", range(1, len(combined) + 1))
   combined.to_csv(OUT_CURATED, index=False)
   write_coverage_report(joined, normalized, combined)
   ```

Import `STYLE_ATTRS` at module top (for the validator).

### 5.3 Supplement loader semantics

- Missing supplement file → silent passthrough. The pipeline behaves
  exactly as today.
- File present but malformed → `ValueError` with the offending values:
  - Missing required columns
  - Unexpected extra columns (catches typos like `srm_value`)
  - `style` values that aren't keys in `STYLE_ATTRS`
- Conflicting `(name, brewery)` between sampled OBDB rows and supplement
  rows → **supplement wins** (`drop_duplicates(keep="last")`). Allows the
  user to override an OBDB row by adding the same beer to the supplement.

### 5.4 `write_coverage_report` change

Add one section at the end of `coverage_report.md`:
```markdown
## Supplemental beers included

| country | count |
|---|---|
| South Africa | 28 |
```
Distinguishes the OBDB-sourced rows from the manually-added ones in the
report.

## 6. SA beer roster (target ~25)

Breweries (8 distinct):
- **SAB** (macro) — Castle Lager, Castle Lite, Castle Milk Stout, Hansa Pilsener, Carling Black Label, Castle Free
- **Devil's Peak** — King's Blockhouse IPA, First Light Golden Ale, Silvertree Saison, Vannie Hout
- **Jack Black's Brewing Co** — Skeleton Coast IPA, Pale Ale, Atlantic Apocalypse Hazy IPA
- **Cape Brewing Company (CBC)** — Pilsner, Krystal Weiss, Amber Weiss
- **Darling Brew** — Bone Crusher Witbier, Black Mist Stout, Rogue Pony
- **Mitchell's Brewery** — Bosun's Bitter, Old Wobbly, 90 Shilling
- **Soweto Gold** — Superior Lager
- **Robson's Brewery** — East Coast Ale, Wheat Beer

Total: 25 beers. (Three lagers dropped per §11 risk trim: Mitchell's
Forester's Draught, Darling Slow Beer, Jack Black Brewers Lager.)

Styles touched (15, all already in `STYLE_ATTRS`):
American Lager, International Pale Lager, German Pilsner, Sweet Stout,
American Stout, American IPA, New England IPA, American Pale Ale, Saison,
Belgian Strong Pale, Hefeweizen, Dunkelweizen, Witbier, Premium Bitter,
English Barleywine, Scotch Ale, American Amber Ale.

Several of these (New England IPA, Belgian Strong Pale, English Barleywine,
Scotch Ale) are styles the OBDB sample didn't carry — SA additions will
raise the catalog's distinct-style count.

## 7. File layout after the change

```
beer-predictor/
├─ data/
│  └─ raw/
│     ├─ obdb/                       (unchanged)
│     ├─ curated_beers.csv           (regenerated — now includes supplements)
│     ├─ supplemental_beers.csv      ← NEW
│     └─ coverage_report.md          (one extra section)
├─ scripts/
│  └─ build_catalog.py               (refactored: separates sample/supplement/beer_id)
└─ tests/
   └─ test_supplements.py            ← NEW
```

## 8. Testing

**New — `tests/test_supplements.py`:**
- `test_apply_supplements_no_file_is_silent_passthrough` — supplement absent
- `test_apply_supplements_merges_supplement_rows` — supplement present, rows appear in output
- `test_apply_supplements_supplement_wins_on_duplicate` — conflict resolution
- `test_validate_supplement_rejects_missing_columns`
- `test_validate_supplement_rejects_extra_columns`
- `test_validate_supplement_rejects_unknown_style`
- `test_supplement_file_loads_cleanly` — actual file passes validation
- `test_supplement_contains_south_african_beers` — ≥20 SA rows (file is meant to hold 25)
- `test_supplement_styles_are_all_in_STYLE_ATTRS` — belt-and-braces

**Updated — `tests/test_catalog.py`:**
- `test_catalog_contains_south_africa` — ≥20 SA rows in the final catalog
- `test_diverse_styles` threshold bumped from ≥40 to ≥50 (SA adds the styles
  OBDB lacks)

**Unchanged:** All 53 existing tests stay green. Schema is identical; share
caps still pass because SA beers spread across many styles.

## 9. Error handling

| Case | Behavior |
|---|---|
| `supplemental_beers.csv` missing | Pipeline runs as before (silent passthrough) |
| Column mismatch | `ValueError` listing missing/extra columns |
| Unknown style | `ValueError` listing the bad styles + remediation hint |
| Duplicate `(name, brewery)` across sample + supplement | Supplement row wins, no error |
| Duplicate `(name, brewery)` within the supplement file | First occurrence wins (pandas default) |

## 10. Out of scope

- Per-country supplement files (single CSV is enough for the foreseeable
  future).
- Validation of ABV/IBU/SRM bounds (already done downstream in
  `data_prep.ipynb`).
- Country-name normalization for supplement entries (we control the
  values; just write "South Africa" consistently).
- Re-running share-cap enforcement after the supplement merge (would
  require marking supplemental rows as "kept"; YAGNI until we actually
  have a share threshold violation).

## 11. Risks

| Risk | Mitigation |
|---|---|
| Adding many same-style SA beers tips `test_no_style_dominates` over 8.5% | With 28 beers across 16 styles, max per-style addition is ~7 (American Lager); American Lager would go from 45/563 (8.0%) to 52/591 (8.8%) — *over* the 8.5% test threshold |
| ABV/IBU values for less-documented craft beers are estimates | Marked in the supplement file as the BJCP style baseline; recommender behavior is unchanged from how it treats unknown OBDB rows |
| Future contributor adds an unknown style to the supplement | Hard fail on first run with explicit error message naming the bad style |

**Risk #1 is real and needs a decision.** Two ways to handle:
- **(a) Trim American Lager SA entries to 4** (keep style at 49/588 = 8.3%, under 8.5%).
- **(b) Bump `test_no_style_dominates` cap to 9%** to admit the larger SA lager presence.

Recommend (a): SA mass-market beers are lager-dominated already, and 4 vs.
7 isn't a meaningful loss of representation. Trim to: Castle Lager,
Carling Black Label, Soweto Gold Superior Lager, Castle Free. Drop:
Mitchell's Forester's Draught, Darling Slow Beer, Jack Black Brewers Lager
(these become International Pale Lager / drop entirely).

Updated roster lands at ~25 beers.

## 12. Out-of-scope follow-ups (notes only)

- The supplement layer could later carry a `notes` column for "draft only" /
  "discontinued" annotations. Not needed yet.
