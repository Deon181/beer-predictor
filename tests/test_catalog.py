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
    # OBDB tags ~46 distinct BJCP-mappable styles; the SA supplement adds
    # ~4 more (New England IPA, Belgian Strong Pale, English Barleywine,
    # Scotch Ale, etc.) bringing the catalog to ≥50.
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
    high = ((df["abv"] >= 8.0) & (df["abv"] <= 12.0)).sum()
    assert high >= 5, f"only {high} beers in [8,12] ABV"


def test_has_saison_for_filter_test(df: pd.DataFrame) -> None:
    """test_recommender.test_filters_styles uses 'Saison'."""
    assert (df["style"] == "Saison").any()


def test_catalog_contains_south_africa(df: pd.DataFrame) -> None:
    sa = df[df["country"] == "South Africa"]
    assert len(sa) >= 20, f"only {len(sa)} SA beers in final catalog"
    assert sa["brewery"].nunique() >= 4, (
        f"expected ≥4 distinct SA breweries, got {sa['brewery'].nunique()}"
    )
