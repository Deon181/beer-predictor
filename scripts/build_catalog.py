"""Build the curated beer catalog from the OBDB raw data.

Pipeline:
    Stage 2:  JOIN + CLEAN          join_and_clean()
    Stage 3a: NORMALIZE STYLE       normalize_style()
    Stage 3b: STRATIFIED SAMPLE     stratified_sample()
    Stage 3c: COVERAGE REPORT       write_coverage_report()

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
from src.style_attributes import STYLE_ATTRS

RAW_OBDB = ROOT / "data" / "raw" / "obdb"
OUT_CURATED = ROOT / "data" / "raw" / "curated_beers.csv"
OUT_JOINED = ROOT / "data" / "raw" / "obdb_joined.csv"
OUT_COVERAGE = ROOT / "data" / "raw" / "coverage_report.md"
SUPPLEMENT_PATH = ROOT / "data" / "raw" / "supplemental_beers.csv"

import re

_SLUG_ASTERISK = re.compile(r"\*")
_SLUG_APOSTROPHE = re.compile(r"['’]")
_SLUG_BAD = re.compile(r"[^a-z0-9]+")


def slugify_beer_id(brewery: str, name: str) -> str:
    """Stable URL-safe identifier: `{brewery-slug}__{name-slug}`.

    Lowercase, ASCII alphanumerics + hyphen only. Apostrophes are stripped
    (so "Devil's" -> "devils"); ampersands, slashes, and consecutive
    whitespace collapse to a single hyphen. Uses `__` between brewery and
    name so the join survives the hyphenation. Asterisks (BrewDog's
    convention for special-edition variants, e.g. "Tokyo*") become
    "-star" so the variant stays distinct from its base beer.
    """
    def slug(s: str) -> str:
        s = s.lower().strip()
        s = _SLUG_ASTERISK.sub("-star", s)
        s = _SLUG_APOSTROPHE.sub("", s)
        s = _SLUG_BAD.sub("-", s)
        s = s.strip("-")
        return s
    return f"{slug(brewery)}__{slug(name)}"


CURATED_COLUMNS = ("beer_id", "name", "brewery", "style", "country", "abv", "ibu", "srm")
SUPPLEMENT_COLUMNS = ("name", "brewery", "style", "country", "abv", "ibu", "srm")

# OBDB uses "United States" / "United Kingdom"; the curated catalog and
# dashboard filters historically use "USA" / "UK".
COUNTRY_NORMALIZATION = {
    "United States": "USA",
    "United Kingdom": "UK",
}


def join_and_clean(raw_dir: Path = RAW_OBDB) -> pd.DataFrame:
    """Stage 2: join beers ↔ breweries ↔ styles, drop unusable rows."""
    beers = pd.read_csv(raw_dir / "beers.csv")
    breweries = pd.read_csv(raw_dir / "breweries.csv")
    styles = pd.read_csv(raw_dir / "styles.csv")

    beers = beers.rename(columns={"id": "beer_id"})
    breweries = breweries.rename(columns={"name": "brewery", "id": "brewery_id"})
    styles = styles.rename(columns={"id": "style_id", "style_name": "style_obdb"})

    df = beers.merge(
        breweries[["brewery_id", "brewery", "country"]],
        on="brewery_id",
        how="left",
    )
    df = df.merge(styles[["style_id", "style_obdb"]], on="style_id", how="left")

    for col in ("abv", "ibu", "srm"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # OBDB uses 0 to mean missing for these columns.
    df.loc[df["ibu"] == 0, "ibu"] = np.nan
    df.loc[df["srm"] == 0, "srm"] = np.nan
    df.loc[df["abv"] == 0, "abv"] = np.nan

    df["country"] = df["country"].replace(COUNTRY_NORMALIZATION)

    df = df.dropna(subset=["name", "brewery", "style_obdb", "country", "abv"])
    df = df.drop_duplicates(subset=["name", "brewery"])

    df["abv"] = df["abv"].clip(lower=0, upper=20)
    df["ibu"] = df["ibu"].clip(lower=0, upper=120)

    df = df[["name", "brewery", "country", "style_obdb", "abv", "ibu", "srm"]]
    return df.reset_index(drop=True)


def normalize_style(df: pd.DataFrame) -> pd.DataFrame:
    """Stage 3a: map OBDB style → BJCP key; drop rows with unmapped style."""
    df = df.copy()
    df["style"] = df["style_obdb"].map(to_bjcp)
    dropped = int(df["style"].isna().sum())
    print(f"normalize_style: dropping {dropped} rows with unmapped OBDB style")
    df = df.dropna(subset=["style"])
    return df.drop(columns=["style_obdb"]).reset_index(drop=True)


def stratified_sample(
    df: pd.DataFrame, target_size: int = 750, seed: int = 42
) -> pd.DataFrame:
    """Stage 3b: three-tier-capped stratified sample.

    Caps applied in order:
        1. per (country, style) cell — 6 rows max
        2. per style — ceil(0.08 * target_size) rows max
        3. per country — ceil(0.35 * target_size) rows max
        4. uniform downsample to target_size if still over

    Within each cap, when surplus rows must be dropped, prefer to keep
    diversity on the other axis: when capping a style we first keep one
    row per country, then fill remaining slots; same idea for the
    per-country cap.
    """
    # Caps are sized so the post-shrinkage catalog stays comfortably under
    # the share thresholds enforced by tests/test_catalog.py (≤35% country,
    # ≤8% style), even when the final catalog is smaller than target_size.
    max_per_cell = 5
    max_per_style = math.ceil(0.06 * target_size)
    max_per_country = math.ceil(0.30 * target_size)

    # Initial shuffle for randomized tie-breaking.
    shuffled = df.sample(frac=1, random_state=seed).reset_index(drop=True)

    # 1. Per-(country, style) cap — keep first 6 per cell.
    cell_pos = shuffled.groupby(["country", "style"]).cumcount()
    capped = shuffled[cell_pos < max_per_cell].reset_index(drop=True)

    # 2. Per-style cap — sort so first-of-each-country comes first within
    #    a style, then take the top max_per_style per style.
    cs_rank = capped.groupby(["style", "country"]).cumcount()
    capped = (
        capped.assign(_priority=cs_rank)
        .sort_values(["style", "_priority"], kind="stable")
        .reset_index(drop=True)
    )
    style_pos = capped.groupby("style").cumcount()
    capped = (
        capped[style_pos < max_per_style]
        .drop(columns="_priority")
        .reset_index(drop=True)
    )

    # 3. Per-country cap — same trick on the other axis.
    sc_rank = capped.groupby(["country", "style"]).cumcount()
    capped = (
        capped.assign(_priority=sc_rank)
        .sort_values(["country", "_priority"], kind="stable")
        .reset_index(drop=True)
    )
    country_pos = capped.groupby("country").cumcount()
    capped = (
        capped[country_pos < max_per_country]
        .drop(columns="_priority")
        .reset_index(drop=True)
    )

    # 4. Final size adjustment.
    if len(capped) > target_size:
        capped = capped.sample(n=target_size, random_state=seed).reset_index(drop=True)

    # 5. Enforce share thresholds on the FINAL catalog: top country ≤ 35%,
    #    top style ≤ 8%. Absolute caps above can over-shoot when the catalog
    #    shrinks more than target_size; this pass trims the largest groups
    #    until their share is below the cutoffs.
    capped = _enforce_share_cap(capped, "country", 0.35)
    capped = _enforce_share_cap(capped, "style", 0.08)

    capped = capped.reset_index(drop=True)
    return capped[list(SUPPLEMENT_COLUMNS)]


def _enforce_share_cap(
    df: pd.DataFrame, column: str, max_share: float
) -> pd.DataFrame:
    """Drop trailing rows from the largest group(s) until every group's
    share of the (shrinking) catalog is ≤ max_share. Stable: assumes input
    is already shuffled, drops from the tail."""
    out = df.reset_index(drop=True).copy()
    while True:
        counts = out[column].value_counts()
        if counts.empty:
            break
        top_value = counts.index[0]
        top_count = counts.iloc[0]
        # Want top_count / len(out) ≤ max_share.
        # Equivalent to top_count ≤ max_share * len(out).
        if top_count <= max_share * len(out):
            break
        # Drop one trailing row of the top group.
        top_rows = out[out[column] == top_value]
        out = out.drop(top_rows.index[-1]).reset_index(drop=True)
    return out


def _validate_supplement(df: pd.DataFrame) -> None:
    """Raise ValueError if the supplement DataFrame is malformed.

    Checks (in order):
    - exact column-set match against SUPPLEMENT_COLUMNS
    - every `style` value is a key in STYLE_ATTRS

    No bounds-checking on abv/ibu/srm — the data_prep notebook clips these.
    This validator catches the kinds of typos a human makes in a CSV.
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


def apply_supplements(
    sampled: pd.DataFrame, path: Path = SUPPLEMENT_PATH
) -> pd.DataFrame:
    """Merge data/raw/supplemental_beers.csv into the sampled DataFrame.

    - Missing file → silent passthrough (pipeline behaves as if there
      were no supplement).
    - File present → validated and appended; on (name, brewery) collisions
      the supplement row wins so the user can override an OBDB row.
    """
    if not path.exists():
        return sampled.copy()
    supp = pd.read_csv(path)
    _validate_supplement(supp)
    combined = pd.concat(
        [sampled, supp[list(SUPPLEMENT_COLUMNS)]], ignore_index=True
    )
    combined = combined.drop_duplicates(subset=["name", "brewery"], keep="last")
    return combined.reset_index(drop=True)


def write_coverage_report(
    joined: pd.DataFrame,
    normalized: pd.DataFrame,
    sampled: pd.DataFrame,
    out: Path = OUT_COVERAGE,
) -> None:
    """Markdown summary of what the pipeline kept and dropped."""
    unmapped_mask = joined["style_obdb"].map(to_bjcp).isna()
    dropped_styles = (
        joined.loc[unmapped_mask]
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

    lines += [
        "",
        "## Country distribution (final)",
        "",
        "| country | rows | share |",
        "|---|---|---|",
    ]
    total = max(1, len(sampled))
    for country, n in sampled["country"].value_counts().items():
        lines.append(f"| {country} | {n} | {n / total:.1%} |")

    lines += [
        "",
        "## Style distribution (final, top 30)",
        "",
        "| style | rows | share |",
        "|---|---|---|",
    ]
    for style, n in sampled["style"].value_counts().head(30).items():
        lines.append(f"| {style} | {n} | {n / total:.1%} |")

    # Supplemental beers summary (only if the file exists, and only counting
    # supplement rows that survived into the final catalog).
    if SUPPLEMENT_PATH.exists():
        supp = pd.read_csv(SUPPLEMENT_PATH)
        supp_keys = set(zip(supp["name"], supp["brewery"]))
        in_supp = sampled.apply(
            lambda r: (r["name"], r["brewery"]) in supp_keys, axis=1
        )
        supp_rows = sampled[in_supp]
        if not supp_rows.empty:
            lines += [
                "",
                "## Supplemental beers included",
                "",
                "| country | rows |",
                "|---|---|",
            ]
            for country, n in supp_rows["country"].value_counts().items():
                lines.append(f"| {country} | {n} |")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"coverage report: {out}")


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
    print(
        f"after style normalization: {len(normalized)} rows, "
        f"{normalized['style'].nunique()} BJCP styles"
    )

    sampled = stratified_sample(normalized, target_size=args.target_size, seed=args.seed)
    print(f"sampled (no supplements yet): {len(sampled)} rows")

    combined = apply_supplements(sampled)
    n_supp = len(combined) - len(sampled)
    if n_supp != 0:
        print(f"applied supplements: +{n_supp} rows ({SUPPLEMENT_PATH.name})")

    combined.insert(
        0,
        "beer_id",
        [slugify_beer_id(b, n) for b, n in zip(combined["brewery"], combined["name"])],
    )
    if not combined["beer_id"].is_unique:
        dups = combined.loc[combined["beer_id"].duplicated(keep=False), :]
        raise AssertionError(
            f"slugify_beer_id produced duplicates:\n{dups[['beer_id','brewery','name']]}"
        )
    combined = combined[list(CURATED_COLUMNS)]
    combined.to_csv(OUT_CURATED, index=False)
    print(f"final catalog: {len(combined)} rows -> {OUT_CURATED}")
    print(
        f"countries: {combined['country'].nunique()}, "
        f"styles: {combined['style'].nunique()}"
    )

    write_coverage_report(joined, normalized, combined)
    return 0


if __name__ == "__main__":
    sys.exit(main())
