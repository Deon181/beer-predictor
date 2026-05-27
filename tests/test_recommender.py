"""Tests for the recommendation engine."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.recommender import (
    TASTE_COLS,
    _resolve_profile,
    explain,
    load_catalog,
    recommend,
)


@pytest.fixture(scope="module")
def catalog() -> pd.DataFrame:
    return load_catalog()


def test_catalog_loads(catalog: pd.DataFrame) -> None:
    assert len(catalog) > 100, "catalog should have at least 100 beers"
    expected_cols = {
        "beer_id", "name", "brewery", "style", "country",
        "abv", "ibu", "srm",
        *TASTE_COLS,
    }
    missing = expected_cols - set(catalog.columns)
    assert not missing, f"catalog missing columns: {missing}"


def test_taste_vector_in_range(catalog: pd.DataFrame) -> None:
    for col in TASTE_COLS:
        s = catalog[col]
        assert s.between(0, 10).all(), f"{col} outside 0-10"


def test_no_nan_in_taste_columns(catalog: pd.DataFrame) -> None:
    assert catalog[list(TASTE_COLS)].isna().sum().sum() == 0


def test_distance_is_symmetric() -> None:
    a = {c: 5.0 for c in TASTE_COLS}
    b = {c: 5.0 for c in TASTE_COLS}
    a["bitterness"] = 9.0
    b["bitterness"] = 1.0
    va = _resolve_profile(a)
    vb = _resolve_profile(b)
    d_ab = np.linalg.norm(va - vb)
    d_ba = np.linalg.norm(vb - va)
    assert d_ab == pytest.approx(d_ba)
    assert d_ab == pytest.approx(8.0)


def test_recommend_returns_topk_sorted() -> None:
    profile = {c: 5.0 for c in TASTE_COLS}
    recs = recommend(profile, top_k=7)
    assert len(recs) == 7
    scores = recs["match_score"].tolist()
    assert scores == sorted(scores, reverse=True), "results must be sorted by match_score desc"
    assert recs["match_score"].iloc[0] > 0


def test_recommend_extreme_bitterness_pulls_hoppy_styles() -> None:
    profile = {
        "bitterness": 10, "sweetness": 0, "maltiness": 4, "hoppiness": 10,
        "body": 6, "sourness": 0, "abv": 7,
    }
    recs = recommend(profile, top_k=5)
    styles = set(recs["style"].tolist())
    hoppy = {"American IPA", "Imperial IPA", "American Strong Ale",
             "American Barleywine"}
    assert styles & hoppy, f"expected hoppy styles in {styles}"


def test_recommend_extreme_sweetness_pulls_sweet_styles() -> None:
    profile = {
        "bitterness": 0, "sweetness": 10, "maltiness": 9, "hoppiness": 1,
        "body": 9, "sourness": 0, "abv": 7,
    }
    recs = recommend(profile, top_k=5)
    styles = set(recs["style"].tolist())
    sweet = {"Sweet Stout", "Imperial Stout", "Russian Imperial Stout",
             "Doppelbock", "Eisbock", "Belgian Strong Dark", "Quadrupel",
             "Wee Heavy", "Scotch Ale", "Baltic Porter"}
    assert styles & sweet, f"expected sweet styles in {styles}"


def test_filters_min_max_abv() -> None:
    profile = {c: 5.0 for c in TASTE_COLS}
    recs = recommend(profile, top_k=20, filters={"min_abv": 8.0, "max_abv": 12.0})
    assert (recs["abv"] >= 8.0).all()
    assert (recs["abv"] <= 12.0).all()


def test_filters_styles() -> None:
    profile = {c: 5.0 for c in TASTE_COLS}
    recs = recommend(profile, top_k=10, filters={"styles": ["Saison"]})
    assert (recs["style"] == "Saison").all()
    assert len(recs) > 0


def test_filters_exclude_styles() -> None:
    profile = {c: 5.0 for c in TASTE_COLS}
    recs = recommend(profile, top_k=20,
                     filters={"exclude_styles": ["American IPA",
                                                  "Imperial IPA"]})
    assert "American IPA" not in recs["style"].tolist()
    assert "Imperial IPA" not in recs["style"].tolist()


def test_filters_no_results_returns_empty() -> None:
    profile = {c: 5.0 for c in TASTE_COLS}
    recs = recommend(profile, top_k=10,
                     filters={"min_abv": 50.0})  # impossible
    assert recs.empty


def test_explain_returns_non_empty_string(catalog: pd.DataFrame) -> None:
    profile = {
        "bitterness": 9, "sweetness": 1, "maltiness": 5, "hoppiness": 9,
        "body": 6, "sourness": 0, "abv": 7,
    }
    recs = recommend(profile, top_k=3)
    for _, r in recs.iterrows():
        s = explain(r, profile)
        assert isinstance(s, str)
        assert len(s) > 20
        assert r["name"] in s


def test_resolve_profile_defaults_to_neutral() -> None:
    v = _resolve_profile({})
    assert (v == 5.0).all()


def test_resolve_profile_clips_out_of_range() -> None:
    v = _resolve_profile({"bitterness": 99, "sweetness": -10})
    assert v[0] == 10.0  # bitterness clipped to 10
    assert v[1] == 0.0   # sweetness clipped to 0
