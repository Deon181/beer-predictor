"""Tests for the processed beer catalog (output of the data_prep notebook)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.recommender import TASTE_COLS

PROCESSED = ROOT / "data" / "processed" / "beers.parquet"


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    if not PROCESSED.exists():
        pytest.skip("processed catalog not built — run notebooks/data_prep.ipynb")
    return pd.read_parquet(PROCESSED)


def test_processed_file_exists() -> None:
    assert PROCESSED.exists(), "data/processed/beers.parquet missing — run data_prep notebook"


def test_no_duplicate_beer_ids(df: pd.DataFrame) -> None:
    assert df["beer_id"].is_unique


def test_required_columns(df: pd.DataFrame) -> None:
    required = {
        "beer_id", "name", "brewery", "style", "country",
        "abv", "ibu", "srm",
        *TASTE_COLS,
    }
    missing = required - set(df.columns)
    assert not missing, f"missing columns: {missing}"


def test_taste_vectors_in_range(df: pd.DataFrame) -> None:
    for col in TASTE_COLS:
        assert df[col].between(0, 10).all(), f"{col} out of 0-10"


def test_no_nans_in_taste_columns(df: pd.DataFrame) -> None:
    assert df[list(TASTE_COLS)].isna().sum().sum() == 0


def test_abv_in_plausible_bounds(df: pd.DataFrame) -> None:
    assert df["abv"].between(0, 20).all(), "ABV outside plausible bounds"


def test_ibu_in_plausible_bounds(df: pd.DataFrame) -> None:
    assert df["ibu"].between(0, 120).all(), "IBU outside plausible bounds"


def test_styles_are_strings(df: pd.DataFrame) -> None:
    assert df["style"].apply(lambda s: isinstance(s, str)).all()


def test_minimum_catalog_size(df: pd.DataFrame) -> None:
    assert len(df) >= 100, f"catalog too small: {len(df)} rows"


def test_diverse_styles(df: pd.DataFrame) -> None:
    assert df["style"].nunique() >= 30, "should have at least 30 distinct styles"
