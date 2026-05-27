# Catalog Expansion — Design

**Date:** 2026-05-22
**Status:** Approved (user explicitly delegated execution; see "Approval" below)

## 1. Goal

Replace the hand-curated 262-beer catalog with a substantially larger, more
geographically and stylistically diverse one. Target final size: **500–1,000
beers**. The app's recommender, dashboard, and `curated_beers.csv` schema
are out of scope and stay untouched.

## 2. Problem

The current catalog (`data/raw/curated_beers.csv`, 262 rows) is too narrow:

- 50% of rows are from the USA. The remaining 18 countries average 7 beers each.
- 69 distinct styles, with the top-3 styles holding ~17% of all rows.
- The catalog is hardcoded as a Python `ROWS` list in
  `scripts/build_raw_catalog.py`, so every addition is a manual code edit.

The user is happy with the app behavior; the database itself is "a bit thin."

## 3. Approach

Switch the source of truth from a hand-written `ROWS` list to a deterministic
pipeline that derives the catalog from the [OpenBeerDB][obdb] public dataset
(~7,722 beers, ~1,414 breweries, 50+ countries), with a stratified sample to
guarantee coverage breadth and a curated style-alias map to keep the existing
recommender working.

[obdb]: https://github.com/jpargudo/pgOpenBeerDB/tree/main/openbeerdb_csv

### Why OpenBeerDB

| Candidate | Schema fit | Breadth | License | Verdict |
|---|---|---|---|---|
| **OpenBeerDB** | name, brewery, style, country, ABV, IBU, SRM — exact match | 7,722 beers, 50+ countries | DbCL/ODbL, share-alike with attribution | **Chosen** |
| Wikidata | Missing IBU/SRM — would force style-baseline imputation for the bitterness axis | Global, living | CC0 | Worse on the most differentiating column |
| Kaggle craft-cans | Clean | US-only — worsens the problem | Various | Rejected |

The ODbL/DbCL is share-alike with attribution. We comply with a one-paragraph
attribution in `README.md` and a `data/raw/obdb/ATTRIBUTION.md` next to the
raw files. This downgrades the derivative dataset from CC0 to ODbL — acceptable.

## 4. Architecture

Four stages, each writing a checked-in artifact so stages can be re-run
independently.

```
Stage 1: FETCH        scripts/fetch_obdb.py
    pins to a specific GitHub commit of jpargudo/pgOpenBeerDB
    downloads beers.csv, breweries.csv, styles.csv
    writes data/raw/obdb/{beers,breweries,styles}.csv
    writes data/raw/obdb/ATTRIBUTION.md (DbCL/ODbL)
                                  ↓
Stage 2: JOIN + CLEAN  scripts/build_catalog.py  (step 1 of 2)
    joins beers → styles (on style_id) and beers → breweries (on brewery_id)
    projects to columns: name, brewery, style_obdb, country, abv, ibu, srm
    coerces numerics; treats abv=0 and ibu=0 as null (OBDB uses 0 for missing)
    drops rows missing name / brewery / style / country / abv
    keeps rows with null IBU/SRM — imputed in Stage 4
    writes data/raw/obdb_joined.csv  (intermediate, ~6k rows)
                                  ↓
Stage 3: NORMALIZE + SAMPLE  scripts/build_catalog.py  (step 2 of 2)
    applies src/style_aliases.py: OBDB style → BJCP key
    drops rows whose OBDB style has no alias entry
    stratified sample to ~500–1,000 with quotas:
        per-country cap, per-style cap, deterministic seed
    assigns sequential beer_id starting at 1
    writes data/raw/curated_beers.csv  (same path as today; replaces it)
    writes data/raw/coverage_report.md
                                  ↓
Stage 4: TASTE-VECTOR  notebooks/data_prep.ipynb  (existing, lightly modified)
    one change: existing IBU style-mean backfill already handles nulls,
    so no functional change should be needed — but verify
    writes data/processed/beers.parquet
                                  ↓
dashboard reads parquet (unchanged)
```

Boundaries between stages are pandas DataFrames written to disk as CSV — same
shape as today, so each stage is testable in isolation.

## 5. Components

### 5.1 `scripts/fetch_obdb.py` (new)

Downloads OBDB raw CSVs from a pinned commit hash for reproducibility.

```python
OBDB_REPO = "jpargudo/pgOpenBeerDB"
OBDB_REF  = "<commit-sha>"  # filled in at implementation time
BASE_URL  = f"https://raw.githubusercontent.com/{OBDB_REPO}/{OBDB_REF}/openbeerdb_csv"

FILES = ["beers.csv", "breweries.csv", "styles.csv", "LICENCE.txt"]
```

- Uses the existing `requests` dependency (already in `pyproject.toml`).
- Skips download if file already present and `--force` not passed.
- Writes `data/raw/obdb/ATTRIBUTION.md` with the DbCL/ODbL notice.

### 5.2 `src/style_aliases.py` (new)

A static dictionary mapping OBDB style names (143 distinct values in
`styles.csv`) to BJCP keys used by `src/style_attributes.py`.

```python
OBDB_TO_BJCP: Mapping[str, str] = {
    "American-Style India Pale Ale":       "American IPA",
    "Imperial or Double India Pale Ale":   "Imperial IPA",
    "English-Style India Pale Ale":        "American IPA",  # closest BJCP key
    "American-Style Pale Ale":             "American Pale Ale",
    "Classic English-Style Pale Ale":      "English Pale Ale",
    "Ordinary Bitter":                     "Ordinary Bitter",
    # ... etc, one entry per OBDB style we want to keep
}

def to_bjcp(obdb_style: str) -> str | None:
    """Map an OBDB style name to a BJCP key, or None if unmapped."""
    return OBDB_TO_BJCP.get(obdb_style)
```

Unmapped styles are intentionally None → row gets dropped in Stage 3. Coverage
report will surface any high-volume unmapped style for review.

A small number of OBDB styles will have no good BJCP match (e.g., "Energy
Drinks", "Specialty Honey Ale"). These are dropped on purpose.

### 5.3 `scripts/build_catalog.py` (new; replaces `build_raw_catalog.py`)

Single CLI script with two phases:

```bash
uv run python scripts/build_catalog.py            # default: fetch + build
uv run python scripts/build_catalog.py --target-size 750
uv run python scripts/build_catalog.py --seed 42
```

Functions:

- `join_and_clean(raw_dir) -> pd.DataFrame` — Stage 2
- `normalize_style(df) -> pd.DataFrame` — Stage 3a
- `stratified_sample(df, target_size, seed) -> pd.DataFrame` — Stage 3b
- `write_coverage_report(df, path)` — markdown summary

Sampling algorithm (Stage 3b) — three-tier quota, applied in order:

1. **Per-(country, style) cap** — `MAX_PER_CELL = 6`. For each
   `(country, style)` group, keep at most 6 rows. Prevents one country
   from monopolizing one style (e.g., 200 American IPAs from USA).
2. **Per-style cap** — `MAX_PER_STYLE` = `ceil(0.08 * target_size)`
   (e.g., 60 for target 750). Enforces the test invariant that no style
   exceeds 8% of the catalog. Rows above the cap are dropped, preferring
   to keep diversity across countries within that style.
3. **Per-country cap** — `MAX_PER_COUNTRY` = `ceil(0.35 * target_size)`
   (e.g., 263 for target 750). Enforces the test invariant that no
   country exceeds 35% of the catalog. Only USA realistically hits this;
   when it does, drop USA rows preferring to keep diversity across styles.
4. **Final size adjustment** — if the total still exceeds `target_size`
   (rare), uniformly down-sample. If below `target_size`, accept as-is
   (a smaller catalog is fine; we don't relax quotas to pad).
5. Random seed fixed for reproducibility (`np.random.default_rng(seed)`).

### 5.4 `notebooks/data_prep.ipynb` (modified)

The notebook already backfills missing IBU with the style mean — that logic
will continue to work. No functional change expected. If verification finds
edge cases (e.g., a style with all-null IBU within the sample), patch the
backfill to fall back to the BJCP style baseline from `style_attributes.py`.

### 5.5 Deleted files

- `scripts/build_raw_catalog.py` — replaced by `scripts/build_catalog.py`

## 6. File layout after the change

```
beer-predictor/
├─ data/
│  ├─ raw/
│  │  ├─ curated_beers.csv         ← regenerated, 500–1,000 rows
│  │  ├─ coverage_report.md        ← NEW: country/style distribution
│  │  └─ obdb/                     ← NEW: raw source data, committed
│  │     ├─ beers.csv
│  │     ├─ breweries.csv
│  │     ├─ styles.csv
│  │     ├─ LICENCE.txt
│  │     └─ ATTRIBUTION.md         ← DbCL/ODbL attribution
│  └─ processed/beers.parquet      ← regenerated, same schema
├─ src/
│  ├─ style_attributes.py          ← unchanged
│  ├─ style_aliases.py             ← NEW: OBDB → BJCP
│  └─ recommender.py               ← unchanged
├─ scripts/
│  ├─ fetch_obdb.py                ← NEW
│  └─ build_catalog.py             ← NEW (replaces build_raw_catalog.py)
├─ tests/
│  ├─ test_recommender.py          ← unchanged
│  ├─ test_data_prep.py            ← may need fixture update
│  └─ test_catalog.py              ← NEW: breadth invariants
└─ README.md                        ← updated: data pipeline + attribution
```

## 7. Testing

### Existing tests
Must continue to pass unmodified:
- `tests/test_recommender.py` — distance, top-k, filters, explain
- `tests/test_data_prep.py` — schema + taste-vector ranges

The catalog schema is unchanged, so existing tests should be a green light
that nothing downstream broke. If `test_data_prep.py` references specific
beer names (e.g., "Pliny the Elder" sanity checks), those assertions need
to either (a) be relaxed to style-level claims or (b) confirm the new
catalog still contains the named beers.

### New tests — `tests/test_catalog.py`

Breadth invariants on the regenerated `curated_beers.csv`:

- `len(catalog) >= 500`
- `catalog['country'].nunique() >= 20`
- `catalog['style'].nunique() >= 50`
- No single country exceeds 35% of rows
- No single style exceeds 8% of rows
- Every style in the catalog has an entry in `STYLE_ATTRS` (so taste
  vector engineering never falls through to `DEFAULT_STYLE_ATTRS`)

These tests verify the *output of the pipeline*, not the pipeline internals.
They load `data/raw/curated_beers.csv` directly.

### New tests — `tests/test_style_aliases.py`

- Every value in `OBDB_TO_BJCP` is a valid key in `STYLE_ATTRS`
- `to_bjcp("nonexistent style")` returns `None`

## 8. Error handling

- **Network failure in fetch**: script exits non-zero with the URL that
  failed. Cached raw files (already on disk) are not deleted.
- **Empty stratified sample**: if quotas eliminate every row (would only
  happen with absurdly tight quotas), exit non-zero with a coverage diff.
- **Unmapped styles**: not an error — silently dropped. Coverage report
  lists the top-10 dropped styles by row count so the alias map can be
  expanded over time.

## 9. License & attribution

OBDB ships under the Database Contents License (DbCL) paired with ODbL
for the database structure. We comply via:

- `data/raw/obdb/ATTRIBUTION.md` — credits openbeerdb.com and the jpargudo
  mirror, reproduces the DbCL header.
- `README.md` — adds an "Attribution" section pointing to the file above.

The derived `curated_beers.csv` is itself a database derivative, so it
inherits ODbL (share-alike with attribution). README is updated to reflect
this — the current CC0 claim for the curated catalog no longer applies.

## 10. Out of scope

- Adding new columns to the catalog schema (no flavor notes, no ratings).
- Changing the recommender, taste vector formula, or dashboard.
- Live data refresh — the OBDB snapshot is checked into git.
- An online ingestion pipeline (`Untappd`, etc.).
- Style-aware imputation when style-mean IBU is itself null (only patch
  if the verification step finds it actually happens).

## 11. Risks

| Risk | Mitigation |
|---|---|
| OBDB data is from ~2010 → some breweries closed | Acceptable; we want stable historical breadth, not freshness |
| Style alias map is tedious to maintain | Coverage report surfaces the worst gaps; iterate over time |
| Some users will miss specific curated picks (e.g., Pliny the Elder) | Verify after sampling whether key landmark beers survive; if not, document that the trade-off is breadth over specific picks |
| Network blocked at build time | The fetch script supports `--force` and the raw OBDB CSVs are committed to git, so fetch only runs on demand |

## 12. Approval

Brainstorming session 2026-05-22. User explicitly delegated execution
("I have to go. Please continue without me until the final goal is done")
after approving the high-level approach. The section-by-section approval
gate was waived by the user.
