# South African Beers — Supplement Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 25 South African beers via a country-agnostic supplement layer that survives every future run of `scripts/build_catalog.py`.

**Architecture:** A new `data/raw/supplemental_beers.csv` holds hand-written rows in the same shape as `curated_beers.csv` minus `beer_id`. `build_catalog.py` is refactored to: (1) have `stratified_sample` return 7-column data (no `beer_id`), (2) merge supplements via a new `apply_supplements` function with strict schema/style validation, (3) assign `beer_id`s on the combined result in `main()`.

**Tech Stack:** Python 3.13, pandas, pytest. No new dependencies.

**Note on git:** This repo is not a git repository. Per-task "commit" steps are omitted.

**Spec:** `docs/superpowers/specs/2026-05-22-south-african-beers-design.md`

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `data/raw/supplemental_beers.csv` | create | 25 hand-written SA beers (also the home for any future manual additions, any country) |
| `scripts/build_catalog.py` | modify | Refactor `stratified_sample` return shape; add `apply_supplements` + `_validate_supplement`; rewire `main()`; extend `write_coverage_report` |
| `tests/test_supplements.py` | create | Tests for `apply_supplements` / `_validate_supplement` and a smoke test that the real supplement file passes validation |
| `tests/test_catalog.py` | modify | Add SA-presence assertion; bump `test_diverse_styles` floor from ≥40 to ≥50 |
| `README.md` | modify | One paragraph noting the supplement file |

---

## Task 1: Refactor `stratified_sample` to drop `beer_id`

**Files:**
- Modify: `scripts/build_catalog.py` (`stratified_sample` final lines)
- Test: `tests/test_supplements.py` (smoke check; full file created in Task 3)

The seven-column output is what `apply_supplements` will concatenate the supplement onto. `beer_id` is then assigned in `main()` over the combined DataFrame.

- [ ] **Step 1.1: Write a failing test in a new file `tests/test_supplements.py`**

```python
"""Tests for the supplemental-beers layer in scripts/build_catalog.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import lazily inside tests; we'll add to this file across tasks.
from scripts import build_catalog as bc


def test_stratified_sample_does_not_emit_beer_id() -> None:
    """beer_id is assigned later in main() over the combined catalog,
    so the sampler must return only the seven non-id columns."""
    joined = bc.join_and_clean()
    normalized = bc.normalize_style(joined)
    sampled = bc.stratified_sample(normalized, target_size=100, seed=42)
    assert "beer_id" not in sampled.columns
    expected = {"name", "brewery", "style", "country", "abv", "ibu", "srm"}
    assert set(sampled.columns) == expected
```

- [ ] **Step 1.2: Run the test — confirm it fails**

```powershell
uv run pytest tests/test_supplements.py::test_stratified_sample_does_not_emit_beer_id -v
```
Expected: FAIL — `beer_id` IS in the output, and an extra column `beer_id` is present.

- [ ] **Step 1.3: Edit `scripts/build_catalog.py`**

Find the current end of `stratified_sample`:

```python
    capped.insert(0, "beer_id", range(1, len(capped) + 1))
    return capped[list(CURATED_COLUMNS)]
```

Replace with:

```python
    return capped[list(SUPPLEMENT_COLUMNS)]
```

And just above the function (near `CURATED_COLUMNS`), add:

```python
SUPPLEMENT_COLUMNS = ("name", "brewery", "style", "country", "abv", "ibu", "srm")
```

(`CURATED_COLUMNS` stays as the final output schema — `beer_id` + the seven non-id columns.)

- [ ] **Step 1.4: Run the test — confirm it passes, and confirm nothing else broke yet**

```powershell
uv run pytest tests/test_supplements.py::test_stratified_sample_does_not_emit_beer_id -v
```
Expected: PASS.

Do NOT run the full pipeline yet — `main()` still expects `beer_id` and will fail. Task 4 fixes `main()`.

---

## Task 2: Validator — `_validate_supplement`

**Files:**
- Modify: `scripts/build_catalog.py` (add `_validate_supplement`)
- Test: `tests/test_supplements.py` (append validator tests)

- [ ] **Step 2.1: Append failing tests to `tests/test_supplements.py`**

```python
def _make_valid_row() -> dict:
    return {
        "name": "Test Beer",
        "brewery": "Test Brewery",
        "style": "American Pale Ale",
        "country": "South Africa",
        "abv": 5.0,
        "ibu": 30.0,
        "srm": 5.0,
    }


def test_validate_supplement_accepts_well_formed_dataframe() -> None:
    df = pd.DataFrame([_make_valid_row()])
    bc._validate_supplement(df)  # should not raise


def test_validate_supplement_rejects_missing_column() -> None:
    df = pd.DataFrame([_make_valid_row()]).drop(columns=["ibu"])
    with pytest.raises(ValueError, match="missing columns"):
        bc._validate_supplement(df)


def test_validate_supplement_rejects_extra_column() -> None:
    row = _make_valid_row()
    row["srm_value"] = 5.0
    df = pd.DataFrame([row])
    with pytest.raises(ValueError, match="unexpected columns"):
        bc._validate_supplement(df)


def test_validate_supplement_rejects_unknown_style() -> None:
    row = _make_valid_row()
    row["style"] = "Definitely Not A Real Style"
    df = pd.DataFrame([row])
    with pytest.raises(ValueError, match="styles not in STYLE_ATTRS"):
        bc._validate_supplement(df)
```

- [ ] **Step 2.2: Run the tests — confirm they all fail**

```powershell
uv run pytest tests/test_supplements.py -v -k validate
```
Expected: 4 failures (AttributeError: module 'build_catalog' has no attribute '_validate_supplement').

- [ ] **Step 2.3: Add the validator to `scripts/build_catalog.py`**

At the module top, add the import:

```python
from src.style_attributes import STYLE_ATTRS
```

Insert the validator function (after `write_coverage_report` is fine, location is just a code-organization choice):

```python
def _validate_supplement(df: pd.DataFrame) -> None:
    """Raise ValueError if the supplement DataFrame is malformed.

    Checks (in order):
    - exact column-set match against SUPPLEMENT_COLUMNS
    - every `style` value is a key in STYLE_ATTRS

    No bounds-checking on abv/ibu/srm — the data_prep notebook already
    clips these. The point of this validator is to fail loudly on the
    kinds of typos a human makes in a hand-written CSV.
    """
    expected = set(SUPPLEMENT_COLUMNS)
    actual = set(df.columns)
    missing = expected - actual
    if missing:
        raise ValueError(
            f"supplemental_beers.csv missing columns: {sorted(missing)}"
        )
    extra = actual - expected
    if extra:
        raise ValueError(
            f"supplemental_beers.csv has unexpected columns: {sorted(extra)}"
        )
    bad_styles = set(df["style"]) - set(STYLE_ATTRS.keys())
    if bad_styles:
        raise ValueError(
            f"supplemental_beers.csv has styles not in STYLE_ATTRS: "
            f"{sorted(bad_styles)}. Add them to src/style_attributes.py "
            "or fix the supplement entry."
        )
```

- [ ] **Step 2.4: Run the validator tests — confirm they pass**

```powershell
uv run pytest tests/test_supplements.py -v -k validate
```
Expected: 4 PASS.

---

## Task 3: Merger — `apply_supplements`

**Files:**
- Modify: `scripts/build_catalog.py` (add `apply_supplements`)
- Test: `tests/test_supplements.py` (append merger tests)

- [ ] **Step 3.1: Append failing tests to `tests/test_supplements.py`**

```python
def test_apply_supplements_no_file_is_silent_passthrough(tmp_path: Path) -> None:
    sampled = pd.DataFrame([_make_valid_row()])
    missing = tmp_path / "does_not_exist.csv"
    out = bc.apply_supplements(sampled, path=missing)
    pd.testing.assert_frame_equal(
        out.reset_index(drop=True), sampled.reset_index(drop=True)
    )


def test_apply_supplements_merges_supplement_rows(tmp_path: Path) -> None:
    sampled = pd.DataFrame([_make_valid_row()])
    supp_row = _make_valid_row()
    supp_row["name"] = "Different Beer"
    supp_path = tmp_path / "supp.csv"
    pd.DataFrame([supp_row]).to_csv(supp_path, index=False)

    out = bc.apply_supplements(sampled, path=supp_path)
    assert len(out) == 2
    assert "Test Beer" in out["name"].tolist()
    assert "Different Beer" in out["name"].tolist()


def test_apply_supplements_supplement_wins_on_duplicate(tmp_path: Path) -> None:
    sampled_row = _make_valid_row()
    sampled_row["abv"] = 4.0
    sampled = pd.DataFrame([sampled_row])

    supp_row = _make_valid_row()
    supp_row["abv"] = 9.9  # different value, same (name, brewery)
    supp_path = tmp_path / "supp.csv"
    pd.DataFrame([supp_row]).to_csv(supp_path, index=False)

    out = bc.apply_supplements(sampled, path=supp_path)
    assert len(out) == 1
    assert out.iloc[0]["abv"] == 9.9, "supplement value should win on duplicate"


def test_apply_supplements_raises_on_malformed_file(tmp_path: Path) -> None:
    sampled = pd.DataFrame([_make_valid_row()])
    supp_path = tmp_path / "supp.csv"
    pd.DataFrame([{"name": "x", "brewery": "y"}]).to_csv(supp_path, index=False)  # missing cols
    with pytest.raises(ValueError, match="missing columns"):
        bc.apply_supplements(sampled, path=supp_path)
```

- [ ] **Step 3.2: Run the tests — confirm they all fail**

```powershell
uv run pytest tests/test_supplements.py -v -k apply_supplements
```
Expected: 4 failures (AttributeError: no `apply_supplements`).

- [ ] **Step 3.3: Add `apply_supplements` and the `SUPPLEMENT_PATH` constant**

Near the other path constants at the top of `scripts/build_catalog.py`:

```python
SUPPLEMENT_PATH = ROOT / "data" / "raw" / "supplemental_beers.csv"
```

Insert the merge function (next to `_validate_supplement`):

```python
def apply_supplements(
    sampled: pd.DataFrame, path: Path = SUPPLEMENT_PATH
) -> pd.DataFrame:
    """Merge data/raw/supplemental_beers.csv into the sampled DataFrame.

    - Missing file → silent passthrough (the pipeline behaves as if there
      were no supplement).
    - File present → validated and appended; on (name, brewery) collisions
      the supplement row wins (so the user can override an OBDB row).
    """
    if not path.exists():
        return sampled.copy()
    supp = pd.read_csv(path)
    _validate_supplement(supp)
    combined = pd.concat([sampled, supp[list(SUPPLEMENT_COLUMNS)]], ignore_index=True)
    combined = combined.drop_duplicates(subset=["name", "brewery"], keep="last")
    return combined.reset_index(drop=True)
```

- [ ] **Step 3.4: Run all supplement tests — confirm pass**

```powershell
uv run pytest tests/test_supplements.py -v
```
Expected: all 9 tests so far PASS (1 from Task 1 + 4 validator + 4 merger).

---

## Task 4: Wire `apply_supplements` into `main()` + extend coverage report

**Files:**
- Modify: `scripts/build_catalog.py` (`main`, `write_coverage_report`)

The current `main()` writes `curated_beers.csv` directly from `stratified_sample`, expecting it to have `beer_id`. Now we run the supplements step, then assign `beer_id` on the combined frame.

- [ ] **Step 4.1: Replace the existing `main()` body**

The current `main()` ends roughly:

```python
    sampled = stratified_sample(normalized, target_size=args.target_size, seed=args.seed)
    sampled.to_csv(OUT_CURATED, index=False)
    print(f"final catalog: {len(sampled)} rows -> {OUT_CURATED}")
    print(
        f"countries: {sampled['country'].nunique()}, "
        f"styles: {sampled['style'].nunique()}"
    )

    write_coverage_report(joined, normalized, sampled)
    return 0
```

Replace with:

```python
    sampled = stratified_sample(normalized, target_size=args.target_size, seed=args.seed)
    print(f"sampled (no supplements yet): {len(sampled)} rows")

    combined = apply_supplements(sampled)
    n_supp = len(combined) - len(sampled)
    if n_supp != 0:
        print(f"applied supplements: +{n_supp} rows ({SUPPLEMENT_PATH.name})")

    combined.insert(0, "beer_id", range(1, len(combined) + 1))
    combined = combined[list(CURATED_COLUMNS)]
    combined.to_csv(OUT_CURATED, index=False)
    print(f"final catalog: {len(combined)} rows -> {OUT_CURATED}")
    print(
        f"countries: {combined['country'].nunique()}, "
        f"styles: {combined['style'].nunique()}"
    )

    write_coverage_report(joined, normalized, combined)
    return 0
```

- [ ] **Step 4.2: Extend `write_coverage_report` to show supplements**

Find the end of `write_coverage_report` (just before the `out.write_text(...)` line). Insert this block:

```python
    # Supplemental beers summary (only if the file exists; counts in the
    # final catalog by country, restricted to rows that appear in the
    # supplement file).
    if SUPPLEMENT_PATH.exists():
        supp = pd.read_csv(SUPPLEMENT_PATH)
        supp_key = supp[["name", "brewery"]].apply(tuple, axis=1)
        sampled_key = sampled[["name", "brewery"]].apply(tuple, axis=1)
        in_supp = sampled_key.isin(set(supp_key))
        supp_in_catalog = sampled[in_supp]
        if not supp_in_catalog.empty:
            lines += [
                "",
                "## Supplemental beers included",
                "",
                "| country | rows |",
                "|---|---|",
            ]
            for country, n in supp_in_catalog["country"].value_counts().items():
                lines.append(f"| {country} | {n} |")
```

(The `sampled` parameter to `write_coverage_report` is the *final* combined catalog at the call site in `main()`, so this works.)

- [ ] **Step 4.3: Run the existing supplement tests and the catalog tests**

```powershell
uv run pytest tests/test_supplements.py tests/test_catalog.py -v
```
Expected: all pass. (No supplemental_beers.csv exists yet, so `apply_supplements` is a passthrough and the catalog tests behave exactly as before.)

- [ ] **Step 4.4: Run the pipeline end-to-end**

```powershell
uv run python scripts/build_catalog.py
```
Expected output:
```
joined+cleaned: 3037 rows -> ...obdb_joined.csv
normalize_style: dropping 640 rows with unmapped OBDB style
after style normalization: 2397 rows, 46 BJCP styles
sampled (no supplements yet): 563 rows
final catalog: 563 rows -> ...curated_beers.csv
countries: 43, styles: 46
coverage report: ...coverage_report.md
```
(No "applied supplements" line — file doesn't exist yet.)

---

## Task 5: Author the supplement CSV

**Files:**
- Create: `data/raw/supplemental_beers.csv`

- [ ] **Step 5.1: Write `data/raw/supplemental_beers.csv`**

Header line and 25 rows. ABV values come from each brewery's published
spec; IBU/SRM come from brewery spec where available, otherwise the
BJCP style baseline (the recommender already imputes missing IBU from
the style mean, so any reasonable value is consistent with downstream
behavior).

```csv
name,brewery,style,country,abv,ibu,srm
Castle Lager,South African Breweries,American Lager,South Africa,5.0,14,4
Castle Lite,South African Breweries,International Pale Lager,South Africa,4.0,10,3
Castle Milk Stout,South African Breweries,Sweet Stout,South Africa,6.0,18,38
Hansa Pilsener,South African Breweries,German Pilsner,South Africa,4.5,22,4
Carling Black Label,South African Breweries,American Lager,South Africa,5.5,14,4
Castle Free,South African Breweries,American Light Lager,South Africa,0.5,8,3
King's Blockhouse IPA,Devil's Peak Brewing Company,American IPA,South Africa,6.0,60,8
First Light Golden Ale,Devil's Peak Brewing Company,American Pale Ale,South Africa,4.5,20,5
Silvertree Saison,Devil's Peak Brewing Company,Saison,South Africa,5.5,28,5
Vannie Hout,Devil's Peak Brewing Company,Belgian Strong Pale,South Africa,7.5,32,7
Skeleton Coast IPA,Jack Black's Brewing Co,American IPA,South Africa,6.0,55,9
Jack Black Pale Ale,Jack Black's Brewing Co,American Pale Ale,South Africa,5.0,30,6
Atlantic Apocalypse Hazy IPA,Jack Black's Brewing Co,New England IPA,South Africa,6.5,40,5
CBC Pilsner,Cape Brewing Company,German Pilsner,South Africa,5.0,30,3
CBC Krystal Weiss,Cape Brewing Company,Hefeweizen,South Africa,5.0,12,6
CBC Amber Weiss,Cape Brewing Company,Dunkelweizen,South Africa,5.2,14,15
Bone Crusher Witbier,Darling Brew,Witbier,South Africa,5.2,14,5
Black Mist Stout,Darling Brew,American Stout,South Africa,5.5,40,38
Rogue Pony,Darling Brew,American Amber Ale,South Africa,5.0,35,12
Bosun's Bitter,Mitchell's Brewery,Premium Bitter,South Africa,4.0,30,12
Old Wobbly,Mitchell's Brewery,English Barleywine,South Africa,9.0,40,18
90 Shilling,Mitchell's Brewery,Scotch Ale,South Africa,5.6,30,18
Soweto Gold Superior Lager,Soweto Gold Brewery,American Lager,South Africa,4.5,14,4
East Coast Ale,Robson's Brewery,American Pale Ale,South Africa,4.5,28,7
Robson's Wheat Beer,Robson's Brewery,Hefeweizen,South Africa,5.0,12,6
```

That's 25 rows × 8 breweries × 15 distinct BJCP styles.

> **Why "South African Breweries" (full name) and not "SAB"** — matches the publicly used brewery name; keep it consistent for filter UX.

> **Why "American Light Lager" for Castle Free** — non-alcoholic mass-market lager; that BJCP key is the closest taste-baseline match.

- [ ] **Step 5.2: Run the supplement file validation smoke test**

```powershell
uv run python -c "
import pandas as pd
from scripts.build_catalog import _validate_supplement, SUPPLEMENT_PATH
df = pd.read_csv(SUPPLEMENT_PATH)
_validate_supplement(df)
print(f'OK: {len(df)} rows validated')
"
```
Expected: `OK: 25 rows validated`.

If it raises, the most likely cause is a style typo in the CSV. The error
message names the offending style.

---

## Task 6: Smoke test for the real supplement file

**Files:**
- Modify: `tests/test_supplements.py` (append two smoke tests)

- [ ] **Step 6.1: Append to `tests/test_supplements.py`**

```python
SUPP_FILE = ROOT / "data" / "raw" / "supplemental_beers.csv"


@pytest.mark.skipif(not SUPP_FILE.exists(), reason="supplement file not authored yet")
def test_supplement_file_passes_validation() -> None:
    df = pd.read_csv(SUPP_FILE)
    bc._validate_supplement(df)


@pytest.mark.skipif(not SUPP_FILE.exists(), reason="supplement file not authored yet")
def test_supplement_contains_south_african_beers() -> None:
    df = pd.read_csv(SUPP_FILE)
    sa = df[df["country"] == "South Africa"]
    assert len(sa) >= 20, f"expected ≥20 SA beers, got {len(sa)}"
```

- [ ] **Step 6.2: Run the new tests**

```powershell
uv run pytest tests/test_supplements.py -v
```
Expected: all 11 supplement tests PASS.

---

## Task 7: Rerun the pipeline with supplements

**Files:** none — verification only.

- [ ] **Step 7.1: Run `build_catalog.py` end-to-end**

```powershell
uv run python scripts/build_catalog.py
```
Expected output now includes:
```
sampled (no supplements yet): 563 rows
applied supplements: +25 rows (supplemental_beers.csv)
final catalog: 588 rows -> ...curated_beers.csv
countries: 44, styles: 51
coverage report: ...coverage_report.md
```

- [ ] **Step 7.2: Spot-check the final catalog**

```powershell
$c = Import-Csv "data/raw/curated_beers.csv"
"rows: $($c.Count)"
"South Africa rows: $((($c | Where-Object country -eq 'South Africa').Count))"
$c | Where-Object country -eq 'South Africa' | Group-Object style | Sort-Object Count -Descending | Format-Table -AutoSize
```
Expected: 588 rows total, 25 SA rows across ~15 styles.

- [ ] **Step 7.3: Verify share thresholds still hold**

```powershell
$c = Import-Csv "data/raw/curated_beers.csv"
$top_c = ($c | Group-Object country | Sort-Object Count -Descending | Select-Object -First 1)
"Top country: $($top_c.Name) at $(($top_c.Count / $c.Count).ToString('P2'))"
$top_s = ($c | Group-Object style | Sort-Object Count -Descending | Select-Object -First 1)
"Top style: $($top_s.Name) at $(($top_s.Count / $c.Count).ToString('P2'))"
```
Expected: top country still USA, share now ~33.5% (down from 35.0%); top style still American Lager at ~8.3% (was 8.0% before SA additions added 4 lagers).

If top style exceeds 8.5%, drop one more American Lager from the supplement CSV (the brief was a max-4 American Lager target — verify Step 5.1's CSV adheres).

---

## Task 8: Catalog tests — SA presence + bumped style threshold

**Files:**
- Modify: `tests/test_catalog.py`

- [ ] **Step 8.1: Bump the diversity threshold and add the SA assertion**

Find this test in `tests/test_catalog.py`:

```python
def test_diverse_styles(df: pd.DataFrame) -> None:
    # OBDB tags only ~46 distinct BJCP-mappable styles; that's a data
    # ceiling, not a sampling failure.
    assert df["style"].nunique() >= 40
```

Replace with:

```python
def test_diverse_styles(df: pd.DataFrame) -> None:
    # OBDB tags ~46 distinct BJCP-mappable styles; the SA supplement adds
    # ~5 more (New England IPA, Belgian Strong Pale, English Barleywine,
    # Scotch Ale, etc.).
    assert df["style"].nunique() >= 50
```

Append a new test:

```python
def test_catalog_contains_south_africa(df: pd.DataFrame) -> None:
    sa = df[df["country"] == "South Africa"]
    assert len(sa) >= 20, f"only {len(sa)} SA beers in final catalog"
    # Sanity: at least 4 distinct SA breweries make it through.
    assert sa["brewery"].nunique() >= 4
```

- [ ] **Step 8.2: Run the catalog tests**

```powershell
uv run pytest tests/test_catalog.py -v
```
Expected: all 12 PASS (was 11 + the new SA one).

---

## Task 9: Rebuild parquet + run full test suite

**Files:** none modified — verification only.

- [ ] **Step 9.1: Rebuild the processed parquet**

```powershell
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/data_prep.ipynb
```
Expected: notebook executes to completion. Final "Sanity checks passed for N beers across M styles" should show N=588, M=51.

- [ ] **Step 9.2: Run the full pytest suite**

```powershell
uv run pytest tests/ -v
```
Expected: all tests pass (existing 53 + 11 supplement tests + 1 new SA test = 65).

If the recommender's `test_filters_styles` for "Saison" or `test_recommend_extreme_*` fail, the most likely cause is a supplement entry overriding an OBDB row by accident — check Step 5.1's CSV for collisions with OBDB names (none expected; no SA brewery is in OBDB).

---

## Task 10: README update

**Files:**
- Modify: `README.md`

- [ ] **Step 10.1: Add a "Manual supplements" paragraph**

In the "Dataset" section, just before the "Attribution" paragraph, insert:

```markdown
**Manual supplements:** Beers that aren't in OpenBeerDB (e.g., the 25
South African beers Castle Lager, Devil's Peak King's Blockhouse IPA,
etc.) live in `data/raw/supplemental_beers.csv`. `build_catalog.py`
always appends this file to the sampled catalog before writing
`curated_beers.csv`, so manual additions persist through every pipeline
rebuild. Adding a beer is a one-line CSV edit — see the file header for
the required columns.
```

- [ ] **Step 10.2: Update the file-layout block**

In the `## Layout` section, find:

```
│  └─ raw/
│     ├─ obdb/                       # OpenBeerDB snapshot + ATTRIBUTION
│     ├─ curated_beers.csv           # final sampled catalog
│     └─ coverage_report.md          # country/style distribution
```

Replace with:

```
│  └─ raw/
│     ├─ obdb/                       # OpenBeerDB snapshot + ATTRIBUTION
│     ├─ supplemental_beers.csv      # manually curated beers (e.g., SA)
│     ├─ curated_beers.csv           # final catalog (sample ∪ supplements)
│     └─ coverage_report.md          # country/style distribution
```

- [ ] **Step 10.3: Final verification**

```powershell
uv run pytest tests/ -v
```
Expected: all 65 tests PASS.

```powershell
Get-Content "data/raw/coverage_report.md" -TotalCount 8
```
Expected: "final sampled catalog: **588**" (or whatever the actual final number is — the point is the report shows the supplement merger ran).

---

## Done

Final state:
- `data/raw/supplemental_beers.csv` contains 25 SA beers across 8 breweries and 15 BJCP styles.
- `scripts/build_catalog.py` always merges supplements into the catalog; future additions for any country are a CSV edit.
- Catalog: ~588 rows, 44 countries (was 43), 51 distinct styles (was 46), USA share ~33.5% (was 35.0%).
- All tests green.
